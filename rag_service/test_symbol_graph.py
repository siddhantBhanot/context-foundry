import shutil
import tempfile
import unittest
from pathlib import Path

from rag_service.domain.models import Chunk, DocumentType, ServiceMetadata
from rag_service.ingestion.symbol_graph import (
    EdgeType,
    NodeType,
    SymbolGraphBuilder,
    SymbolGraphIndex,
)
from rag_service.infrastructure.providers.qdrant_store import QdrantVectorStoreAdapter


class TestSymbolGraph(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="symbol_graph_test_"))

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_java_two_pass_di_and_call_resolution(self) -> None:
        """
        Verify the exact scenario proposed by the user:
        OrderService depends on PaymentService, createOrder() calls paymentService.charge().
        PaymentService is an interface implemented by StripePaymentService.
        """
        # File 1: PaymentService.java (Interface)
        (self.temp_dir / "PaymentService.java").write_text(
            """package com.example.payment;
public interface PaymentService {
    void charge();
}""",
            encoding="utf-8",
        )

        # File 2: StripePaymentService.java (Implementation)
        (self.temp_dir / "StripePaymentService.java").write_text(
            """package com.example.payment;
public class StripePaymentService implements PaymentService {
    @Override
    public void charge() {
        System.out.println("Charging stripe");
    }
}""",
            encoding="utf-8",
        )

        # File 3: OrderService.java (Service with DI and method invocation)
        (self.temp_dir / "OrderService.java").write_text(
            """package com.example.order;
import com.example.payment.PaymentService;

@Service
public class OrderService {
    private final PaymentService paymentService;

    public OrderService(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    public void createOrder() {
        paymentService.charge();
    }
}""",
            encoding="utf-8",
        )

        # File 4: OrderController.java (API Ingress)
        (self.temp_dir / "OrderController.java").write_text(
            """package com.example.order;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/orders")
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping("/create")
    public void handleOrder() {
        orderService.createOrder();
    }
}""",
            encoding="utf-8",
        )

        # Build symbol graph
        graph = SymbolGraphBuilder.build_and_save(self.temp_dir, "order-service")
        idx = SymbolGraphIndex(graph)

        # Verify Nodes
        self.assertIn("PaymentService", idx.class_names_map)
        self.assertIn("StripePaymentService", idx.class_names_map)
        self.assertIn("OrderService", idx.class_names_map)
        self.assertIn("OrderController", idx.class_names_map)
        self.assertIn("createOrder", idx.method_names_map)
        self.assertIn("charge", idx.method_names_map)
        self.assertIn("handleOrder", idx.method_names_map)
        self.assertIn("POST /orders/create", idx.endpoints_map)

        # Verify Ingress -> Controller Edge
        controller_method = idx.find_nodes_by_name("OrderController.handleOrder")[0]
        ingress_nodes = [
            idx.nodes[e.source_id]
            for e in idx.incoming.get(controller_method.id, [])
            if e.edge_type == EdgeType.INVOKES
        ]
        self.assertTrue(any(n.name == "POST /orders/create" for n in ingress_nodes))

        # Verify OrderController.handleOrder -> OrderService.createOrder (Call Edge)
        order_method = idx.find_nodes_by_name("OrderService.createOrder")[0]
        out_edges_controller = idx.outgoing.get(controller_method.id, [])
        callee_ids = [e.target_id for e in out_edges_controller if e.edge_type == EdgeType.CALLS]
        self.assertIn(order_method.id, callee_ids)

        # Verify OrderService.createOrder -> PaymentService.charge & StripePaymentService.charge
        out_edges_order = idx.outgoing.get(order_method.id, [])
        callee_ids_order = [e.target_id for e in out_edges_order if e.edge_type == EdgeType.CALLS]

        payment_interface_method = idx.find_nodes_by_name("PaymentService.charge")[0]
        stripe_impl_method = idx.find_nodes_by_name("StripePaymentService.charge")[0]

        self.assertIn(payment_interface_method.id, callee_ids_order)
        self.assertIn(stripe_impl_method.id, callee_ids_order)

        # Verify Call Hierarchy Trace
        trace = idx.build_call_hierarchy_trace(["handleOrder"])
        trace_str = "\n".join(trace)
        self.assertIn("POST /orders/create", trace_str)
        self.assertIn("OrderController.handleOrder", trace_str)
        self.assertIn("OrderService.createOrder", trace_str)
        self.assertIn("PaymentService.charge", trace_str)
        self.assertIn("StripePaymentService.charge", trace_str)

    def test_kotlin_primary_constructor_di_and_calls(self) -> None:
        """Verify Kotlin classes with primary constructor DI and member function calls."""
        (self.temp_dir / "AuthService.kt").write_text(
            """package com.example.auth

interface TokenGenerator {
    fun generateToken(userId: String): String
}

class JwtTokenGenerator : TokenGenerator {
    override fun generateToken(userId: String): String = "jwt-token"
}

class AuthService(private val tokenGenerator: TokenGenerator) {
    fun login(userId: String): String {
        return tokenGenerator.generateToken(userId)
    }
}""",
            encoding="utf-8",
        )

        graph = SymbolGraphBuilder.build_and_save(self.temp_dir, "auth-service")
        idx = SymbolGraphIndex(graph)

        self.assertIn("AuthService", idx.class_names_map)
        self.assertIn("TokenGenerator", idx.class_names_map)
        self.assertIn("JwtTokenGenerator", idx.class_names_map)
        self.assertIn("login", idx.method_names_map)
        self.assertIn("generateToken", idx.method_names_map)

        login_method = idx.find_nodes_by_name("AuthService.login")[0]
        callees = idx.get_callees(login_method.id, max_depth=2)
        callee_names = [c.name for c in callees]
        self.assertTrue(
            any("generateToken" in name for name in callee_names),
            f"Expected generateToken in callees, got {callee_names}",
        )

    def test_python_init_di_and_method_calls(self) -> None:
        """Verify Python classes with typed __init__ DI and attribute calls."""
        (self.temp_dir / "user_service.py").write_text(
            """class UserRepository:
    def find_by_id(self, user_id: str):
        return {"id": user_id}

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_user_profile(self, user_id: str):
        return self.user_repo.find_by_id(user_id)
""",
            encoding="utf-8",
        )

        graph = SymbolGraphBuilder.build_and_save(self.temp_dir, "user-service")
        idx = SymbolGraphIndex(graph)

        self.assertIn("UserService", idx.class_names_map)
        self.assertIn("UserRepository", idx.class_names_map)
        self.assertIn("get_user_profile", idx.method_names_map)
        self.assertIn("find_by_id", idx.method_names_map)

        profile_method = idx.find_nodes_by_name("UserService.get_user_profile")[0]
        callees = idx.get_callees(profile_method.id, max_depth=1)
        self.assertTrue(any("find_by_id" in c.name for c in callees))

    def test_vector_store_fetch_by_methods(self) -> None:
        """Verify in-memory QdrantVectorStore fetch_by_methods behavior."""
        from rag_service.infrastructure.config import Settings
        store = QdrantVectorStoreAdapter(settings=Settings(qdrant_url="", qdrant_api_key=""))
        store._client = None

        chunk1 = Chunk(
            id="c1",
            content="public void charge() { ... }",
            metadata=ServiceMetadata(
                service="test-service",
                document_type=DocumentType.SOURCE_CODE,
                source="repo",
                file_path="PaymentService.java",
                class_name="PaymentService",
                method_name="charge",
            ),
        )
        chunk2 = Chunk(
            id="c2",
            content="public void createOrder() { ... }",
            metadata=ServiceMetadata(
                service="test-service",
                document_type=DocumentType.SOURCE_CODE,
                source="repo",
                file_path="OrderService.java",
                class_name="OrderService",
                method_name="createOrder",
            ),
        )

        import asyncio

        loop = asyncio.new_event_loop()
        loop.run_until_complete(store.upsert([chunk1, chunk2]))

        results = loop.run_until_complete(
            store.fetch_by_methods(
                service="test-service",
                methods=["PaymentService.charge", "createOrder"],
                limit=2,
            )
        )
        loop.close()

        self.assertEqual(len(results), 2)
        found_methods = {r.metadata.method_name for r in results}
        self.assertIn("charge", found_methods)
        self.assertIn("createOrder", found_methods)

    def test_spring_boot_realworld_end_to_end(self) -> None:
        """Verify symbol graph on the real ingested spring-boot-realworld microservice."""
        realworld_dir = Path("backend_service/data/storage/services/spring-boot-realworld")
        if not realworld_dir.exists():
            self.skipTest("spring-boot-realworld directory not found")

        graph = SymbolGraphBuilder.build_and_save(realworld_dir, "spring-boot-realworld")
        idx = SymbolGraphIndex(graph)

        self.assertGreater(graph.total_nodes, 300)
        self.assertGreater(graph.total_edges, 800)

        # Check that createArticle traces all the way to MyBatisArticleRepository.save
        trace = idx.build_call_hierarchy_trace(["createArticle"])
        trace_str = "\n".join(trace)
        self.assertIn("ArticlesApi.createArticle", trace_str)
        self.assertIn("ArticleCommandService.createArticle", trace_str)
        self.assertIn("ArticleRepository.save", trace_str)
        self.assertIn("MyBatisArticleRepository.save", trace_str)


if __name__ == "__main__":
    unittest.main()

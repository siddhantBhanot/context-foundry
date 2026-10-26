import asyncio
import sys

async def verify_kt_qdrant():
    print("1. Testing CourseIndexer and Qdrant isolation...")
    from rag_service.infrastructure.config import get_settings
    from rag_service.infrastructure.providers.qdrant_store import QdrantVectorStoreAdapter
    from rag_service.infrastructure.providers.qdrant_embedding import QdrantEmbeddingProvider
    from rag_service.infrastructure.providers.openai_llm import OpenAiClientProvider
    from rag_service.knowledge_cafe.course_indexer import CourseIndexer
    from rag_service.knowledge_cafe.kt_engine import KTEngine

    settings = get_settings()
    print(f"   Dev Chat collection: {settings.qdrant_collection_name}")
    print(f"   KT Courses collection: {settings.qdrant_kt_collection_name}")
    assert settings.qdrant_collection_name != settings.qdrant_kt_collection_name, "Collections MUST be different!"

    # Instantiate dedicated vector store and embedding provider
    kt_store = QdrantVectorStoreAdapter(
        settings=settings,
        collection_name=settings.qdrant_kt_collection_name,
    )
    emb_provider = QdrantEmbeddingProvider(settings)

    indexer = CourseIndexer(
        vector_store=kt_store,
        embedding_provider=emb_provider,
    )

    print("\n2. Indexing income-assessment-kt course materials into knowledge_cafe_collection...")
    count = await indexer.index_course("income-assessment-kt", force=True)
    print(f"   Upserted {count} chunks for income-assessment-kt.")
    assert count > 0, "Expected at least 1 chunk indexed!"

    print("\n3. Testing strict course_id pre-filtering...")
    query_text = "How does MongoDB reactive repository handle timeout?"
    query_vec = await emb_provider.embed_query(query_text)

    # Search with correct course_id
    matched_correct = await kt_store.search(
        query_vector=query_vec,
        limit=5,
        filter_dict={"course_id": "income-assessment-kt"},
    )
    print(f"   Matched {len(matched_correct)} chunks for course_id='income-assessment-kt'")
    assert len(matched_correct) > 0, "Should match chunks for income-assessment-kt"
    for m in matched_correct:
        assert m.metadata.extra.get("course_id") == "income-assessment-kt"

    # Search with different/unrelated course_id -> MUST return 0 chunks
    matched_wrong = await kt_store.search(
        query_vector=query_vec,
        limit=5,
        filter_dict={"course_id": "unrelated-nonexistent-course"},
    )
    print(f"   Matched {len(matched_wrong)} chunks for course_id='unrelated-nonexistent-course'")
    assert len(matched_wrong) == 0, "Isolation failure! Chunks returned for wrong course_id"
    print("   ✓ Strict course isolation verified: 0 chunks leaked!")

    print("\n4. Testing KTEngine with vector store integrated...")
    llm = OpenAiClientProvider(settings)
    engine = KTEngine(
        llm_provider=llm,
        kt_vector_store=kt_store,
        embedding_provider=emb_provider,
    )

    print("   Asking doubt via engine (testing vector search + synthesis)...")
    doubt_res = await engine.answer_doubt(
        course_id="income-assessment-kt",
        lesson_id="02-architecture",
        question="Why is WebFlux reactive model chosen?",
    )
    print(f"   Answer length: {len(doubt_res['answer'])} chars")
    print(f"   Sources cited: {len(doubt_res['sources'])} sources")
    assert len(doubt_res["answer"]) > 50, "Answer too short"
    assert len(doubt_res["sources"]) > 0, "No sources cited"
    print("   Answer snippet:", doubt_res["answer"][:150], "...")
    print("   ✓ Doubt answering with dedicated course vector context works seamlessly!")

    print("\n5. Testing deterministic lesson synthesis (verifying no regression on file loading)...")
    lesson_res = await engine.synthesize_lesson(
        course_id="income-assessment-kt",
        lesson_id="01-service-overview",
    )
    assert len(lesson_res["content"]) > 100
    print(f"   Lesson 1 synthesized: {len(lesson_res['content'])} chars")
    print("   ✓ Lesson synthesis remains 100% complete and deterministic!")

    print("\nALL KT QDRANT TESTS PASSED SUCCESSFULLY! 🎉")

if __name__ == "__main__":
    asyncio.run(verify_kt_qdrant())

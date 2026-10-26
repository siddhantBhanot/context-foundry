from pathlib import Path
import sys
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

_project_root = Path(__file__).resolve().parents[4]

router = APIRouter(prefix="/services", tags=["Services"])


class ServiceInfo(BaseModel):
    id: str
    name: str
    description: str
    has_indexed_data: bool = False
    doc_count: int = 0


@router.get("", response_model=List[ServiceInfo])
async def list_available_services() -> List[ServiceInfo]:
    """
    List supported microservices, discovering any services with local sample data or docs.
    """
    sample_data_dir = _project_root / "rag_service" / "sample_data"

    services = [
        ServiceInfo(
            id="income-assessment-service",
            name="income-assessment-service",
            description="Income assessment rules engine & eligibility calculations",
            has_indexed_data=True,
            doc_count=3,
        ),
        ServiceInfo(
            id="loan-origination-service",
            name="loan-origination-service",
            description="Loan application lifecycle & underwriting workflows",
            has_indexed_data=False,
            doc_count=0,
        ),
        ServiceInfo(
            id="kyc-verification-service",
            name="kyc-verification-service",
            description="Identity verification & document assessment",
            has_indexed_data=False,
            doc_count=0,
        ),
    ]

    # Dynamically scan sample_data for any newly added microservices
    if sample_data_dir.exists():
        existing_ids = {s.id for s in services}
        for path in sample_data_dir.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                files = [
                    f for f in path.glob("**/*")
                    if f.is_file() and f.suffix.lower() in [".md", ".kt", ".kts"]
                ]
                if path.name not in existing_ids:
                    services.append(
                        ServiceInfo(
                            id=path.name,
                            name=path.name,
                            description=f"Microservice documentation & contracts for {path.name}",
                            has_indexed_data=len(files) > 0,
                            doc_count=len(files),
                        )
                    )
                else:
                    # Update doc_count
                    for s in services:
                        if s.id == path.name:
                            s.has_indexed_data = len(files) > 0
                            s.doc_count = len(files)

    return services

from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend_service.app.api.dependencies import get_current_user
from backend_service.app.domain.models.user import User
from backend_service.app.infrastructure.persistence.database import Database, get_database

_project_root = Path(__file__).resolve().parents[4]
_storage_dir = _project_root / "backend_service" / "data" / "storage" / "services"
_sample_data_dir = _project_root / "rag_service" / "sample_data"

router = APIRouter(prefix="/services", tags=["Services"])


class ServiceInfo(BaseModel):
    id: str
    name: str
    description: str
    has_indexed_data: bool = False
    doc_count: int = 0


class CreateServiceRequest(BaseModel):
    id: str = Field(..., min_length=2, max_length=64, description="Service identifier, e.g. payment-gateway-service")
    name: Optional[str] = Field(None, max_length=128, description="Human-readable name")
    description: Optional[str] = Field(None, max_length=500, description="Brief description of the service")


@router.get("", response_model=List[ServiceInfo])
async def list_available_services(
    db: Database = Depends(get_database),
) -> List[ServiceInfo]:
    """
    List supported microservices, aggregating registered services from SQLite,
    dedicated storage, and legacy sample directories.
    """
    allowed_suffixes = {".md", ".markdown", ".pdf", ".kt", ".kts"}
    services_map = {}

    # 1. Default initial services
    defaults = [
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
    for s in defaults:
        services_map[s.id] = s

    # 2. Load registered services from database
    try:
        async with db.connection() as conn:
            cursor = await conn.execute("SELECT id, name, description FROM registered_services")
            rows = await cursor.fetchall()
            for row in rows:
                sid = row["id"]
                if sid not in services_map:
                    services_map[sid] = ServiceInfo(
                        id=sid,
                        name=row["name"] or sid,
                        description=row["description"] or f"Microservice {sid}",
                        has_indexed_data=False,
                        doc_count=0,
                    )
    except Exception:
        pass

    # 3. Helper to count non-pending valid files in a directory
    def count_service_files(dir_path: Path) -> set:
        found_names = set()
        if dir_path.is_dir():
            for f in dir_path.rglob("*"):
                if f.is_file() and f.suffix.lower() in allowed_suffixes and "pending" not in f.parts:
                    found_names.add(f.name)
        return found_names

    # 4. Scan dedicated storage and sample_data
    all_service_ids = set(services_map.keys())
    for parent in [_storage_dir, _sample_data_dir]:
        if parent.exists():
            for child in parent.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    all_service_ids.add(child.name)

    # 5. Populate and calculate document counts
    for sid in all_service_ids:
        files_set = set()
        files_set.update(count_service_files(_storage_dir / sid))
        files_set.update(count_service_files(_sample_data_dir / sid))

        doc_count = len(files_set)
        has_data = doc_count > 0

        if sid in services_map:
            services_map[sid].doc_count = doc_count
            services_map[sid].has_indexed_data = has_data
        else:
            services_map[sid] = ServiceInfo(
                id=sid,
                name=sid,
                description=f"Microservice documentation & contracts for {sid}",
                has_indexed_data=has_data,
                doc_count=doc_count,
            )

    return list(services_map.values())


@router.post("", response_model=ServiceInfo, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: CreateServiceRequest,
    current_user: User = Depends(get_current_user),
    db: Database = Depends(get_database),
) -> ServiceInfo:
    """
    Register a new microservice context for knowledge ingestion and grounded Q&A.
    """
    cleaned_id = payload.id.strip().lower()
    if not re.match(r"^[a-z0-9_\-]+$", cleaned_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service ID may only contain lowercase letters, numbers, hyphens, and underscores.",
        )

    name = payload.name.strip() if payload.name and payload.name.strip() else cleaned_id
    description = (
        payload.description.strip()
        if payload.description and payload.description.strip()
        else f"Microservice knowledge context for {cleaned_id}"
    )

    # Persist to database
    now_iso = datetime.now(timezone.utc).isoformat()
    async with db.connection() as conn:
        await conn.execute(
            """
            INSERT INTO registered_services (id, name, description, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description;
            """,
            (cleaned_id, name, description, now_iso),
        )
        await conn.commit()

    # Ensure storage folder structure exists
    target_storage = _storage_dir / cleaned_id / "pending"
    target_storage.mkdir(parents=True, exist_ok=True)

    return ServiceInfo(
        id=cleaned_id,
        name=name,
        description=description,
        has_indexed_data=False,
        doc_count=0,
    )


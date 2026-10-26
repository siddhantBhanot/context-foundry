import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend_service.app.application.services.saathi_service import (
    SaathiService,
    get_saathi_service,
)
from backend_service.app.domain.models.saathi import (
    CustomerRelationship,
    CustomerSummaryDTO,
    RelationshipBrief,
    CustomerFeedbackRequest,
    UpdateActionStatusRequest,
    UpdateCommitmentStatusRequest,
    TriggerHandoverRequest,
    TransitionActionItem,
    CommitmentItem,
    AskSaathiRequest,
    AskSaathiResponse,
    ValidateFactRequest,
    PreCallBriefing,
    ManagementSummary,
    AddContextRequest,
    ManualContextItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saathi", tags=["Saathi - Relationship Continuity"])


@router.get("/customers", response_model=List[CustomerSummaryDTO])
async def list_transition_customers(
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> List[CustomerSummaryDTO]:
    """
    List all customer transition cases under Saathi Continuity management.
    """
    return saathi_service.list_customers()


@router.get("/customers/{customer_id}", response_model=CustomerRelationship)
async def get_customer_relationship(
    customer_id: str,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> CustomerRelationship:
    """
    Retrieve full relationship profile, history, brief, commitments, facts, and timeline.
    """
    customer = saathi_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer transition profile '{customer_id}' not found.",
        )
    return customer


@router.post("/customers/{customer_id}/context", response_model=CustomerRelationship)
async def add_customer_context(
    customer_id: str,
    payload: AddContextRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> CustomerRelationship:
    """
    Manually add extra relationship context for a given customer from the UI.
    Automatically indexes the note into the dedicated Saathi Qdrant collection
    and re-synthesizes the AI Relationship Brief.
    """
    try:
        return await saathi_service.add_manual_context(customer_id=customer_id, request=payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add customer context for {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/customers/{customer_id}/synthesize-brief", response_model=RelationshipBrief)
async def synthesize_relationship_brief(
    customer_id: str,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> RelationshipBrief:
    """
    Step 1 ('We Remember'): Trigger AI synthesis of the Relationship Brief
    from historical interactions and CRM signals.
    """
    try:
        return await saathi_service.synthesize_brief(customer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to synthesize Saathi brief: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/customers/{customer_id}/ask", response_model=AskSaathiResponse)
async def ask_saathi_question(
    customer_id: str,
    payload: AskSaathiRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> AskSaathiResponse:
    """
    Natural-Language 'Ask Saathi':
    Ask questions grounded in customer history, distinguishing confirmed commitments
    from discussed possibilities.
    """
    try:
        return await saathi_service.ask_saathi(customer_id=customer_id, question=payload.question)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process Ask Saathi query: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/customers/{customer_id}/ask/stream")
async def ask_saathi_stream_endpoint(
    customer_id: str,
    payload: AskSaathiRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> StreamingResponse:
    """
    Streamed Ask Saathi natural-language Q&A using AWS Bedrock Sonnet 4.6 default with transparent fallback.
    Emits SSE events: metadata with model name, progressive token chunks, and done completion.
    """
    generator = saathi_service.ask_saathi_stream(customer_id=customer_id, question=payload.question)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/customers/{customer_id}/pre-call-brief", response_model=PreCallBriefing)
async def get_pre_call_brief(
    customer_id: str,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> PreCallBriefing:
    """
    'What Should I Know Before I Call?': 2-minute actionable pre-call briefing.
    """
    brief = saathi_service.get_pre_call_brief(customer_id)
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pre-call briefing for '{customer_id}' not found.",
        )
    return brief


@router.get("/customers/{customer_id}/management-summary", response_model=ManagementSummary)
async def get_management_summary(
    customer_id: str,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> ManagementSummary:
    """
    Executive Management Summary: High-level overview for leadership.
    """
    summary = saathi_service.get_management_summary(customer_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Management summary for '{customer_id}' not found.",
        )
    return summary


@router.post("/customers/{customer_id}/facts/{fact_id}/validate", response_model=CustomerRelationship)
async def validate_customer_fact(
    customer_id: str,
    fact_id: str,
    payload: ValidateFactRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> CustomerRelationship:
    """
    Customer Validation: Confirm, update, or mark a fact as no longer relevant.
    """
    try:
        return saathi_service.validate_customer_fact(
            customer_id=customer_id,
            fact_id=fact_id,
            action=payload.action,
            updated_text=payload.updated_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/customers/{customer_id}/commitments/{commitment_id}", response_model=CommitmentItem)
async def update_customer_commitment(
    customer_id: str,
    commitment_id: str,
    payload: UpdateCommitmentStatusRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> CommitmentItem:
    """
    Update status of a tracked relationship commitment.
    """
    try:
        return saathi_service.update_commitment_status(
            customer_id=customer_id,
            commitment_id=commitment_id,
            new_status=payload.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/customers/{customer_id}/customer-feedback", response_model=CustomerRelationship)
async def submit_customer_verification(
    customer_id: str,
    payload: CustomerFeedbackRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> CustomerRelationship:
    """
    Step 2 ('We Ask the Customer'): Customer confirms or provides additions to Saathi's understanding.
    """
    try:
        return saathi_service.submit_customer_feedback(
            customer_id=customer_id,
            customer_notes=payload.customer_notes,
            corrected_items=payload.corrected_items,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/customers/{customer_id}/actions/{action_id}", response_model=TransitionActionItem)
async def update_transition_action(
    customer_id: str,
    action_id: str,
    payload: UpdateActionStatusRequest,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> TransitionActionItem:
    """
    Step 4 ('We Hand Over Responsibility'): Update status of an open SLA handover item.
    """
    try:
        return saathi_service.update_action_status(
            customer_id=customer_id,
            action_id=action_id,
            new_status=payload.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/customers/{customer_id}/complete-handover", response_model=CustomerRelationship)
async def complete_rm_handover(
    customer_id: str,
    payload: Optional[TriggerHandoverRequest] = None,
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> CustomerRelationship:
    """
    Step 3/4: New RM formally accepts handover, activating full relationship management.
    """
    try:
        notes = payload.new_rm_notes if payload else None
        return saathi_service.complete_handover(customer_id=customer_id, new_rm_notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/reset-demo")
async def reset_saathi_demo(
    saathi_service: SaathiService = Depends(get_saathi_service),
) -> dict:
    """
    Reset all demo profiles and interactive transition states.
    """
    saathi_service.reset_demo()
    return {"status": "success", "message": "Saathi demo profiles reset to initial state."}

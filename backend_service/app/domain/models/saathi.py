from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClientTier(str, Enum):
    BURGUNDY = "Burgundy"
    BURGUNDY_PRIVATE = "Burgundy Private"
    NRI_ELITE = "NRI Elite"
    WEALTH = "Private Wealth"
    PRIORITY = "Priority Banking"


class TransitionStatus(str, Enum):
    INITIATED = "initiated"                   # RM transfer announced, synthesizing brief
    CUSTOMER_REVIEW = "customer_review"       # Reached out to customer for verification
    CUSTOMER_CONFIRMED = "customer_confirmed" # Customer added notes / verified
    HANDOVER_ACTIVE = "handover_active"       # New RM active with full brief & action tracker
    COMPLETED = "completed"                   # All transition tasks completed


class ActionPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CommitmentType(str, Enum):
    CONFIRMED_COMMITMENT = "confirmed_commitment"  # Firm promise/SLA made by bank/RM
    DISCUSSED_POSSIBILITY = "discussed_possibility" # Explored/suggested, but no commitment recorded


class CommitmentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    OVERDUE = "overdue"
    COMPLETED = "completed"


class HealthLevel(str, Enum):
    STABLE = "stable"                       # 🟢 No significant unresolved relationship issues
    ATTENTION_REQUIRED = "attention_required" # 🟡 Active discussions or pending follow-ups
    IMMEDIATE_ATTENTION = "immediate_attention" # 🔴 Overdue commitments or unresolved complaints


class CustomerFactStatus(str, Enum):
    CONFIRMED = "confirmed"
    UPDATED = "updated"
    NO_LONGER_RELEVANT = "no_longer_relevant"


class CRMInteraction(BaseModel):
    id: str
    date: str
    channel: str  # e.g., "Branch Meeting", "Phone Call", "WhatsApp Note", "Portfolio Review"
    rm_name: str
    summary: str
    tags: List[str] = Field(default_factory=list)


class TransitionActionItem(BaseModel):
    id: str
    title: str
    description: str
    category: str  # e.g., "Loan Renewal", "Wealth Allocation", "KYC / Service Request", "Family Assistance"
    priority: ActionPriority = ActionPriority.HIGH
    status: ActionStatus = ActionStatus.PENDING
    sla_date: str
    assigned_to: str


class CommitmentItem(BaseModel):
    id: str
    title: str
    details: str
    committed_by: str
    committed_on: str
    commitment_type: CommitmentType
    status: CommitmentStatus = CommitmentStatus.PENDING
    urgency: ActionPriority = ActionPriority.HIGH
    source_interaction_id: Optional[str] = None
    evidence_snippet: Optional[str] = None


class RelationshipTimelineEvent(BaseModel):
    id: str
    year: str
    date_display: str
    title: str
    description: str
    category: str  # e.g., "Relationship Inception", "Credit & Lending", "Education & Global", "Transition"
    source_channel: Optional[str] = None
    interaction_id: Optional[str] = None


class ContradictionAlert(BaseModel):
    id: str
    title: str
    description: str
    detected_date: str
    previous_record: str
    recent_record: str
    recommendation: str


class CustomerFact(BaseModel):
    id: str
    statement: str
    category: str  # e.g., "Family & Education", "Communication", "Financial Goal"
    status: CustomerFactStatus = CustomerFactStatus.CONFIRMED
    updated_note: Optional[str] = None
    last_updated: str


class RelationshipHealth(BaseModel):
    level: HealthLevel
    headline: str
    reasons: List[str] = Field(default_factory=list)


class PreCallBriefing(BaseModel):
    who_is_customer: str
    what_matters: List[str]
    current_discussions: List[str]
    what_we_owe: List[str]
    unresolved_issues: List[str]
    follow_up_items: List[str]
    sensitive_nuances: List[str]
    recommended_approach: str


class ManagementSummary(BaseModel):
    client_snapshot: str
    aum_and_tier: str
    active_opportunities: List[str]
    risk_and_unresolved: List[str]
    rm_handover_status: str
    executive_notes: str


class RelationshipBrief(BaseModel):
    client_sentiment: str
    executive_summary: str
    family_and_lifestage: List[str] = Field(default_factory=list)
    preferences_and_nuances: List[str] = Field(default_factory=list)
    active_portfolio_summary: str
    key_discussion_topics: List[str] = Field(default_factory=list)
    conversation_starter: str
    talking_points: List[str] = Field(default_factory=list)
    customer_priorities: List[str] = Field(default_factory=list)
    explicit_preferences: List[str] = Field(default_factory=list)
    current_conversations: List[str] = Field(default_factory=list)
    open_threads: List[str] = Field(default_factory=list)
    customer_concerns: List[str] = Field(default_factory=list)
    dont_repeat_items: List[str] = Field(default_factory=list)
    important_context: List[str] = Field(default_factory=list)
    synthesized_at: str


class CustomerFeedback(BaseModel):
    confirmed_at: Optional[str] = None
    customer_notes: Optional[str] = None
    corrected_items: List[str] = Field(default_factory=list)
    has_verified: bool = False


class ManualContextItem(BaseModel):
    id: str
    title: str
    category: str = "General"
    content: str
    source_channel: str = "RM Note"
    recorded_by: str = "Relationship Manager"
    created_at: str


class AddContextRequest(BaseModel):
    title: str
    category: str = "General"
    content: str
    source_channel: str = "RM Note"
    recorded_by: Optional[str] = None


class CustomerRelationship(BaseModel):
    id: str
    name: str
    tier: ClientTier
    segment_description: str
    city: str
    account_number_masked: str
    aum_display: str
    tenure_years: int
    avatar_color: str
    
    # RM Details
    previous_rm_name: str
    previous_rm_role: str
    transfer_reason: str
    new_rm_name: str
    new_rm_role: str
    new_rm_phone: str
    new_rm_email: str
    
    # Transition Pipeline
    status: TransitionStatus = TransitionStatus.INITIATED
    transition_date: str
    
    # Grounding Data & Intelligence
    interactions: List[CRMInteraction] = Field(default_factory=list)
    action_items: List[TransitionActionItem] = Field(default_factory=list)
    commitments: List[CommitmentItem] = Field(default_factory=list)
    timeline: List[RelationshipTimelineEvent] = Field(default_factory=list)
    contradictions: List[ContradictionAlert] = Field(default_factory=list)
    facts: List[CustomerFact] = Field(default_factory=list)
    extra_context: List[ManualContextItem] = Field(default_factory=list)
    health: Optional[RelationshipHealth] = None
    pre_call_brief: Optional[PreCallBriefing] = None
    management_summary: Optional[ManagementSummary] = None
    brief: Optional[RelationshipBrief] = None
    feedback: Optional[CustomerFeedback] = None


class CustomerSummaryDTO(BaseModel):
    id: str
    name: str
    tier: ClientTier
    city: str
    account_number_masked: str
    aum_display: str
    tenure_years: int
    previous_rm_name: str
    new_rm_name: str
    status: TransitionStatus
    transition_date: str
    avatar_color: str
    pending_actions_count: int
    health_level: HealthLevel = HealthLevel.STABLE
    open_commitments_count: int = 0
    contradictions_count: int = 0


class CustomerFeedbackRequest(BaseModel):
    customer_notes: str
    corrected_items: Optional[List[str]] = None


class UpdateActionStatusRequest(BaseModel):
    status: ActionStatus


class UpdateCommitmentStatusRequest(BaseModel):
    status: CommitmentStatus


class TriggerHandoverRequest(BaseModel):
    new_rm_notes: Optional[str] = None


class AskEvidenceItem(BaseModel):
    date: str
    channel: str
    rm_name: str
    snippet: str
    commitment_type: Optional[str] = None


class AskSaathiRequest(BaseModel):
    question: str


class AskSaathiResponse(BaseModel):
    question: str
    answer: str
    is_commitment: bool = False
    commitment_type: Optional[str] = None  # "confirmed_commitment" | "discussed_possibility" | "none"
    evidence: List[AskEvidenceItem] = Field(default_factory=list)
    confidence: str = "high"
    drilldown_context: Optional[str] = None
    model: str = "Claude Sonnet 4.6 (AWS Bedrock)"
    is_fallback: bool = False


class ValidateFactRequest(BaseModel):
    action: str  # "confirm" | "update" | "mark_irrelevant"
    updated_text: Optional[str] = None

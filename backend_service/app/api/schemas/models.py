from typing import List, Optional
from pydantic import BaseModel, Field


class ModelInfoResponse(BaseModel):
    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable display name")
    provider: str = Field(..., description="LLM provider category (e.g. groq, bedrock, openai)")
    description: Optional[str] = Field(default=None, description="Brief description of model capabilities")
    is_default: bool = Field(default=False, description="Whether this is the default model")


class ModelListResponse(BaseModel):
    models: List[ModelInfoResponse] = Field(..., description="List of configured and accessible LLM models")
    default_model: str = Field(..., description="Identifier of the default model")

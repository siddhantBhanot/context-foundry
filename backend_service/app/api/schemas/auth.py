from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    role: str = Field(default="developer", description="User role: 'developer' | 'banking_staff'")
    created_at: str = Field(..., description="Account creation timestamp (ISO 8601)")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="Authenticated user profile")


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, description="Valid email address")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    name: str = Field(..., min_length=1, description="Full name")
    role: str = Field(default="developer", description="User role: 'developer' | 'banking_staff'")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, description="User email address")
    password: str = Field(..., min_length=1, description="Password")

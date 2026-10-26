from typing import Any, Dict
from fastapi import APIRouter, Depends, status

from backend_service.app.api.dependencies import get_auth_service, get_current_user
from backend_service.app.api.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from backend_service.app.application.services.auth_service import AuthService
from backend_service.app.domain.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Register a new engineer user account and receive an access token.
    """
    result = await auth_service.signup(
        email=payload.email,
        password=payload.password,
        name=payload.name,
        role=payload.role,
    )
    return TokenResponse(**result)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate an existing user using email and password to receive a JWT access token.
    """
    result = await auth_service.login(
        email=payload.email,
        password=payload.password,
    )
    return TokenResponse(**result)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Retrieve profile details of the currently authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Logout confirmation endpoint.
    Client clears stored JWT bearer token.
    """
    return {
        "status": "logged_out",
        "message": f"User '{current_user.email}' logged out successfully.",
    }

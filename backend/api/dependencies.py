#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Dependency Injection.

Provee dependencias reutilizables para autenticación, rate limiting, cache, etc.
"""

from typing import Optional, Annotated
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
import time
from collections import defaultdict

from backend.api.config import settings
from backend.database.session import get_db
from backend.services.cache_service import CacheService


# Security
security = HTTPBearer()

# Rate limiting storage (in-memory for now, should use Redis in production)
rate_limit_storage: dict[str, list[float]] = defaultdict(list)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception."""
    
    def __init__(self):
        """Initialize rate limit exception."""
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(settings.rate_limit_window)}
        )


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """
    Verify JWT token and return payload.
    
    Args:
        credentials: HTTP Bearer credentials with JWT token
        
    Returns:
        Token payload dictionary
        
    Raises:
        HTTPException: If token is invalid or expired
        
    Examples:
        >>> @app.get("/protected")
        >>> async def protected_route(token_data: dict = Depends(verify_token)):
        >>>     return {"user": token_data["sub"]}
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(token_data: dict = Depends(verify_token)) -> str:
    """
    Get current authenticated user from token.
    
    Args:
        token_data: Token payload from verify_token
        
    Returns:
        User identifier (email or username)
        
    Examples:
        >>> @app.get("/me")
        >>> async def get_user(user: str = Depends(get_current_user)):
        >>>     return {"user": user}
    """
    user = token_data.get("sub")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user identifier"
        )
    return user


def check_rate_limit(
    client_id: str = Header(None, alias="X-Client-ID"),
    x_forwarded_for: str = Header(None, alias="X-Forwarded-For")
) -> None:
    """
    Check rate limiting for client.
    
    Uses sliding window algorithm. Identifies client by X-Client-ID header
    or IP address.
    
    Args:
        client_id: Client identifier from header
        x_forwarded_for: Client IP from proxy header
        
    Raises:
        RateLimitExceeded: If rate limit is exceeded
        
    Examples:
        >>> @app.get("/limited", dependencies=[Depends(check_rate_limit)])
        >>> async def limited_endpoint():
        >>>     return {"message": "Success"}
    """
    if not settings.rate_limit_enabled:
        return
    
    # Determine client identifier
    identifier = client_id or x_forwarded_for or "unknown"
    
    # Get current timestamp
    now = time.time()
    window_start = now - settings.rate_limit_window
    
    # Clean old requests
    rate_limit_storage[identifier] = [
        ts for ts in rate_limit_storage[identifier]
        if ts > window_start
    ]
    
    # Check limit
    if len(rate_limit_storage[identifier]) >= settings.rate_limit_requests:
        raise RateLimitExceeded()
    
    # Add current request
    rate_limit_storage[identifier].append(now)


def get_cache_service() -> CacheService:
    """
    Get cache service instance.
    
    Returns:
        Initialized CacheService
        
    Examples:
        >>> @app.get("/cached")
        >>> async def cached_endpoint(cache: CacheService = Depends(get_cache_service)):
        >>>     data = await cache.get("my_key")
        >>>     return data
    """
    return CacheService()


# Type aliases for common dependencies
DbDependency = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[str, Depends(get_current_user)]
CacheDependency = Annotated[CacheService, Depends(get_cache_service)]
RateLimited = Depends(check_rate_limit)


def create_access_token(user_id: str, additional_data: Optional[dict] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        user_id: User identifier (email, username, etc.)
        additional_data: Optional additional claims to include in token
        
    Returns:
        Encoded JWT token string
        
    Examples:
        >>> token = create_access_token("user@example.com", {"role": "admin"})
        >>> # Use token in Authorization: Bearer <token> header
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_data:
        payload.update(additional_data)
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return token


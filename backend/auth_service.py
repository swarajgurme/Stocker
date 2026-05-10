"""
Authentication service
Handles JWT tokens, password hashing, and user authentication
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import uuid

from flask import request, g
import jwt
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError

from database import db_session
from models import User, UserRole
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# ============= PASSWORD HASHING =============
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ============= JWT TOKEN MANAGEMENT =============
def create_access_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        user_id: User database ID
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token
    """
    payload = {
        "user_id": user_id,
        "token_type": "access",
        "exp": datetime.utcnow() + (expires_delta or config.JWT_ACCESS_TOKEN_EXPIRES),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())  # JWT ID for revocation/blacklisting
    }

    token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")
    logger.debug(f"Created access token for user {user_id}")
    return token


def create_refresh_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token

    Args:
        user_id: User database ID
        expires_delta: Token expiration time (default: 30 days)

    Returns:
        Encoded JWT token
    """
    payload = {
        "user_id": user_id,
        "token_type": "refresh",
        "exp": datetime.utcnow() + (expires_delta or config.JWT_REFRESH_TOKEN_EXPIRES),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())
    }

    token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")
    logger.debug(f"Created refresh token for user {user_id}")
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        Token payload dict if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None


def get_current_user() -> Optional[User]:
    """
    Get the current authenticated user from request context.
    Should be called within a Flask request context.

    Returns:
        User object if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    # Extract Bearer token
    parts = auth_header.split()
    if parts[0].lower() != "bearer" or len(parts) != 2:
        return None

    token = parts[1]
    payload = decode_token(token)

    if not payload or payload.get("token_type") != "access":
        return None

    user_id = payload.get("user_id")
    if not user_id:
        return None

    # Fetch user from database
    try:
        user = db_session.query(User).filter_by(id=user_id, is_active=True).first()
        if user:
            # Update last login on first use
            if not user.last_login:
                user.last_login = datetime.utcnow()
                user.login_count = 1
                db_session.commit()
            elif (datetime.utcnow() - user.last_login).total_seconds() > 300:
                # Update login count if more than 5 minutes since last login
                user.login_count += 1
                user.last_login = datetime.utcnow()
                db_session.commit()

        return user
    except SQLAlchemyError as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return None


def require_role(*roles: UserRole):
    """
    Decorator to require specific user roles.
    In TESTING mode, bypasses auth and sets a dummy admin user.
    """
    def decorator(func):
        from functools import wraps
        from flask import current_app, g

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Allow unrestricted access in testing mode
            if current_app.config.get('TESTING', False):
                # Create or fetch a dummy test user
                from database import db_session
                from models import User
                user = db_session.query(User).filter_by(email='test@test.com').first()
                if not user:
                    user = User(
                        email='test@test.com',
                        password_hash='',
                        full_name='Test User',
                        role=UserRole.ADMIN,
                        is_active=True
                    )
                    db_session.add(user)
                    db_session.commit()
                g.current_user = user
                return func(*args, **kwargs)

            # Normal authentication flow
            user = get_current_user()
            if not user:
                from flask import jsonify
                return jsonify({
                    "status": "error",
                    "error": "Authentication required",
                    "code": "AUTH_REQUIRED"
                }), 401

            if user.role not in roles:
                logger.warning(f"User {user.id} role {user.role} not in required {roles}")
                from flask import jsonify
                return jsonify({
                    "status": "error",
                    "error": "Insufficient permissions",
                    "code": "FORBIDDEN"
                }), 403

            g.current_user = user
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func):
    """Decorator requiring admin role"""
    return require_role(UserRole.ADMIN)(func)


# ============= USER MANAGEMENT =============
def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate user with email/password

    Args:
        email: User email
        password: Plain text password

    Returns:
        User object if credentials valid, None otherwise
    """
    try:
        user = db_session.query(User).filter_by(email=email, is_active=True).first()
        if not user:
            logger.warning(f"Authentication failed: user not found - {email}")
            return None

        if not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user {user.id}")
            return None

        logger.info(f"User {user.id} ({user.email}) authenticated successfully")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Database error during authentication: {str(e)}")
        return None


def create_user(
    email: str,
    password: str,
    role: UserRole = UserRole.BUSINESS_ANALYST,
    full_name: Optional[str] = None
) -> Tuple[Optional[User], Optional[str]]:
    """
    Create a new user account

    Args:
        email: User email (unique)
        password: Plain text password
        role: UserRole enum value
        full_name: Optional full name

    Returns:
        Tuple of (User object or None, error message or None)
    """
    try:
        # Check for existing user
        existing = db_session.query(User).filter_by(email=email).first()
        if existing:
            return None, "Email already registered"

        # Hash password
        password_hash = hash_password(password)

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        logger.info(f"Created user {user.id} ({email}) with role {role}")
        return user, None

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Failed to create user: {str(e)}")
        return None, "Database error"


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID"""
    try:
        return db_session.query(User).filter_by(id=user_id, is_active=True).first()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return None


def update_last_login(user_id: int):
    """Update user's last login timestamp"""
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if user:
            user.last_login = datetime.utcnow()
            db_session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Error updating login for user {user_id}: {str(e)}")


# ============= TOKEN BLACKLIST (simple in-memory for now, Redis later) =============
_blacklisted_tokens = set()


def blacklist_token(token: str):
    """Add token to blacklist (logout)"""
    _blacklisted_tokens.add(token)
    logger.info(f"Token blacklisted")


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    return token in _blacklisted_tokens


# ============= AUDIT LOGGING HELPER =============
def log_auth_action(
    user_id: Optional[int],
    action: str,
    resource_type: str = "auth",
    resource_id: Optional[str] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log authentication-related actions to audit log"""
    from models import AuditLog

    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address or request.remote_addr if request else None,
            user_agent=user_agent or request.headers.get("User-Agent") if request else None
        )
        db_session.add(audit)
        db_session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {str(e)}")

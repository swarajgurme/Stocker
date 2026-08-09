"""
Authentication Routes (Blueprint: /api/auth)
Handles user registration, login, logout, token refresh, and profile
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy.exc import SQLAlchemyError

from auth_service import (
    authenticate_user, create_user, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    decode_token_unverified_signature,
    get_current_user, require_role, UserRole, log_auth_action,
    blacklist_token,
)
from database import db_session
from models import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


# ============= USER REGISTRATION =============
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account

    Request Body:
        {
            "email": "user@example.com",
            "password": "secure_password",
            "full_name": "John Doe",  # optional
            "role": "business_analyst"  # optional, defaults to business_analyst
        }

    Response (201):
        {
            "status": "success",
            "data": {
                "user_id": 1,
                "email": "user@example.com",
                "role": "business_analyst",
                "full_name": "John Doe"
            },
            "timestamp": "2026-05-10T..."
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body required",
                "code": "INVALID_INPUT"
            }), 400

        # Extract fields
        email = str(data.get('email', '')).strip().lower()
        password = data.get('password', '')
        full_name = str(data.get('full_name', '')).strip() or None
        role_str = str(data.get('role', 'business_analyst')).strip().lower()

        # Validate
        if not email or '@' not in email:
            return jsonify({
                "status": "error",
                "error": "Valid email required",
                "code": "VALIDATION_ERROR"
            }), 400

        if len(password) < 8:
            return jsonify({
                "status": "error",
                "error": "Password must be at least 8 characters",
                "code": "VALIDATION_ERROR"
            }), 400

        if role_str == UserRole.ADMIN.value:
            return jsonify({
                "status": "error",
                "error": "Administrator accounts cannot be created via public registration",
                "code": "FORBIDDEN_ROLE",
            }), 403

        try:
            role = UserRole(role_str)
        except ValueError:
            role = UserRole.BUSINESS_ANALYST

        # Check if user exists
        existing = db_session.query(User).filter_by(email=email).first()
        if existing:
            return jsonify({
                "status": "error",
                "error": "Email already registered",
                "code": "USER_EXISTS"
            }), 409

        # Create user
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Audit log
        log_auth_action(
            user_id=user.id,
            action="user_registered",
            resource_type="user",
            resource_id=str(user.id),
            details={"email": email, "role": role.value}
        )

        logger.info(f"User registered: {email} (role: {role.value})")

        return jsonify({
            "status": "success",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "access_token": access_token,
                "refresh_token": refresh_token
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 201

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Registration DB error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Database error during registration",
            "code": "DB_ERROR"
        }), 500
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Registration failed",
            "code": "REGISTRATION_ERROR"
        }), 500


# ============= USER LOGIN =============
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login with email/password

    Request Body:
        {
            "email": "user@example.com",
            "password": "password"
        }

    Response (200):
        {
            "status": "success",
            "data": {
                "user_id": 1,
                "email": "user@example.com",
                "role": "admin",
                "access_token": "...",
                "refresh_token": "...",
                "login_count": 5
            },
            "timestamp": "2026-05-10T..."
        }

    Error Response (401):
        {
            "status": "error",
            "error": "Invalid credentials",
            "code": "INVALID_CREDENTIALS"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body required",
                "code": "INVALID_INPUT"
            }), 400

        email = str(data.get('email', '')).strip().lower()
        password = data.get('password', '')

        # Validate
        if not email or not password:
            return jsonify({
                "status": "error",
                "error": "Email and password required",
                "code": "VALIDATION_ERROR"
            }), 400

        # Authenticate
        user = authenticate_user(email, password)
        if not user:
            log_auth_action(
                user_id=None,
                action="login_failed",
                resource_type="auth",
                details={"email": email, "reason": "invalid_credentials"},
                ip_address=request.remote_addr
            )
            return jsonify({
                "status": "error",
                "error": "Invalid email or password",
                "code": "INVALID_CREDENTIALS"
            }), 401

        # Update login stats
        user.last_login = datetime.utcnow()
        user.login_count += 1
        db_session.commit()

        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Audit log
        log_auth_action(
            user_id=user.id,
            action="login_success",
            resource_type="auth",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )

        logger.info(f"User logged in: {email} (ID: {user.id})")

        return jsonify({
            "status": "success",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "login_count": user.login_count,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"Login DB error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Database error during login",
            "code": "DB_ERROR"
        }), 500
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Login failed",
            "code": "LOGIN_ERROR"
        }), 500


# ============= TOKEN REFRESH =============
@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Get new access token using refresh token

    Request Body:
        {
            "refresh_token": "..."
        }

    Response (200):
        {
            "status": "success",
            "data": {
                "access_token": "...",
                "refresh_token": "..."  # Optional: rotate refresh token
            },
            "timestamp": "2026-05-10T..."
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body required",
                "code": "INVALID_INPUT"
            }), 400

        refresh_token = data.get('refresh_token', '')
        if not refresh_token:
            return jsonify({
                "status": "error",
                "error": "Refresh token required",
                "code": "VALIDATION_ERROR"
            }), 400

        # Decode token
        payload = decode_token(refresh_token)
        if not payload or payload.get('token_type') != 'refresh':
            return jsonify({
                "status": "error",
                "error": "Invalid refresh token",
                "code": "INVALID_TOKEN"
            }), 401

        user_id = payload.get('user_id')
        if not user_id:
            return jsonify({
                "status": "error",
                "error": "Token malformed",
                "code": "INVALID_TOKEN"
            }), 401

        # Verify user still exists and is active
        user = db_session.query(User).filter_by(id=user_id, is_active=True).first()
        if not user:
            return jsonify({
                "status": "error",
                "error": "User not found or deactivated",
                "code": "USER_NOT_FOUND"
            }), 401

        # Issue new tokens
        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)  # Rotate

        log_auth_action(
            user_id=user.id,
            action="token_refreshed",
            resource_type="auth"
        )

        return jsonify({
            "status": "success",
            "data": {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Token refresh failed",
            "code": "REFRESH_ERROR"
        }), 401


# ============= LOGOUT =============
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Invalidate the current access token (server-side blacklist).
    Accepts Bearer token even when expired (signature-valid only).
    """
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.lower().startswith("bearer ") and len(auth_header.split()) == 2:
        token = auth_header.split()[1].strip()

    user_id_for_audit = None
    if token:
        blacklist_token(token)
        payload = decode_token(token) or decode_token_unverified_signature(token)
        if payload and payload.get("user_id"):
            user_id_for_audit = payload.get("user_id")

    log_auth_action(
        user_id=user_id_for_audit,
        action="logout",
        resource_type="auth",
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    return jsonify({
        "status": "success",
        "data": {"logged_out": True},
        "message": "Logged out successfully",
    }), 200


# ============= GET CURRENT USER =============
@auth_bp.route('/me', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER,
    UserRole.EXECUTIVE
)
def get_me():
    """
    Get current user profile

    Response (200):
        {
            "status": "success",
            "data": {
                "user_id": 1,
                "email": "...",
                "full_name": "...",
                "role": "admin",
                "last_login": "..."
            }
        }
    """
    user = g.current_user

    return jsonify({
        "status": "success",
        "data": {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "login_count": user.login_count,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        },
        "timestamp": datetime.utcnow().isoformat()
    }), 200


# ============= USER MANAGEMENT (ADMIN ONLY) =============
@auth_bp.route('/users', methods=['GET'])
@require_role(UserRole.ADMIN)
def list_users():
    """
    List all users (admin only)

    Query params:
        ?role=admin&active=true&limit=50&offset=0

    Response (200):
        {
            "status": "success",
            "data": {
                "users": [...],
                "total": 5
            }
        }
    """
    try:
        # Parse query params
        role_filter = request.args.get('role')
        active_filter = request.args.get('active', 'true').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        query = db_session.query(User)

        if role_filter:
            try:
                role = UserRole(role_filter)
                query = query.filter_by(role=role)
            except ValueError:
                pass

        if active_filter is not None:
            query = query.filter_by(is_active=active_filter)

        total = query.count()
        users = query.offset(offset).limit(limit).all()

        user_list = [{
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "login_count": u.login_count,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        } for u in users]

        return jsonify({
            "status": "success",
            "data": {
                "users": user_list,
                "total": total,
                "limit": limit,
                "offset": offset
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to list users",
            "code": "LIST_ERROR"
        }), 500


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_role(UserRole.ADMIN)
def update_user(user_id: int):
    """
    Update user details (admin only)

    Request Body:
        {
            "full_name": "...",
            "role": "store_manager",
            "is_active": true/false
        }

    Response (200):
        {
            "status": "success",
            "data": { updated user fields }
        }
    """
    try:
        data = request.get_json() or {}
        user = db_session.query(User).filter_by(id=user_id).first()

        if not user:
            return jsonify({
                "status": "error",
                "error": "User not found",
                "code": "NOT_FOUND"
            }), 404

        # Update fields
        if 'full_name' in data:
            user.full_name = str(data['full_name']).strip()

        if 'role' in data:
            try:
                user.role = UserRole(str(data['role']).lower())
            except ValueError:
                return jsonify({
                    "status": "error",
                    "error": "Invalid role",
                    "code": "VALIDATION_ERROR"
                }), 400

        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        if 'password' in data and data['password']:
            if len(data['password']) < 8:
                return jsonify({
                    "status": "error",
                    "error": "Password must be at least 8 characters",
                    "code": "VALIDATION_ERROR"
                }), 400
            user.password_hash = hash_password(data['password'])

        db_session.commit()

        log_auth_action(
            user_id=g.current_user.id if hasattr(g, 'current_user') else None,
            action="user_updated",
            resource_type="user",
            resource_id=str(user_id),
            details=data
        )

        return jsonify({
            "status": "success",
            "data": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Update user error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Database error",
            "code": "DB_ERROR"
        }), 500


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_role(UserRole.ADMIN)
def delete_user(user_id: int):
    """
    Soft delete user (set is_active=False)

    Response (204):
        No content
    """
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({
                "status": "error",
                "error": "User not found",
                "code": "NOT_FOUND"
            }), 404

        user.is_active = False
        db_session.commit()

        log_auth_action(
            user_id=g.current_user.id if hasattr(g, 'current_user') else None,
            action="user_deleted",
            resource_type="user",
            resource_id=str(user_id)
        )

        return '', 204

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Delete user error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Database error",
            "code": "DB_ERROR"
        }), 500

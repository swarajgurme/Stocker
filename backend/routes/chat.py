"""
Chatbot API Routes (Blueprint: /api/chat)
AI Copilot for Multilingual Inventory & Supply Chain Intelligence
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from database import get_db_session
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('', methods=['POST'])
@chat_bp.route('/', methods=['POST'])
def handle_chat_message():
    """
    POST /api/chat
    Request Body:
    {
        "message": "Which products are low on stock?",
        "history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        message = data.get('message', '').strip()

        if not message:
            return jsonify({
                "status": "error",
                "error": "Message cannot be empty",
                "code": "EMPTY_MESSAGE"
            }), 400

        history = data.get('history', [])
        client_key = request.headers.get('x-gemini-api-key') or data.get('gemini_api_key')

        with get_db_session() as db:
            service = ChatService(db, gemini_api_key=client_key)
            result = service.chat(user_message=message, history=history)

            return jsonify({
                "status": "success",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": "Failed to process chat message",
            "details": str(e),
            "code": "CHAT_ERROR"
        }), 500


@chat_bp.route('/status', methods=['GET'])
def get_chat_status():
    """
    GET /api/chat/status
    Returns status of AI engines and live system context summary
    """
    try:
        has_gemini = bool(os.getenv("GEMINI_API_KEY"))
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_groq = bool(os.getenv("GROQ_API_KEY"))

        with get_db_session() as db:
            service = ChatService(db)
            context = service.get_live_system_context()

            return jsonify({
                "status": "success",
                "data": {
                    "online": True,
                    "providers": {
                        "gemini": has_gemini,
                        "openai": has_openai,
                        "groq": has_groq,
                        "local_semantic": True
                    },
                    "active_provider": "gemini" if has_gemini else ("openai" if has_openai else "local_semantic"),
                    "supported_languages": [
                        "English", "हिन्दी (Hindi)", "मराठी (Marathi)", 
                        "Español", "Français", "Deutsch", "中文 (Chinese)", 
                        "العربية (Arabic)", "Any Language"
                    ],
                    "system_summary": {
                        "total_products": context.get("total_products", 20),
                        "total_stores": context.get("total_stores", 5),
                        "low_stock_count": context.get("low_stock_count", 0),
                        "active_transfers": context.get("active_transfers_count", 0),
                        "procurement_alerts": context.get("procurement_alerts_count", 0)
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200
    except Exception as e:
        logger.error(f"Chat status error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve chat status",
            "code": "STATUS_ERROR"
        }), 500

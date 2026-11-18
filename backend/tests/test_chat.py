"""
Unit Tests for AI Chatbot API & Multilingual Intelligence
"""

import pytest
from app import create_app
from database import init_db


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_chat_status_endpoint(client):
    """Verify /api/chat/status returns online status and available providers"""
    res = client.get("/api/chat/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["data"]["online"] is True
    assert "local_semantic" in data["data"]["providers"]
    assert "supported_languages" in data["data"]


def test_chat_message_english(client):
    """Verify chatbot responds accurately to low stock query in English"""
    res = client.post("/api/chat", json={"message": "Which products are low on stock?"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reply" in data["data"]
    assert len(data["data"]["reply"]) > 20


def test_chat_message_hindi(client):
    """Verify chatbot understands and responds in Hindi"""
    res = client.post("/api/chat", json={"message": "स्टॉक कितना बचा है और कम स्टॉक वाले पार्ट्स बताओ"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reply" in data["data"]
    assert ("स्टॉक" in data["data"]["reply"] or "स्टॉकर" in data["data"]["reply"])


def test_chat_message_marathi(client):
    """Verify chatbot understands and responds in Marathi"""
    res = client.post("/api/chat", json={"message": "स्टॉकर प्रोजेक्ट काय करतो माहिती सांगा"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reply" in data["data"]
    assert ("स्टॉकर" in data["data"]["reply"] or "माहिती" in data["data"]["reply"])


def test_chat_empty_message_validation(client):
    """Verify 400 error when sending empty message"""
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400
    data = res.get_json()
    assert data["code"] == "EMPTY_MESSAGE"

import pytest
import json
from unittest.mock import MagicMock, patch
from flask_jwt_extended import create_access_token
from app import create_app, db
from app.config import TestingConfig
from app.models import Mall, Offer, Store, User, Category, Admin
from app.models.analytics import UserEvent, VisitorSession


class AdminAITestingConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'


@pytest.fixture()
def app():
    application = create_app(AdminAITestingConfig)
    application.config.update(TESTING=True)
    with application.app_context():
        db.drop_all()
        db.create_all()

        mall = Mall(name="Test Mall", city="City", address="Address", operating_hours={})
        db.session.add(mall)
        db.session.commit()

        cat = Category(name="Food", icon="🍔", description="F&B")
        db.session.add(cat)
        db.session.commit()

        store = Store(name="KFC", mall_id=mall.id, category_id=cat.id, floor="1", unit="101", status="open")
        db.session.add(store)
        db.session.commit()

        user = User(name='User One', email='user@test.local', password_hash='hash')
        db.session.add(user)

        admin = Admin(name='Admin One', email='admin@test.local', password_hash='hash', role='admin', is_active=True)
        db.session.add(admin)
        db.session.commit()

        application.test_mall_id = mall.id
        application.test_store_id = store.id
        application.test_user_id = user.id
        application.test_admin_id = admin.id

        yield application

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_headers(app):
    with app.app_context():
        token = create_access_token(identity=app.test_admin_id, additional_claims={"role": "admin", "is_admin": True})
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def user_headers(app):
    with app.app_context():
        token = create_access_token(identity=app.test_user_id)
    return {'Authorization': f'Bearer {token}'}


# Helper class to mock Gemini GenerateContent response
class MockGeminiResponse:
    def __init__(self, text="", function_calls=None):
        self.text = text
        self.function_calls = function_calls


class MockFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


def test_admin_authentication_and_security(client, user_headers, admin_headers):
    # 1. No JWT
    res = client.post('/api/admin/ai/chat', json={"message": "What is the store count?"})
    assert res.status_code == 401

    # 2. Non-admin user rejection
    res = client.post('/api/admin/ai/chat', json={"message": "What is the store count?"}, headers=user_headers)
    assert res.status_code == 403

    # 3. Message validation
    res = client.post('/api/admin/ai/chat', json={}, headers=admin_headers)
    assert res.status_code == 400


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_overview_question_and_tool_invocation(mock_get_client, client, admin_headers):
    # Mock Gemini client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Define first turn: model requests tool get_overview_analytics
    fc = MockFunctionCall(name="get_overview_analytics", args={"period": "30d"})
    res1 = MockGeminiResponse(text="", function_calls=[fc])

    # Define second turn: model returns final text answer
    final_text = "INSIGHT\nThe mall had steady visitor count today.\n\nEVIDENCE\n- Sessions count: 0\n\nINTERPRETATION\nNothing unusual.\n\nRECOMMENDED ACTION\nNo action recommended.\n\nCONFIDENCE\nHigh"
    res2 = MockGeminiResponse(text=final_text)

    # Mock responses sequentially
    mock_client.models.generate_content.side_effect = [res1, res2]

    # POST request
    res = client.post('/api/admin/ai/chat', json={"message": "Show overview metrics"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()

    # Verify response structure and tool usage
    assert "INSIGHT" in data['answer']
    assert "get_overview_analytics" in data['tools_used']
    assert data['confidence'] == "high"
    assert len(data['evidence']) == 1
    assert data['evidence'][0]['tool'] == "get_overview_analytics"


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_multi_tool_invocation(mock_get_client, client, admin_headers):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # First turn: Gemini requests get_store_performance and get_category_demand
    fc1 = MockFunctionCall(name="get_store_performance", args={"period": "7d"})
    fc2 = MockFunctionCall(name="get_category_demand", args={"period": "7d"})
    res1 = MockGeminiResponse(text="", function_calls=[fc1, fc2])

    # Second turn: Final explanation
    final_text = "INSIGHT\nInsights on category demand.\n\nEVIDENCE\n- Food demand is high.\n\nINTERPRETATION\nPeople love food.\n\nRECOMMENDED ACTION\nAdd another cafe.\n\nCONFIDENCE\nMedium"
    res2 = MockGeminiResponse(text=final_text)

    mock_client.models.generate_content.side_effect = [res1, res2]

    res = client.post('/api/admin/ai/chat', json={"message": "Compare food category and store performance"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()

    assert "get_store_performance" in data['tools_used']
    assert "get_category_demand" in data['tools_used']
    assert data['confidence'] == "medium"
    assert len(data['evidence']) == 2


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_empty_analytics_dataset(mock_get_client, client, admin_headers):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # First turn: get_offer_performance
    fc = MockFunctionCall(name="get_offer_performance", args={"period": "30d"})
    res1 = MockGeminiResponse(text="", function_calls=[fc])

    # Second turn: Gemini indicates insufficient data
    insufficient_text = "Insufficient MallBuddy data to make a reliable recommendation."
    res2 = MockGeminiResponse(text=insufficient_text)

    mock_client.models.generate_content.side_effect = [res1, res2]

    res = client.post('/api/admin/ai/chat', json={"message": "What is the CTR for active offers?"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()

    assert "Insufficient MallBuddy data" in data['answer']
    assert data['confidence'] == "low"


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_gemini_failure_handling(mock_get_client, client, admin_headers):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Gemini model generation fails
    mock_client.models.generate_content.side_effect = Exception("API connection timed out")

    res = client.post('/api/admin/ai/chat', json={"message": "Tell me about visitor trends"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "Error calling Gemini AI" in data['answer']
    assert data['confidence'] == 'low'


@patch('app.services.admin_ai.graph.get_gemini_client')
@patch('app.services.analytics_service.get_demand_signals')
def test_analytics_tool_failure_handling(mock_get_demand, mock_get_client, client, admin_headers):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Mock demand signals service method to raise an exception
    mock_get_demand.side_effect = Exception("Database connection failed")

    # Turn 1: Gemini calls get_demand_signals
    fc = MockFunctionCall(name="get_demand_signals", args={"period": "30d"})
    res1 = MockGeminiResponse(text="", function_calls=[fc])

    # Turn 2: Gemini explains failure
    final_text = "INSIGHT\nWe could not query demand signals.\n\nEVIDENCE\n- Error: invalid format\n\nINTERPRETATION\nFailure.\n\nRECOMMENDED ACTION\nNone.\n\nCONFIDENCE\nLow"
    res2 = MockGeminiResponse(text=final_text)

    mock_client.models.generate_content.side_effect = [res1, res2]

    # In our tools.py, if get_demand_signals throws exception, it returns error json string
    res = client.post('/api/admin/ai/chat', json={"message": "Show demand signals"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "get_demand_signals" in data['tools_used']
    assert "error" in data['evidence'][0]['result']


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_unsupported_question(mock_get_client, client, admin_headers):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # If question is completely unrelated (e.g. "Write a poem"), Gemini returns answer directly without tool calls
    direct_res = MockGeminiResponse(text="INSIGHT\nThis is unrelated to MallBuddy.\n\nCONFIDENCE\nLow")
    mock_client.models.generate_content.return_value = direct_res

    res = client.post('/api/admin/ai/chat', json={"message": "What is the capital of France?"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['tools_used'] == []
    assert data['evidence'] == []


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3.3 — Observability tests
# ─────────────────────────────────────────────────────────────────────────────

@patch('app.services.admin_ai.graph.get_gemini_client')
def test_single_tool_name_present_in_tools_used(mock_get_client, client, admin_headers):
    """One-tool query: tools_used must contain the actual tool name that executed."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    fc = MockFunctionCall(name="get_store_performance", args={"period": "today"})
    res1 = MockGeminiResponse(text="", function_calls=[fc])
    final_text = (
        "INSIGHT\nZara leads today.\n\nEVIDENCE\n- Zara: 1 view.\n\n"
        "INTERPRETATION\nLow data.\n\nRECOMMENDED ACTION\nNone.\n\nCONFIDENCE\nLow"
    )
    res2 = MockGeminiResponse(text=final_text)
    mock_client.models.generate_content.side_effect = [res1, res2]

    res = client.post('/api/admin/ai/chat', json={"message": "Which stores are most visited?"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()

    # The actual executed tool name must appear in tools_used — not hardcoded
    assert "get_store_performance" in data['tools_used'], (
        f"Expected 'get_store_performance' in tools_used, got: {data['tools_used']}"
    )
    assert len(data['tools_used']) == 1
    assert len(data['evidence']) == 1
    assert data['evidence'][0]['tool'] == "get_store_performance"


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_multi_tool_all_names_in_tools_used(mock_get_client, client, admin_headers):
    """Multi-tool query: tools_used must contain ALL tool names that executed."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    fc1 = MockFunctionCall(name="get_visitor_analytics", args={"period": "7d"})
    fc2 = MockFunctionCall(name="get_offer_performance", args={"period": "7d"})
    fc3 = MockFunctionCall(name="get_navigation_analytics", args={"period": "7d"})
    res1 = MockGeminiResponse(text="", function_calls=[fc1, fc2, fc3])
    final_text = (
        "INSIGHT\nMultiple metrics checked.\n\nEVIDENCE\n- See data.\n\n"
        "INTERPRETATION\nLow traffic.\n\nRECOMMENDED ACTION\nNone.\n\nCONFIDENCE\nMedium"
    )
    res2 = MockGeminiResponse(text=final_text)
    mock_client.models.generate_content.side_effect = [res1, res2]

    res = client.post(
        '/api/admin/ai/chat',
        json={"message": "Give me visitors, offers, and navigation data"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.get_json()

    for expected_tool in ("get_visitor_analytics", "get_offer_performance", "get_navigation_analytics"):
        assert expected_tool in data['tools_used'], (
            f"Expected '{expected_tool}' in tools_used, got: {data['tools_used']}"
        )
    assert len(data['tools_used']) == 3
    assert len(data['evidence']) == 3
    # Verify evidence tool keys match tools_used (no fabrication)
    evidence_tools = {e['tool'] for e in data['evidence']}
    assert evidence_tools == set(data['tools_used'])


@patch('app.services.admin_ai.graph.get_gemini_client')
@patch('app.services.analytics_service.get_navigation')
def test_failed_tool_execution_still_tracked_in_tools_used(
    mock_get_nav, mock_get_client, client, admin_headers
):
    """Failed tool: must appear in tools_used and evidence must contain the error."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_get_nav.side_effect = Exception("DB timeout")

    fc = MockFunctionCall(name="get_navigation_analytics", args={"period": "30d"})
    res1 = MockGeminiResponse(text="", function_calls=[fc])
    final_text = (
        "INSIGHT\nNavigation query failed.\n\nEVIDENCE\n- Error: DB timeout.\n\n"
        "INTERPRETATION\nUnavailable.\n\nRECOMMENDED ACTION\nRetry later.\n\nCONFIDENCE\nLow"
    )
    res2 = MockGeminiResponse(text=final_text)
    mock_client.models.generate_content.side_effect = [res1, res2]

    res = client.post('/api/admin/ai/chat', json={"message": "Navigation data please"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()

    # Failed tool must still be listed — not silently dropped
    assert "get_navigation_analytics" in data['tools_used'], (
        f"Failed tool missing from tools_used: {data['tools_used']}"
    )
    assert len(data['evidence']) == 1
    assert "error" in data['evidence'][0]['result']


@patch('app.services.admin_ai.graph.get_gemini_client')
def test_evidence_corresponds_to_executed_tools(mock_get_client, client, admin_headers):
    """Evidence items must match the tools that ran; no fabricated or extra entries."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    fc1 = MockFunctionCall(name="get_overview_analytics", args={"period": "today"})
    fc2 = MockFunctionCall(name="get_category_demand", args={"period": "today"})
    res1 = MockGeminiResponse(text="", function_calls=[fc1, fc2])
    final_text = (
        "INSIGHT\nOverview and categories.\n\nEVIDENCE\n- Data available.\n\n"
        "INTERPRETATION\nSmall dataset.\n\nRECOMMENDED ACTION\nNone.\n\nCONFIDENCE\nLow"
    )
    res2 = MockGeminiResponse(text=final_text)
    mock_client.models.generate_content.side_effect = [res1, res2]

    res = client.post(
        '/api/admin/ai/chat',
        json={"message": "Overview and categories for today"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.get_json()

    # Exactly two evidence items, one per tool called
    assert len(data['evidence']) == 2
    evidence_tool_names = [e['tool'] for e in data['evidence']]
    assert "get_overview_analytics" in evidence_tool_names
    assert "get_category_demand" in evidence_tool_names

    # No tool names in tools_used that don't appear in evidence
    evidence_tool_set = set(evidence_tool_names)
    for tool in data['tools_used']:
        assert tool in evidence_tool_set, (
            f"tools_used contains '{tool}' but it has no matching evidence entry"
        )


import pytest
import math
from app import create_app, db
from app.config import TestingConfig
from app.services.navigation.astar import NavigationGraph, get_layout_data, calculate_astar_route, Node
from app.models import Store, Route, Mall, Category

class NavTestingConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'

@pytest.fixture
def app():
    application = create_app(NavTestingConfig)
    application.config.update(TESTING=True)
    with application.app_context():
        db.drop_all()
        db.create_all()
        mall = Mall(name="Test Mall", city="City", address="Address", operating_hours={})
        db.session.add(mall)
        cat = Category(name="Fashion", icon="👗", description="F")
        db.session.add(cat)
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_database(app):
    with app.app_context():
        yield db

@pytest.fixture
def layout_data():
    return get_layout_data()

@pytest.fixture
def graph(layout_data):
    return NavigationGraph(layout_data)

def test_basic_shortest_path(graph):
    route = calculate_astar_route(graph, "Zara", "H&M")
    assert route is not None
    assert route["from"]["name"] == "Zara"
    assert route["to"]["name"] == "H&M"
    assert len(route["floors"]) == 1
    assert route["floors"][0]["floor"] == "1"
    
    dist = route["totalDistance"]
    assert 230 <= dist <= 250, f"Expected around 240, got {dist}"

def test_same_source_destination(graph):
    route = calculate_astar_route(graph, "Starbucks", "Starbucks")
    assert route is not None
    assert route["totalDistance"] == 0
    assert route["estimatedTime"] == 0
    assert "already at" in route["steps"][-1]
    assert len(route["floors"]) == 1
    assert len(route["floors"][0]["path"]) == 1

def test_multi_floor_routing(graph):
    route = calculate_astar_route(graph, "Main Entrance", "Adidas")
    assert route is not None
    assert len(route["floors"]) == 2
    assert route["floors"][0]["floor"] == "1"
    assert route["floors"][1]["floor"] == "2"
    assert "Take escalator to Floor 2" in route["steps"]
    
def test_actual_mallbuddy_route(graph):
    route = calculate_astar_route(graph, "Main Entrance", "PVR Cinemas")
    assert route is not None
    assert len(route["floors"]) == 4
    assert route["floors"][0]["floor"] == "1"
    assert route["floors"][-1]["floor"] == "4"
    assert "Take escalator to Floor 4" in route["steps"]
    assert route["totalDistance"] > 0

def test_unreachable_destination(graph):
    unreachable_node = Node("1", -100, -100, "Secret Room")
    graph.add_node(unreachable_node)
    graph.store_nodes["secret room"] = unreachable_node
    
    route = calculate_astar_route(graph, "Main Entrance", "Secret Room")
    assert route is None

def test_competing_paths(graph):
    n_entrance = graph.find_node_by_name("Main Entrance")
    n_zara = graph.find_node_by_name("Zara")
    
    n_shortcut = Node("1", 200, 300, "Shortcut")
    graph.add_node(n_shortcut)
    graph.add_edge(n_entrance, n_shortcut, 10.0)
    graph.add_edge(n_shortcut, n_zara, 10.0)
    
    route = calculate_astar_route(graph, "Main Entrance", "Zara")
    assert route is not None
    assert route["totalDistance"] == 20

def test_api_response_compatibility(client, app, init_database):
    with app.app_context():
        response = client.get('/api/navigation/?from=Main Entrance&to=PVR Cinemas')
        assert response.status_code == 200
        data = response.get_json()
        assert "route" in data
        route = data["route"]
        assert "from" in route
        assert "to" in route
        assert "floors" in route
        assert "totalDistance" in route
        assert "estimatedTime" in route
        assert "steps" in route
        
def test_astar_failure_fallback(client, app, monkeypatch, init_database):
    def mock_astar(*args, **kwargs):
        raise Exception("A* simulated failure")
    
    from app.routes import navigation
    monkeypatch.setattr(navigation, "calculate_astar_route", mock_astar)
    
    with app.app_context():
        # Zara must exist in DB for fallback to work
        zara = Store.query.filter_by(name="Zara").first()
        if not zara:
            zara = Store(name="Zara", unit="105", floor="1", status="open", mall_id=1, category_id=1)
            db.session.add(zara)
            db.session.commit()
            
        response = client.get('/api/navigation/?from=Main Entrance&to=Zara')
        assert response.status_code == 200
        data = response.get_json()
        route = data["route"]
        assert route["distance_meters"] == 50

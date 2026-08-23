from datetime import date, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app import create_app, db
from app.config import TestingConfig
from app.models import Mall, Offer, Store, User, UserEvent, VisitorSession


class AnalyticsTestingConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'


@pytest.fixture()
def app():
    application = create_app(AnalyticsTestingConfig)
    application.config.update(TESTING=True)
    with application.app_context():
        mall = Mall.query.first()
        store = Store.query.first()
        user = User(name='Tracked User', email='tracked@example.test', password_hash='unused')
        db.session.add(user)
        db.session.commit()
        offer = Offer(
            store_id=store.id,
            title='Tracked offer',
            description='Offer used by tracking tests',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            is_active=True,
        )
        db.session.add(offer)
        db.session.commit()
        application.test_mall_id = mall.id
        application.test_store_id = store.id
        application.test_offer_id = offer.id
        application.test_user_id = user.id
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def start_session(client, mall_id):
    response = client.post('/api/tracking/session', json={'mall_id': mall_id})
    assert response.status_code == 201
    return response.get_json()['session_id']


def test_creates_anonymous_visitor_session(app, client):
    token = start_session(client, app.test_mall_id)
    with app.app_context():
        session = VisitorSession.query.filter_by(session_token=token).one()
        assert session.mall_id == app.test_mall_id
        assert session.user_id is None
        assert session.is_guest is True


def test_creates_anonymous_store_search_event(app, client):
    token = start_session(client, app.test_mall_id)
    response = client.post('/api/tracking/event', json={
        'event_type': 'store_search', 'mall_id': app.test_mall_id,
        'session_id': token, 'search_query': 'cafe', 'metadata': {},
    })
    assert response.status_code == 201
    with app.app_context():
        event = UserEvent.query.one()
        assert event.event_type == 'store_search'
        assert event.search_query == 'cafe'
        assert event.user_id is None
        assert event.is_synthetic is False


def test_creates_logged_in_event_from_jwt(app, client):
    with app.app_context():
        access_token = create_access_token(identity=app.test_user_id)
    token = start_session(client, app.test_mall_id)
    response = client.post('/api/tracking/event', headers={'Authorization': f'Bearer {access_token}'}, json={
        'event_type': 'store_view', 'mall_id': app.test_mall_id,
        'session_id': token, 'store_id': app.test_store_id, 'metadata': {},
    })
    assert response.status_code == 201
    with app.app_context():
        assert UserEvent.query.one().user_id == app.test_user_id


def test_records_ai_query_and_offer_click(app, client):
    token = start_session(client, app.test_mall_id)
    ai_response = client.post('/api/tracking/event', json={
        'event_type': 'ai_query', 'mall_id': app.test_mall_id,
        'session_id': token, 'search_query': 'Where is the cinema?', 'metadata': {},
    })
    offer_response = client.post('/api/tracking/event', json={
        'event_type': 'offer_click', 'mall_id': app.test_mall_id,
        'session_id': token, 'offer_id': app.test_offer_id, 'metadata': {},
    })
    assert ai_response.status_code == 201
    assert offer_response.status_code == 201
    with app.app_context():
        assert {event.event_type for event in UserEvent.query.all()} == {'ai_query', 'offer_click'}


def test_rejects_invalid_event(app, client):
    token = start_session(client, app.test_mall_id)
    response = client.post('/api/tracking/event', json={
        'event_type': 'delete_everything', 'mall_id': app.test_mall_id,
        'session_id': token, 'metadata': {'is_synthetic': True},
    })
    assert response.status_code == 400
    with app.app_context():
        assert UserEvent.query.count() == 0


def test_tracking_failure_does_not_break_store_read(app, client, monkeypatch):
    import app.routes.tracking as tracking_route

    token = start_session(client, app.test_mall_id)
    monkeypatch.setattr(tracking_route, 'track_event', lambda **kwargs: None)
    tracking_response = client.post('/api/tracking/event', json={
        'event_type': 'store_search', 'mall_id': app.test_mall_id,
        'session_id': token, 'search_query': 'fashion', 'metadata': {},
    })
    store_response = client.get(f'/api/stores/?mall_id={app.test_mall_id}')
    assert tracking_response.status_code == 503
    assert store_response.status_code == 200
    assert store_response.get_json()['count'] > 0


def test_ends_visitor_session(app, client):
    token = start_session(client, app.test_mall_id)
    response = client.post('/api/tracking/session/end', json={
        'mall_id': app.test_mall_id, 'session_id': token,
    })
    assert response.status_code == 200
    with app.app_context():
        assert VisitorSession.query.filter_by(session_token=token).one().ended_at is not None

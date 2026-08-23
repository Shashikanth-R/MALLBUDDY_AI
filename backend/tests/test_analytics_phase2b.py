import pytest
from datetime import datetime, timedelta, date
from flask_jwt_extended import create_access_token
from app import create_app, db
from app.config import TestingConfig
from app.models import Mall, Offer, Store, User, Category, Admin
from app.models.analytics import UserEvent, VisitorSession


class AnalyticsTestingConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'


@pytest.fixture()
def app():
    application = create_app(AnalyticsTestingConfig)
    application.config.update(TESTING=True)
    with application.app_context():
        # Setup initial DB structure
        db.drop_all()
        db.create_all()

        mall = Mall(name="Elements Mall", city="Bangalore", address="123 MG Road", operating_hours={})
        db.session.add(mall)
        db.session.commit()

        cat = Category(name="Fashion", icon="👗", description="Fashion category")
        db.session.add(cat)
        db.session.commit()

        store = Store(name="Zara", mall_id=mall.id, category_id=cat.id, floor="1", unit="105", status="open")
        db.session.add(store)
        db.session.commit()

        user = User(name='Tracked User', email='tracked@example.test', password_hash='unused')
        db.session.add(user)
        
        admin = Admin(name='Admin User', email='admin@example.test', password_hash='unused', role='admin')
        db.session.add(admin)
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
        application.test_admin_id = admin.id
        application.test_category_id = cat.id

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


def test_auth_protection(client, user_headers):
    # Missing authorization header
    res = client.get('/api/admin/analytics/overview')
    assert res.status_code == 401

    # Unauthorized non-admin user
    res = client.get('/api/admin/analytics/overview', headers=user_headers)
    assert res.status_code == 403


def test_overview_empty_handling(client, admin_headers):
    res = client.get('/api/admin/analytics/overview', headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['total_sessions'] == 0
    assert data['unique_visitors'] == 0
    assert data['total_events'] == 0
    assert data['store_views'] == 0


def test_invalid_date_range(client, admin_headers):
    # start_date > end_date
    res = client.get('/api/admin/analytics/overview?start_date=2026-08-23&end_date=2026-08-22', headers=admin_headers)
    assert res.status_code == 400
    assert 'before' in res.get_json()['error']

    # Date range exceeds 1 year
    res = client.get('/api/admin/analytics/overview?start_date=2024-08-23&end_date=2026-08-23', headers=admin_headers)
    assert res.status_code == 400
    assert 'exceed' in res.get_json()['error']


def test_analytics_calculations(app, client, admin_headers):
    # Seed visitor sessions and events
    with app.app_context():
        # User session
        sess = VisitorSession(session_token="session1", mall_id=app.test_mall_id, user_id=app.test_user_id, is_guest=False)
        db.session.add(sess)
        db.session.commit()

        # Real store view event
        ev1 = UserEvent(
            session_id=sess.id,
            user_id=app.test_user_id,
            mall_id=app.test_mall_id,
            event_type='store_view',
            store_id=app.test_store_id,
            is_synthetic=False
        )
        db.session.add(ev1)

        # Synthetic store view event (should be ignored)
        ev2 = UserEvent(
            session_id=sess.id,
            user_id=app.test_user_id,
            mall_id=app.test_mall_id,
            event_type='store_view',
            store_id=app.test_store_id,
            is_synthetic=True
        )
        db.session.add(ev2)

        # Search event
        ev3 = UserEvent(
            session_id=sess.id,
            user_id=app.test_user_id,
            mall_id=app.test_mall_id,
            event_type='store_search',
            category_id=app.test_category_id,
            is_synthetic=False
        )
        db.session.add(ev3)

        # AI query event
        ev4 = UserEvent(
            session_id=sess.id,
            user_id=app.test_user_id,
            mall_id=app.test_mall_id,
            event_type='ai_query',
            search_query='Find Zara store',
            is_synthetic=False
        )
        db.session.add(ev4)

        # Recommendation view event
        ev5 = UserEvent(
            session_id=sess.id,
            user_id=app.test_user_id,
            mall_id=app.test_mall_id,
            event_type='recommendation_view',
            metadata_={'type': 'fashion'},
            is_synthetic=False
        )
        db.session.add(ev5)

        # Offer click event
        ev6 = UserEvent(
            session_id=sess.id,
            user_id=app.test_user_id,
            mall_id=app.test_mall_id,
            event_type='offer_click',
            offer_id=app.test_offer_id,
            is_synthetic=False
        )
        db.session.add(ev6)

        db.session.commit()

    # Query overview
    res = client.get('/api/admin/analytics/overview', headers=admin_headers)
    assert res.status_code == 200
    overview = res.get_json()
    assert overview['total_sessions'] == 1
    assert overview['unique_visitors'] == 1
    assert overview['total_events'] == 5 # excluding synthetic
    assert overview['store_views'] == 1
    assert overview['store_searches'] == 1
    assert overview['offer_clicks'] == 1

    # Query visitors
    res = client.get('/api/admin/analytics/visitors', headers=admin_headers)
    assert res.status_code == 200
    visitors = res.get_json()
    assert visitors['unique_visitors'] == 1
    assert visitors['new_sessions'] == 1
    assert visitors['returning_visitors'] == 0

    # Query categories
    res = client.get('/api/admin/analytics/categories', headers=admin_headers)
    assert res.status_code == 200
    cats = res.get_json()
    assert len(cats) > 0
    assert cats[0]['category'] == 'Fashion'

    # Query stores
    res = client.get('/api/admin/analytics/stores', headers=admin_headers)
    assert res.status_code == 200
    stores = res.get_json()
    assert len(stores) > 0
    assert stores[0]['store_name'] == 'Zara'
    assert stores[0]['store_views'] == 1

    # Query offers
    res = client.get('/api/admin/analytics/offers', headers=admin_headers)
    assert res.status_code == 200
    offers = res.get_json()
    assert len(offers) > 0
    assert offers[0]['clicks'] == 1

    # Query navigation
    res = client.get('/api/admin/analytics/navigation', headers=admin_headers)
    assert res.status_code == 200
    nav = res.get_json()
    assert 'total_navigation_requests' in nav

    # Query AI queries
    res = client.get('/api/admin/analytics/ai-queries', headers=admin_headers)
    assert res.status_code == 200
    ai = res.get_json()
    assert ai['total_ai_queries'] == 1
    assert len(ai['popular_questions']) > 0
    assert ai['popular_questions'][0]['query'] == 'find zara store'

    # Query recommendations
    res = client.get('/api/admin/analytics/recommendations', headers=admin_headers)
    assert res.status_code == 200
    recs = res.get_json()
    assert recs['total_views'] == 1
    assert len(recs['performance_by_type']) > 0
    assert recs['performance_by_type'][0]['recommendation_type'] == 'fashion'

    # Query demand
    res = client.get('/api/admin/analytics/demand', headers=admin_headers)
    assert res.status_code == 200
    demand = res.get_json()
    assert len(demand) > 0
    assert 'signal' in demand[0]

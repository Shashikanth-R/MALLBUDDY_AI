"""Centralized business intelligence analytics service for MallBuddy."""
from datetime import datetime
from sqlalchemy import func, desc
from app import db
from app.models import Category, Offer, Store, VisitorSession
from app.models.analytics import UserEvent


def get_overview(start_date, end_date):
    """Calculate overview analytics for the selected period."""
    total_sessions = db.session.query(func.count(VisitorSession.id)).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date
    ).scalar() or 0

    unique_visitors = db.session.query(
        func.count(func.distinct(func.coalesce(VisitorSession.user_id, VisitorSession.session_token)))
    ).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date
    ).scalar() or 0

    total_events = db.session.query(func.count(UserEvent.id)).filter(
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).scalar() or 0

    event_counts = db.session.query(
        UserEvent.event_type,
        func.count(UserEvent.id)
    ).filter(
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.event_type).all()

    counts_dict = {et: cnt for et, cnt in event_counts}

    return {
        'total_sessions': total_sessions,
        'unique_visitors': unique_visitors,
        'total_events': total_events,
        'store_searches': counts_dict.get('store_search', 0),
        'store_views': counts_dict.get('store_view', 0),
        'navigation_requests': counts_dict.get('navigation_request', 0),
        'offer_views': counts_dict.get('offer_view', 0),
        'offer_clicks': counts_dict.get('offer_click', 0),
        'ai_queries': counts_dict.get('ai_query', 0),
        'recommendation_views': counts_dict.get('recommendation_view', 0),
        'recommendation_clicks': counts_dict.get('recommendation_click', 0)
    }


def get_visitors(start_date, end_date):
    """Calculate detailed visitor analytics."""
    unique_visitors = db.session.query(
        func.count(func.distinct(func.coalesce(VisitorSession.user_id, VisitorSession.session_token)))
    ).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date
    ).scalar() or 0

    total_sessions = db.session.query(func.count(VisitorSession.id)).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date
    ).scalar() or 0

    first_sessions_sub = db.session.query(
        func.min(VisitorSession.started_at).label('first_started')
    ).group_by(
        func.coalesce(VisitorSession.user_id, VisitorSession.session_token)
    ).subquery()

    new_sessions = db.session.query(func.count()).select_from(first_sessions_sub).filter(
        first_sessions_sub.c.first_started >= start_date,
        first_sessions_sub.c.first_started <= end_date
    ).scalar() or 0

    returning_visitors = max(0, unique_visitors - new_sessions)

    if db.engine.dialect.name == 'sqlite':
        diff_expr = (func.julianday(VisitorSession.ended_at) - func.julianday(VisitorSession.started_at)) * 86400
    else:
        diff_expr = func.extract('epoch', VisitorSession.ended_at - VisitorSession.started_at)

    avg_duration = db.session.query(
        func.avg(diff_expr)
    ).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date,
        VisitorSession.ended_at != None
    ).scalar() or 0.0

    daily_stats = db.session.query(
        func.date(VisitorSession.started_at).label('date'),
        func.count(func.distinct(func.coalesce(VisitorSession.user_id, VisitorSession.session_token))).label('visitors'),
        func.count(VisitorSession.id).label('sessions')
    ).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date
    ).group_by(func.date(VisitorSession.started_at)).order_by('date').all()

    daily_trend = [
        {'date': str(row.date), 'unique_visitors': row.visitors, 'sessions': row.sessions}
        for row in daily_stats
    ]

    if db.engine.dialect.name == 'sqlite':
        hour_expr = func.cast(func.strftime('%H', VisitorSession.started_at), db.Integer)
    else:
        hour_expr = func.cast(func.extract('hour', VisitorSession.started_at), db.Integer)

    hour_stats = db.session.query(
        hour_expr.label('hour'),
        func.count(VisitorSession.id).label('sessions')
    ).filter(
        VisitorSession.started_at >= start_date,
        VisitorSession.started_at <= end_date
    ).group_by('hour').order_by('hour').all()

    hourly_activity = {row.hour: row.sessions for row in hour_stats}
    hourly_trend = [{'hour': h, 'sessions': hourly_activity.get(h, 0)} for h in range(24)]

    return {
        'unique_visitors': unique_visitors,
        'total_sessions': total_sessions,
        'new_sessions': new_sessions,
        'returning_visitors': returning_visitors,
        'average_session_duration': round(float(avg_duration), 1),
        'daily_visitor_trend': daily_trend,
        'hourly_activity': hourly_trend
    }


def get_categories(start_date, end_date):
    """Rank mall categories based on search count and views demand."""
    searches = db.session.query(
        UserEvent.category_id,
        func.count(UserEvent.id).label('search_count'),
        func.count(func.distinct(UserEvent.session_id)).label('unique_visitors')
    ).filter(
        UserEvent.event_type.in_(['category_search', 'store_search']),
        UserEvent.category_id != None,
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.category_id).subquery()

    store_views = db.session.query(
        Store.category_id,
        func.count(UserEvent.id).label('view_count')
    ).join(UserEvent, UserEvent.store_id == Store.id).filter(
        UserEvent.event_type == 'store_view',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(Store.category_id).subquery()

    store_counts = db.session.query(
        Store.category_id,
        func.count(Store.id).label('active_stores')
    ).filter(Store.status == 'open').group_by(Store.category_id).subquery()

    results = db.session.query(
        Category.id,
        Category.name,
        func.coalesce(searches.c.search_count, 0).label('search_count'),
        func.coalesce(searches.c.unique_visitors, 0).label('unique_visitors'),
        func.coalesce(store_views.c.view_count, 0).label('store_views'),
        func.coalesce(store_counts.c.active_stores, 0).label('active_stores')
    ).outerjoin(searches, Category.id == searches.c.category_id)\
     .outerjoin(store_views, Category.id == store_views.c.category_id)\
     .outerjoin(store_counts, Category.id == store_counts.c.category_id)\
     .all()

    categories_list = []
    for row in results:
        score = float(row.search_count * 1.2 + row.unique_visitors * 1.0 + row.store_views * 0.8)
        categories_list.append({
            'category_id': row.id,
            'category': row.name,
            'search_count': row.search_count,
            'unique_visitors': row.unique_visitors,
            'store_views': row.store_views,
            'active_stores': row.active_stores,
            'demand_score': round(score, 1)
        })

    categories_list.sort(key=lambda x: x['demand_score'], reverse=True)
    return categories_list


def get_stores(start_date, end_date):
    """Rank stores by engagement metrics."""
    views = db.session.query(
        UserEvent.store_id,
        func.count(UserEvent.id).label('view_count'),
        func.count(func.distinct(UserEvent.session_id)).label('unique_visitors')
    ).filter(
        UserEvent.event_type == 'store_view',
        UserEvent.store_id != None,
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.store_id).subquery()

    searches = db.session.query(
        UserEvent.store_id,
        func.count(UserEvent.id).label('search_count')
    ).filter(
        UserEvent.event_type == 'store_search',
        UserEvent.store_id != None,
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.store_id).subquery()

    navs = db.session.query(
        UserEvent.store_id,
        func.count(UserEvent.id).label('nav_count')
    ).filter(
        UserEvent.event_type == 'navigation_request',
        UserEvent.store_id != None,
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.store_id).subquery()

    offers = db.session.query(
        func.coalesce(UserEvent.store_id, Offer.store_id).label('store_id'),
        func.count(UserEvent.id).label('offer_count')
    ).outerjoin(Offer, UserEvent.offer_id == Offer.id).filter(
        UserEvent.event_type.in_(['offer_view', 'offer_click']),
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(func.coalesce(UserEvent.store_id, Offer.store_id)).subquery()

    recs = db.session.query(
        UserEvent.store_id,
        func.count(UserEvent.id).label('rec_count')
    ).filter(
        UserEvent.event_type.in_(['recommendation_view', 'recommendation_click']),
        UserEvent.store_id != None,
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.store_id).subquery()

    results = db.session.query(
        Store.id,
        Store.name,
        Category.name.label('category_name'),
        func.coalesce(views.c.view_count, 0).label('views'),
        func.coalesce(searches.c.search_count, 0).label('searches'),
        func.coalesce(views.c.unique_visitors, 0).label('unique_visitors'),
        func.coalesce(navs.c.nav_count, 0).label('navigation_requests'),
        func.coalesce(offers.c.offer_count, 0).label('offer_interactions'),
        func.coalesce(recs.c.rec_count, 0).label('recommendation_interactions')
    ).join(Category, Store.category_id == Category.id)\
     .outerjoin(views, Store.id == views.c.store_id)\
     .outerjoin(searches, Store.id == searches.c.store_id)\
     .outerjoin(navs, Store.id == navs.c.store_id)\
     .outerjoin(offers, Store.id == offers.c.store_id)\
     .outerjoin(recs, Store.id == recs.c.store_id)\
     .all()

    stores_list = []
    for row in results:
        score = float(
            row.views * 1.0 + row.searches * 1.2 + row.navigation_requests * 2.0 +
            row.offer_interactions * 1.5 + row.recommendation_interactions * 1.5
        )
        stores_list.append({
            'store_id': row.id,
            'store_name': row.name,
            'category': row.category_name,
            'store_views': row.views,
            'searches': row.searches,
            'navigation_requests': row.navigation_requests,
            'offer_interactions': row.offer_interactions,
            'recommendation_interactions': row.recommendation_interactions,
            'unique_visitors': row.unique_visitors,
            'engagement_score': round(score, 1)
        })

    stores_list.sort(key=lambda x: x['engagement_score'], reverse=True)
    return stores_list


def get_offers(start_date, end_date):
    """Rank offers based on clicks, views, and CTR."""
    metrics = db.session.query(
        UserEvent.offer_id,
        func.sum(db.case((UserEvent.event_type == 'offer_view', 1), else_=0)).label('views'),
        func.sum(db.case((UserEvent.event_type == 'offer_click', 1), else_=0)).label('clicks'),
        func.count(func.distinct(UserEvent.session_id)).label('unique_visitors')
    ).filter(
        UserEvent.offer_id != None,
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(UserEvent.offer_id).subquery()

    results = db.session.query(
        Offer.id,
        Offer.title,
        Store.name.label('store_name'),
        func.coalesce(metrics.c.views, 0).label('views'),
        func.coalesce(metrics.c.clicks, 0).label('clicks'),
        func.coalesce(metrics.c.unique_visitors, 0).label('unique_visitors')
    ).join(Store, Offer.store_id == Store.id)\
     .outerjoin(metrics, Offer.id == metrics.c.offer_id)\
     .all()

    offers_list = []
    for row in results:
        ctr = round((row.clicks / row.views * 100), 2) if row.views > 0 else 0.0
        offers_list.append({
            'offer_id': row.id,
            'title': row.title,
            'store_name': row.store_name,
            'views': row.views,
            'clicks': row.clicks,
            'unique_visitors': row.unique_visitors,
            'ctr': ctr
        })

    offers_list.sort(key=lambda x: x['ctr'], reverse=True)
    return offers_list


def get_navigation(start_date, end_date):
    """Rank destination stores by navigation requests."""
    nav_demand = db.session.query(
        Store.id,
        Store.name,
        Category.name.label('category_name'),
        func.count(UserEvent.id).label('requests')
    ).join(UserEvent, Store.id == UserEvent.store_id)\
     .join(Category, Store.category_id == Category.id).filter(
        UserEvent.event_type == 'navigation_request',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(Store.id, Store.name, Category.name).order_by(desc('requests')).all()

    popular_destinations = [
        {
            'store_id': row.id,
            'store_name': row.name,
            'category': row.category_name,
            'navigation_requests': row.requests
        }
        for row in nav_demand
    ]

    total_requests = sum(d['navigation_requests'] for d in popular_destinations)

    return {
        'total_navigation_requests': total_requests,
        'popular_destinations': popular_destinations
    }


def get_ai_queries(start_date, end_date):
    """Analyze query metrics from ai_query telemetry."""
    total_ai_queries = db.session.query(func.count(UserEvent.id)).filter(
        UserEvent.event_type == 'ai_query',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).scalar() or 0

    unique_visitors = db.session.query(
        func.count(func.distinct(UserEvent.session_id))
    ).filter(
        UserEvent.event_type == 'ai_query',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).scalar() or 0

    frequent_queries = db.session.query(
        func.lower(func.trim(UserEvent.search_query)).label('query'),
        func.count(UserEvent.id).label('count')
    ).filter(
        UserEvent.event_type == 'ai_query',
        UserEvent.search_query != None,
        UserEvent.search_query != '',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(func.lower(func.trim(UserEvent.search_query)))\
     .order_by(desc('count')).limit(10).all()

    popular_questions = [
        {'query': row.query, 'count': row.count}
        for row in frequent_queries
    ]

    daily_stats = db.session.query(
        func.date(UserEvent.created_at).label('date'),
        func.count(UserEvent.id).label('count')
    ).filter(
        UserEvent.event_type == 'ai_query',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(func.date(UserEvent.created_at)).order_by('date').all()

    query_volume_by_day = [
        {'date': str(row.date), 'count': row.count}
        for row in daily_stats
    ]

    if db.engine.dialect.name == 'sqlite':
        hour_expr = func.cast(func.strftime('%H', UserEvent.created_at), db.Integer)
    else:
        hour_expr = func.cast(func.extract('hour', UserEvent.created_at), db.Integer)

    hour_stats = db.session.query(
        hour_expr.label('hour'),
        func.count(UserEvent.id).label('count')
    ).filter(
        UserEvent.event_type == 'ai_query',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by('hour').order_by('hour').all()

    hour_activity = {row.hour: row.count for row in hour_stats}
    query_volume_by_hour = [{'hour': h, 'count': hour_activity.get(h, 0)} for h in range(24)]

    return {
        'total_ai_queries': total_ai_queries,
        'unique_visitors': unique_visitors,
        'popular_questions': popular_questions,
        'query_volume_by_day': query_volume_by_day,
        'query_volume_by_hour': query_volume_by_hour
    }


def get_recommendations(start_date, end_date):
    """Aggregate clicks, views, and CTR for recommendations."""
    if db.engine.dialect.name == 'sqlite':
        type_expr = func.json_extract(UserEvent.metadata_, '$.type')
    else:
        type_expr = UserEvent.metadata_['type'].astext

    views = db.session.query(
        type_expr.label('rec_type'),
        func.count(UserEvent.id).label('views')
    ).filter(
        UserEvent.event_type == 'recommendation_view',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(type_expr).subquery()

    clicks = db.session.query(
        type_expr.label('rec_type'),
        func.count(UserEvent.id).label('clicks')
    ).filter(
        UserEvent.event_type == 'recommendation_click',
        UserEvent.created_at >= start_date,
        UserEvent.created_at <= end_date,
        UserEvent.is_synthetic == False
    ).group_by(type_expr).subquery()

    results = db.session.query(
        func.coalesce(views.c.rec_type, clicks.c.rec_type).label('rec_type'),
        func.coalesce(views.c.views, 0).label('views'),
        func.coalesce(clicks.c.clicks, 0).label('clicks')
    ).outerjoin(clicks, views.c.rec_type == clicks.c.rec_type).all()

    types_list = []
    total_views = 0
    total_clicks = 0

    for row in results:
        rec_type = row.rec_type
        if rec_type and isinstance(rec_type, str):
            rec_type = rec_type.strip('"')

        views_cnt = row.views
        clicks_cnt = row.clicks
        ctr = round((clicks_cnt / views_cnt * 100), 2) if views_cnt > 0 else 0.0

        total_views += views_cnt
        total_clicks += clicks_cnt

        types_list.append({
            'recommendation_type': rec_type or 'unknown',
            'views': views_cnt,
            'clicks': clicks_cnt,
            'ctr': ctr
        })

    overall_ctr = round((total_clicks / total_views * 100), 2) if total_views > 0 else 0.0

    return {
        'total_views': total_views,
        'total_clicks': total_clicks,
        'ctr': overall_ctr,
        'performance_by_type': types_list
    }


def get_demand_signals(start_date, end_date):
    """Compile evidence of category demand levels."""
    category_data = get_categories(start_date, end_date)
    signals = []

    for item in category_data:
        search_count = item['search_count']
        unique_visitors = item['unique_visitors']
        store_views = item['store_views']
        active_stores = item['active_stores']
        demand_score = item['demand_score']

        if demand_score >= 50.0:
            signal = 'high_demand'
            if active_stores == 0:
                confidence = 0.95
            else:
                confidence = min(0.9, max(0.6, round(1.0 / active_stores, 2)))
        elif demand_score >= 20.0:
            signal = 'medium_demand'
            confidence = 0.6
        else:
            signal = 'low_demand'
            confidence = 0.3

        signals.append({
            'category': item['category'],
            'signal': signal,
            'evidence': {
                'search_count': search_count,
                'unique_visitors': unique_visitors,
                'store_views': store_views,
                'active_stores': active_stores
            },
            'confidence': confidence
        })

    return signals

import json
import logging
from datetime import datetime, timedelta
import app.services.analytics_service as service

logger = logging.getLogger(__name__)

def parse_dates(period: str = '30d', start_date: str = None, end_date: str = None):
    end_date_dt = datetime.now()
    start_date_dt = end_date_dt - timedelta(days=30)

    if start_date and end_date:
        try:
            start_date_dt = datetime.fromisoformat(start_date)
            end_date_dt = datetime.fromisoformat(end_date)
        except ValueError:
            logger.warning(f"Invalid date format passed to tool: {start_date}, {end_date}. Falling back to period.")

    if period == 'today':
        start_date_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date_dt = datetime.now()
    elif period == '7d':
        start_date_dt = end_date_dt - timedelta(days=7)
    elif period == '30d':
        start_date_dt = end_date_dt - timedelta(days=30)

    return start_date_dt, end_date_dt

def get_overview_analytics(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Get global totals of sessions, unique visitors, total events, store views, searches, offer clicks, etc."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_overview(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_overview_analytics tool: {e}")
        return json.dumps({"error": str(e)})

def get_visitor_analytics(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Get visitor metrics including unique visitor counts, returning visitors, new sessions, average session duration, and daily/hourly trends."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_visitors(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_visitor_analytics tool: {e}")
        return json.dumps({"error": str(e)})

def get_category_demand(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Rank mall categories based on search count, views, and store counts."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_categories(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_category_demand tool: {e}")
        return json.dumps({"error": str(e)})

def get_store_performance(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Rank stores by engagement metrics (views, searches, navigation requests, offer interactions, and weighted engagement score)."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_stores(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_store_performance tool: {e}")
        return json.dumps({"error": str(e)})

def get_offer_performance(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Get click-through rates (CTR), views, and clicks for active mall offers."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_offers(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_offer_performance tool: {e}")
        return json.dumps({"error": str(e)})

def get_navigation_analytics(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Rank destination stores by wayfinding navigation requests."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_navigation(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_navigation_analytics tool: {e}")
        return json.dumps({"error": str(e)})

def get_ai_query_analytics(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Analyze search query volume, popular chatbot questions, and hourly chatbot query volume."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_ai_queries(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_ai_query_analytics tool: {e}")
        return json.dumps({"error": str(e)})

def get_recommendation_analytics(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Aggregate views, clicks, and CTR for personalization and recommendation slots."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_recommendations(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_recommendation_analytics tool: {e}")
        return json.dumps({"error": str(e)})

def get_demand_signals(period: str = '30d', start_date: str = None, end_date: str = None) -> str:
    """Compile retail demand signals and confidence scores for categories to identify supply gaps."""
    try:
        s_date, e_date = parse_dates(period, start_date, end_date)
        return json.dumps(service.get_demand_signals(s_date, e_date))
    except Exception as e:
        logger.error(f"Error in get_demand_signals tool: {e}")
        return json.dumps({"error": str(e)})

# Mapping from name to function
TOOLS_MAP = {
    'get_overview_analytics': get_overview_analytics,
    'get_visitor_analytics': get_visitor_analytics,
    'get_category_demand': get_category_demand,
    'get_store_performance': get_store_performance,
    'get_offer_performance': get_offer_performance,
    'get_navigation_analytics': get_navigation_analytics,
    'get_ai_query_analytics': get_ai_query_analytics,
    'get_recommendation_analytics': get_recommendation_analytics,
    'get_demand_signals': get_demand_signals,
}

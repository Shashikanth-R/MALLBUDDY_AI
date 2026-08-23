"""
Analytics endpoints for admin dashboard
Provides statistics and insights about mall operations
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Store, Offer, Event, ChatSession, ChatMessage, User, Feedback
from sqlalchemy import func, desc
from datetime import datetime, timedelta

bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@bp.route('/overview', methods=['GET'])
def get_overview():
    """Get overview statistics"""
    try:
        # Get counts
        total_stores = Store.query.count()
        total_offers = Offer.query.filter_by(is_active=True).count()
        total_events = Event.query.count()
        total_users = User.query.count()
        total_chat_sessions = ChatSession.query.count()
        total_messages = ChatMessage.query.count()
        
        # Get active stores
        active_stores = Store.query.filter_by(status='open').count()
        
        # Get recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_sessions = ChatSession.query.filter(
            ChatSession.created_at >= week_ago
        ).count()
        
        return jsonify({
            'overview': {
                'total_stores': total_stores,
                'active_stores': active_stores,
                'total_offers': total_offers,
                'total_events': total_events,
                'total_users': total_users,
                'total_chat_sessions': total_chat_sessions,
                'total_messages': total_messages,
                'recent_sessions_7d': recent_sessions
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/popular-stores', methods=['GET'])
def get_popular_stores():
    """Get most popular stores based on chat mentions"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Get stores mentioned in chat
        # This is a simplified version - in production you'd track actual store views/clicks
        stores = Store.query.limit(limit).all()
        
        popular_stores = []
        for store in stores:
            popular_stores.append({
                'id': store.id,
                'name': store.name,
                'category': store.category.name if store.category else 'N/A',
                'floor': store.floor,
                'mentions': 0  # Placeholder - would track actual mentions
            })
        
        return jsonify({
            'popular_stores': popular_stores,
            'count': len(popular_stores)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/chatbot-usage', methods=['GET'])
def get_chatbot_usage():
    """Get chatbot usage statistics"""
    try:
        # Get date range
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now() - timedelta(days=days)
        
        # Total sessions and messages
        total_sessions = ChatSession.query.filter(
            ChatSession.created_at >= start_date
        ).count()
        
        total_messages = ChatMessage.query.join(ChatSession).filter(
            ChatSession.created_at >= start_date
        ).count()
        
        # Average messages per session
        avg_messages = total_messages / total_sessions if total_sessions > 0 else 0
        
        # Get daily breakdown
        daily_stats = db.session.query(
            func.date(ChatSession.created_at).label('date'),
            func.count(ChatSession.id).label('sessions')
        ).filter(
            ChatSession.created_at >= start_date
        ).group_by(
            func.date(ChatSession.created_at)
        ).all()
        
        daily_data = [
            {'date': str(stat.date), 'sessions': stat.sessions}
            for stat in daily_stats
        ]
        
        return jsonify({
            'chatbot_usage': {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'avg_messages_per_session': round(avg_messages, 2),
                'daily_breakdown': daily_data
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/category-distribution', methods=['GET'])
def get_category_distribution():
    """Get distribution of stores by category"""
    try:
        mall_id = request.args.get('mall_id', 1, type=int)
        
        # Get category counts
        category_stats = db.session.query(
            Store.category_id,
            func.count(Store.id).label('count')
        ).filter_by(
            mall_id=mall_id
        ).group_by(
            Store.category_id
        ).all()
        
        from app.models import Category
        distribution = []
        for stat in category_stats:
            category = Category.query.get(stat.category_id)
            if category:
                distribution.append({
                    'category': category.name,
                    'icon': category.icon,
                    'count': stat.count
                })
        
        return jsonify({
            'category_distribution': distribution,
            'total_categories': len(distribution)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/floor-distribution', methods=['GET'])
def get_floor_distribution():
    """Get distribution of stores by floor"""
    try:
        mall_id = request.args.get('mall_id', 1, type=int)
        
        # Get floor counts
        floor_stats = db.session.query(
            Store.floor,
            func.count(Store.id).label('count')
        ).filter_by(
            mall_id=mall_id
        ).group_by(
            Store.floor
        ).all()
        
        distribution = [
            {'floor': stat.floor, 'count': stat.count}
            for stat in floor_stats
        ]
        
        # Sort by floor
        distribution.sort(key=lambda x: x['floor'])
        
        return jsonify({
            'floor_distribution': distribution,
            'total_floors': len(distribution)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/active-offers', methods=['GET'])
def get_active_offers_stats():
    """Get statistics about active offers"""
    try:
        # Get active offers
        active_offers = Offer.query.filter_by(is_active=True).count()
        featured_offers = Offer.query.filter_by(is_active=True, is_featured=True).count()
        
        # Get offers expiring soon (within 7 days)
        week_from_now = datetime.now().date() + timedelta(days=7)
        expiring_soon = Offer.query.filter(
            Offer.is_active == True,
            Offer.end_date <= week_from_now
        ).count()
        
        return jsonify({
            'offers_stats': {
                'active_offers': active_offers,
                'featured_offers': featured_offers,
                'expiring_soon': expiring_soon
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/upcoming-events', methods=['GET'])
def get_upcoming_events_stats():
    """Get statistics about upcoming events"""
    try:
        # Get upcoming events
        now = datetime.now()
        upcoming_events = Event.query.filter(
            Event.event_date >= now
        ).count()
        
        # Get events this week
        week_from_now = now + timedelta(days=7)
        events_this_week = Event.query.filter(
            Event.event_date >= now,
            Event.event_date <= week_from_now
        ).count()
        
        return jsonify({
            'events_stats': {
                'upcoming_events': upcoming_events,
                'events_this_week': events_this_week
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

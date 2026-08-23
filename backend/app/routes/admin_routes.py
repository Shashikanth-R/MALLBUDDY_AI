"""
Admin Dashboard API Routes
Comprehensive endpoints for admin dashboard functionality
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app import db
from app.models import (
    User, Admin, Store, Offer, Event, Facility, 
    ChatSession, ChatMessage, Feedback, 
    KnowledgeDoc, ChatbotSettings, AuditLog, Category
)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
import app.services.analytics_service as service

def admin_required(fn):
    """Decorator to require admin role or claim."""
    @wraps(fn)
    @jwt_required()
    def decorator(*args, **kwargs):
        claims = get_jwt()
        if not claims.get('is_admin') and claims.get('role') != 'admin':
            return jsonify({'error': 'Admin authorization required'}), 403
        admin_id = get_jwt_identity()
        admin = Admin.query.get(admin_id)
        if not admin or not admin.is_active:
            return jsonify({'error': 'Admin account is inactive or not found'}), 403
        return fn(*args, **kwargs)
    return decorator


def parse_period_args():
    """Parse start_date, end_date, or period from request query params."""
    period = request.args.get('period', '30d')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    if start_date_str and end_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            raise ValueError('Invalid date format. Use ISO format (YYYY-MM-DD)')
    elif period == 'today':
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now()
    elif period == '7d':
        start_date = end_date - timedelta(days=7)
    elif period == '30d':
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        raise ValueError('start_date must be before end_date')
    if (end_date - start_date).days > 366:
        raise ValueError('Date range cannot exceed 1 year')

    return start_date, end_date


@bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics():
    """Get comprehensive dashboard analytics"""
    try:
        # Basic counts
        total_stores = Store.query.count()
        active_offers = Offer.query.filter_by(is_active=True).count()
        total_events = Event.query.count()
        total_users = User.query.count()
        total_sessions = ChatSession.query.count()
        total_messages = ChatMessage.query.count()
        total_feedback = Feedback.query.count()
        
        # Chat sessions by day (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        daily_sessions = db.session.query(
            func.date(ChatSession.created_at).label('date'),
            func.count(ChatSession.id).label('count')
        ).filter(
            ChatSession.created_at >= seven_days_ago
        ).group_by(func.date(ChatSession.created_at)).all()
        
        # Top stores by category
        stores_by_category = db.session.query(
            Category.name,
            func.count(Store.id).label('count')
        ).join(Store).group_by(Category.name).all()
        
        # Recent activity
        recent_sessions = ChatSession.query.order_by(
            desc(ChatSession.created_at)
        ).limit(5).all()
        
        return jsonify({
            'stats': {
                'total_stores': total_stores,
                'active_offers': active_offers,
                'total_events': total_events,
                'total_users': total_users,
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'total_feedback': total_feedback
            },
            'daily_sessions': [
                {'date': str(d.date), 'count': d.count} 
                for d in daily_sessions
            ],
            'stores_by_category': [
                {'category': s[0], 'count': s[1]} 
                for s in stores_by_category
            ],
            'recent_sessions': [s.to_dict() for s in recent_sessions]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats/live', methods=['GET'])
@admin_required
def get_live_stats():
    """Get real-time visitor statistics"""
    try:
        # Active sessions in the last 30 minutes
        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        active_sessions = ChatSession.query.filter(
            ChatSession.updated_at >= thirty_min_ago
        ).count()
        
        # Messages in the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_messages = ChatMessage.query.filter(
            ChatMessage.timestamp >= one_hour_ago
        ).count()
        
        # Today's stats
        today = datetime.utcnow().date()
        today_sessions = ChatSession.query.filter(
            func.date(ChatSession.created_at) == today
        ).count()
        
        today_messages = ChatMessage.query.filter(
            func.date(ChatMessage.timestamp) == today
        ).count()
        
        return jsonify({
            'active_sessions': active_sessions,
            'recent_messages': recent_messages,
            'today_sessions': today_sessions,
            'today_messages': today_messages,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/analytics/overview', methods=['GET'])
@admin_required
def get_overview_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_overview(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/visitors', methods=['GET'])
@admin_required
def get_visitors_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_visitors(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/categories', methods=['GET'])
@admin_required
def get_categories_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_categories(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/stores', methods=['GET'])
@admin_required
def get_stores_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_stores(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/offers', methods=['GET'])
@admin_required
def get_offers_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_offers(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/navigation', methods=['GET'])
@admin_required
def get_navigation_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_navigation(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/ai-queries', methods=['GET'])
@admin_required
def get_ai_queries_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_ai_queries(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/recommendations', methods=['GET'])
@admin_required
def get_recommendations_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_recommendations(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@bp.route('/analytics/demand', methods=['GET'])
@admin_required
def get_demand_analytics():
    try:
        start_date, end_date = parse_period_args()
        data = service.get_demand_signals(start_date, end_date)
        return jsonify(data), 200
    except ValueError as val_err:
        return jsonify({'error': str(val_err)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# =============================================
# USERS MANAGEMENT
# =============================================

@bp.route('/users', methods=['GET'])
def get_users():
    """Get all registered users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = User.query
        
        if search:
            query = query.filter(
                (User.name.ilike(f'%{search}%')) | 
                (User.email.ilike(f'%{search}%'))
            )
        
        users = query.order_by(desc(User.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [u.to_dict() for u in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user status"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================
# CHAT HISTORY & ANALYTICS
# =============================================

@bp.route('/chats', methods=['GET'])
def get_chat_sessions():
    """Get all chat sessions with messages"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        sessions = ChatSession.query.order_by(
            desc(ChatSession.updated_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        result = []
        for session in sessions.items:
            session_data = session.to_dict()
            session_data['message_count'] = session.messages.count()
            session_data['last_message'] = None
            
            last_msg = session.messages.order_by(
                desc(ChatMessage.timestamp)
            ).first()
            if last_msg:
                session_data['last_message'] = last_msg.message[:100]
            
            result.append(session_data)
        
        return jsonify({
            'sessions': result,
            'total': sessions.total,
            'pages': sessions.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/chats/<int:session_id>', methods=['GET'])
def get_chat_detail(session_id):
    """Get detailed chat session with all messages"""
    try:
        session = ChatSession.query.get_or_404(session_id)
        messages = session.messages.order_by(ChatMessage.timestamp).all()
        
        return jsonify({
            'session': session.to_dict(),
            'messages': [m.to_dict() for m in messages]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/chats/popular-questions', methods=['GET'])
def get_popular_questions():
    """Get most frequently asked questions"""
    try:
        # Get user messages and group by similarity
        questions = ChatMessage.query.filter_by(role='user').order_by(
            desc(ChatMessage.timestamp)
        ).limit(100).all()
        
        # Simple word frequency analysis
        word_freq = {}
        for msg in questions:
            words = msg.message.lower().split()
            for word in words:
                if len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return jsonify({
            'popular_keywords': [{'word': w[0], 'count': w[1]} for w in top_words],
            'total_questions': len(questions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================
# FEEDBACK MANAGEMENT
# =============================================

@bp.route('/feedback', methods=['GET'])
def get_feedback():
    """Get all user feedback"""
    try:
        status = request.args.get('status', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = Feedback.query
        
        if status:
            query = query.filter_by(status=status)
        
        feedback_list = query.order_by(
            desc(Feedback.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'feedback': [f.to_dict() for f in feedback_list.items],
            'total': feedback_list.total,
            'pages': feedback_list.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/feedback', methods=['POST'])
def create_feedback():
    """Create new feedback (from user app)"""
    try:
        data = request.get_json()
        
        feedback = Feedback(
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            type=data.get('type', 'general'),
            message=data['message'],
            status='open'
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback': feedback.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/feedback/<int:feedback_id>', methods=['PUT'])
def update_feedback(feedback_id):
    """Update feedback status"""
    try:
        feedback = Feedback.query.get_or_404(feedback_id)
        data = request.get_json()
        
        if 'status' in data:
            feedback.status = data['status']
            if data['status'] == 'resolved':
                feedback.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Feedback updated successfully',
            'feedback': feedback.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================
# FACILITIES MANAGEMENT
# =============================================

@bp.route('/facilities', methods=['GET'])
def get_facilities():
    """Get all facilities"""
    try:
        mall_id = request.args.get('mall_id', 1, type=int)
        facility_type = request.args.get('type', '')
        
        query = Facility.query.filter_by(mall_id=mall_id)
        
        if facility_type:
            query = query.filter_by(type=facility_type)
        
        facilities = query.all()
        
        return jsonify({
            'facilities': [f.to_dict() for f in facilities],
            'total': len(facilities)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/facilities', methods=['POST'])
def create_facility():
    """Create new facility"""
    try:
        data = request.get_json()
        
        facility = Facility(
            mall_id=data.get('mall_id', 1),
            name=data['name'],
            type=data['type'],
            floor=data.get('floor'),
            unit=data.get('unit'),
            description=data.get('description'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(facility)
        db.session.commit()
        
        return jsonify({
            'message': 'Facility created successfully',
            'facility': facility.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/facilities/<int:facility_id>', methods=['PUT'])
def update_facility(facility_id):
    """Update facility"""
    try:
        facility = Facility.query.get_or_404(facility_id)
        data = request.get_json()
        
        if 'name' in data:
            facility.name = data['name']
        if 'type' in data:
            facility.type = data['type']
        if 'floor' in data:
            facility.floor = data['floor']
        if 'unit' in data:
            facility.unit = data['unit']
        if 'description' in data:
            facility.description = data['description']
        if 'is_active' in data:
            facility.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Facility updated successfully',
            'facility': facility.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/facilities/<int:facility_id>', methods=['DELETE'])
def delete_facility(facility_id):
    """Delete facility"""
    try:
        facility = Facility.query.get_or_404(facility_id)
        db.session.delete(facility)
        db.session.commit()
        
        return jsonify({'message': 'Facility deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================
# AUDIT LOGS
# =============================================

@bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    """Get admin audit logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action = request.args.get('action', '')
        
        query = AuditLog.query
        
        if action:
            query = query.filter_by(action=action)
        
        logs = query.order_by(
            desc(AuditLog.timestamp)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'logs': [l.to_dict() for l in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def log_admin_action(admin_id, action, entity_type, entity_id=None, details=None):
    """Helper function to log admin actions"""
    try:
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging admin action: {e}")


# =============================================
# CHATBOT SETTINGS
# =============================================

@bp.route('/settings', methods=['GET'])
def get_settings():
    """Get all chatbot settings"""
    try:
        settings = ChatbotSettings.query.all()
        
        return jsonify({
            'settings': [s.to_dict() for s in settings]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/settings/<key>', methods=['PUT'])
def update_setting(key):
    """Update a chatbot setting"""
    try:
        setting = ChatbotSettings.query.filter_by(key=key).first()
        data = request.get_json()
        
        if not setting:
            # Create new setting
            setting = ChatbotSettings(
                key=key,
                value=data['value'],
                description=data.get('description', '')
            )
            db.session.add(setting)
        else:
            setting.value = data['value']
            if 'description' in data:
                setting.description = data['description']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Setting updated successfully',
            'setting': setting.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/settings/bulk', methods=['POST'])
def update_settings_bulk():
    """Update multiple settings at once"""
    try:
        data = request.get_json()
        settings_data = data.get('settings', {})
        
        for key, value in settings_data.items():
            setting = ChatbotSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = ChatbotSettings(key=key, value=value)
                db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Settings updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
# =============================================
# STORES MANAGEMENT
# =============================================

@bp.route('/stores', methods=['GET'])
def get_all_stores():
    """Get all stores for admin"""
    try:
        stores = Store.query.all()
        return jsonify({
            'stores': [store.to_dict() for store in stores],
            'count': len(stores)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stores', methods=['POST'])
def create_store():
    """Create a new store"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'mall_id', 'category_id', 'floor', 'unit']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        store = Store(
            name=data['name'],
            mall_id=data['mall_id'],
            category_id=data['category_id'],
            floor=data['floor'],
            unit=data['unit'],
            description=data.get('description'),
            # contact=data.get('contact'), # Field might not exist in model yet
            status=data.get('status', 'open')
        )
        
        db.session.add(store)
        db.session.commit()
        
        # Log action
        log_admin_action(1, 'create', 'store', store.id, {'name': store.name})
        
        return jsonify({
            'message': 'Store created successfully',
            'store': store.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/stores/<int:store_id>', methods=['PUT'])
def update_store(store_id):
    """Update a store"""
    store = Store.query.get_or_404(store_id)
    data = request.get_json()
    
    try:
        if 'name' in data:
            store.name = data['name']
        if 'category_id' in data:
            store.category_id = data['category_id']
        if 'floor' in data:
            store.floor = data['floor']
        if 'unit' in data:
            store.unit = data['unit']
        if 'description' in data:
            store.description = data['description']
        if 'status' in data:
            store.status = data['status']
        
        db.session.commit()
        
        # Log action
        log_admin_action(1, 'update', 'store', store.id, data)
        
        return jsonify({
            'message': 'Store updated successfully',
            'store': store.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/stores/<int:store_id>', methods=['DELETE'])
def delete_store(store_id):
    """Delete a store"""
    store = Store.query.get_or_404(store_id)
    
    try:
        db.session.delete(store)
        db.session.commit()
        
        # Log action
        log_admin_action(1, 'delete', 'store', store_id, {'name': store.name})
        
        return jsonify({'message': 'Store deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================
# OFFERS MANAGEMENT
# =============================================

@bp.route('/offers', methods=['GET'])
def get_all_offers():
    """Get all offers for admin"""
    try:
        offers = Offer.query.all()
        return jsonify({
            'offers': [offer.to_dict() for offer in offers],
            'count': len(offers)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/offers', methods=['POST'])
def create_offer():
    """Create a new offer"""
    data = request.get_json()
    
    required_fields = ['store_id', 'title', 'description', 'start_date', 'end_date']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        offer = Offer(
            store_id=data['store_id'],
            title=data['title'],
            description=data['description'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            is_featured=data.get('is_featured', False),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(offer)
        db.session.commit()
        
        log_admin_action(1, 'create', 'offer', offer.id, {'title': offer.title})
        
        return jsonify({
            'message': 'Offer created successfully',
            'offer': offer.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/offers/<int:offer_id>', methods=['PUT'])
def update_offer(offer_id):
    """Update an offer"""
    offer = Offer.query.get_or_404(offer_id)
    data = request.get_json()
    
    try:
        if 'title' in data:
            offer.title = data['title']
        if 'description' in data:
            offer.description = data['description']
        if 'start_date' in data:
            offer.start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            offer.end_date = datetime.fromisoformat(data['end_date'])
        if 'is_featured' in data:
            offer.is_featured = data['is_featured']
        if 'is_active' in data:
            offer.is_active = data['is_active']
        
        db.session.commit()
        
        log_admin_action(1, 'update', 'offer', offer.id, data)
        
        return jsonify({
            'message': 'Offer updated successfully',
            'offer': offer.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/offers/<int:offer_id>', methods=['DELETE'])
def delete_offer(offer_id):
    """Delete an offer"""
    offer = Offer.query.get_or_404(offer_id)
    
    try:
        db.session.delete(offer)
        db.session.commit()
        
        log_admin_action(1, 'delete', 'offer', offer_id, {'title': offer.title})
        
        return jsonify({'message': 'Offer deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================
# EVENTS MANAGEMENT
# =============================================

@bp.route('/events', methods=['GET'])
def get_all_events():
    """Get all events for admin"""
    try:
        events = Event.query.all()
        return jsonify({
            'events': [event.to_dict() for event in events],
            'count': len(events)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/events', methods=['POST'])
def create_event():
    """Create a new event"""
    data = request.get_json()
    
    required_fields = ['mall_id', 'name', 'description', 'event_date', 'location']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        event = Event(
            mall_id=data['mall_id'],
            name=data['name'],
            description=data['description'],
            event_date=datetime.fromisoformat(data['event_date']),
            location=data['location']
        )
        
        db.session.add(event)
        db.session.commit()
        
        log_admin_action(1, 'create', 'event', event.id, {'name': event.name})
        
        return jsonify({
            'message': 'Event created successfully',
            'event': event.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """Update an event"""
    event = Event.query.get_or_404(event_id)
    data = request.get_json()
    
    try:
        if 'name' in data:
            event.name = data['name']
        if 'description' in data:
            event.description = data['description']
        if 'event_date' in data:
            event.event_date = datetime.fromisoformat(data['event_date'])
        if 'location' in data:
            event.location = data['location']
        
        db.session.commit()
        
        log_admin_action(1, 'update', 'event', event.id, data)
        
        return jsonify({
            'message': 'Event updated successfully',
            'event': event.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete an event"""
    event = Event.query.get_or_404(event_id)
    
    try:
        db.session.delete(event)
        db.session.commit()
        
        log_admin_action(1, 'delete', 'event', event_id, {'name': event.name})
        
        return jsonify({'message': 'Event deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/ai/chat', methods=['POST'])
@admin_required
def admin_ai_chat():
    """Admin AI Business Intelligence Agent chatbot endpoint"""
    import time
    from app.services.admin_ai import run_admin_ai
    import logging
    
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message parameter is required'}), 400
        
    message = data['message']
    admin_id = get_jwt_identity()
    
    start_time = time.time()
    
    try:
        # Run agent
        result = run_admin_ai(message)
        
        execution_time = time.time() - start_time
        
        logging.getLogger('app.routes.admin_routes').info(
            f"Admin AI Request ID: {admin_id} | "
            f"Tools used: {result['tools_used']} | "
            f"Execution time: {execution_time:.3f}s | Success: True"
        )
        
        return jsonify({
            'answer': result['answer'],
            'evidence': result['evidence'],
            'tools_used': result['tools_used'],
            'confidence': result['confidence']
        }), 200
        
    except Exception as e:
        execution_time = time.time() - start_time
        logging.getLogger('app.routes.admin_routes').error(
            f"Admin AI Request ID: {admin_id} | "
            f"Execution time: {execution_time:.3f}s | Success: False | Error: {str(e)}"
        )
        return jsonify({'error': str(e)}), 500



"""
Feedback system endpoints for collecting user feedback
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Feedback, ChatSession
from datetime import datetime

bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')


@bp.route('/', methods=['POST'])
def submit_feedback():
    """Submit user feedback"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        feedback = Feedback(
            session_id=data.get('session_id'),
            rating=data.get('rating'),
            comment=data.get('comment', ''),
            feedback_type=data.get('feedback_type', 'general')
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/session/<int:session_id>', methods=['POST'])
def submit_session_feedback(session_id):
    """Submit feedback for a specific chat session"""
    data = request.get_json()
    
    if not data or 'rating' not in data:
        return jsonify({'error': 'Rating is required'}), 400
    
    try:
        # Verify session exists
        session = ChatSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        feedback = Feedback(
            session_id=session_id,
            rating=data['rating'],
            comment=data.get('comment', ''),
            feedback_type='chat_session'
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'message': 'Session feedback submitted successfully',
            'feedback_id': feedback.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
def get_feedback_stats():
    """Get feedback statistics (admin only)"""
    try:
        # Total feedback count
        total_feedback = Feedback.query.count()
        
        # Average rating
        from sqlalchemy import func
        avg_rating = db.session.query(
            func.avg(Feedback.rating)
        ).scalar()
        
        # Rating distribution
        rating_dist = db.session.query(
            Feedback.rating,
            func.count(Feedback.id).label('count')
        ).group_by(Feedback.rating).all()
        
        distribution = {
            str(rating): count
            for rating, count in rating_dist
        }
        
        # Recent feedback
        recent = Feedback.query.order_by(
            Feedback.created_at.desc()
        ).limit(10).all()
        
        return jsonify({
            'total_feedback': total_feedback,
            'average_rating': round(float(avg_rating or 0), 2),
            'rating_distribution': distribution,
            'recent_feedback': [f.to_dict() for f in recent]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:feedback_id>', methods=['GET'])
def get_feedback(feedback_id):
    """Get specific feedback (admin only)"""
    try:
        feedback = Feedback.query.get(feedback_id)
        
        if not feedback:
            return jsonify({'error': 'Feedback not found'}), 404
        
        return jsonify({'feedback': feedback.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/all', methods=['GET'])
def get_all_feedback():
    """Get all feedback with pagination (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        feedback_type = request.args.get('type')
        
        query = Feedback.query
        
        if feedback_type:
            query = query.filter_by(feedback_type=feedback_type)
        
        pagination = query.order_by(
            Feedback.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'feedback': [f.to_dict() for f in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

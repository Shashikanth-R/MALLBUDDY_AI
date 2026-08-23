from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import Event

bp = Blueprint('events', __name__, url_prefix='/api/events')


@bp.route('/', methods=['GET'])
def get_events():
    """Get all upcoming events"""
    mall_id = request.args.get('mall_id', type=int)
    
    query = Event.query.filter(
        Event.is_active == True,
        Event.event_date >= datetime.now()
    ).order_by(Event.event_date)
    
    if mall_id:
        query = query.filter_by(mall_id=mall_id)
    
    events = query.all()
    
    return jsonify({
        'events': [event.to_dict() for event in events],
        'count': len(events)
    }), 200


@bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get event details"""
    event = Event.query.get(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    return jsonify({'event': event.to_dict()}), 200

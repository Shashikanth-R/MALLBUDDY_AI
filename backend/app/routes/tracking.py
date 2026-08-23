"""Validated browser telemetry endpoints for the analytics event stream."""
import json
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.models import Category, Event, Facility, Mall, Offer, Store, VisitorSession
from app.services.event_tracking_service import create_visitor_session, end_visitor_session, track_event

bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

ALLOWED_EVENT_TYPES = {
    'store_search', 'category_search', 'store_view', 'navigation_request',
    'navigation_complete', 'offer_view', 'offer_click', 'recommendation_view',
    'recommendation_click', 'ai_query', 'event_view', 'facility_search',
    'feedback_submitted',
}
MAX_METADATA_BYTES = 8192
MAX_SEARCH_QUERY_LENGTH = 500
TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9_-]{20,100}$')


def _optional_user_id():
    verify_jwt_in_request(optional=True)
    return get_jwt_identity()


def _valid_metadata(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        return None
    try:
        encoded = json.dumps(value, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError):
        return None
    return value if len(encoded) <= MAX_METADATA_BYTES else None


def _validate_references(data, mall_id):
    store_id = data.get('store_id')
    category_id = data.get('category_id')
    offer_id = data.get('offer_id')
    event_id = data.get('event_id')
    facility_id = data.get('facility_id')

    store = None
    if store_id is not None:
        store = Store.query.filter_by(id=store_id, mall_id=mall_id).first()
        if not store:
            return 'Invalid store_id'
    if category_id is not None and not Category.query.get(category_id):
        return 'Invalid category_id'
    if offer_id is not None:
        offer = Offer.query.get(offer_id)
        if not offer or offer.store.mall_id != mall_id:
            return 'Invalid offer_id'
        if store and offer.store_id != store.id:
            return 'offer_id does not belong to store_id'
    if event_id is not None and not Event.query.filter_by(id=event_id, mall_id=mall_id).first():
        return 'Invalid event_id'
    if facility_id is not None and not Facility.query.filter_by(id=facility_id, mall_id=mall_id).first():
        return 'Invalid facility_id'
    return None


def _parse_session_token(data):
    token = data.get('session_id')
    return token if isinstance(token, str) and TOKEN_PATTERN.fullmatch(token) else None


@bp.route('/session', methods=['POST'])
def start_session():
    data = request.get_json(silent=True) or {}
    mall_id = data.get('mall_id', 1)
    if not isinstance(mall_id, int) or not Mall.query.get(mall_id):
        return jsonify({'error': 'Invalid mall_id'}), 400
    try:
        user_id = _optional_user_id()
        token = _parse_session_token(data)
        device_type = data.get('device_type')
        if device_type is not None and (not isinstance(device_type, str) or len(device_type) > 30):
            return jsonify({'error': 'Invalid device_type'}), 400
        session = create_visitor_session(mall_id, user_id=user_id, device_type=device_type, session_token=token)
        return jsonify({'session_id': session.session_token, 'mall_id': session.mall_id}), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception:
        return jsonify({'error': 'Unable to start visitor session'}), 503


@bp.route('/event', methods=['POST'])
def create_event():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    event_type = data.get('event_type')
    mall_id = data.get('mall_id')
    session_token = _parse_session_token(data)
    metadata = _valid_metadata(data.get('metadata'))
    search_query = data.get('search_query')
    if event_type not in ALLOWED_EVENT_TYPES:
        return jsonify({'error': 'Invalid event_type'}), 400
    if not isinstance(mall_id, int) or not Mall.query.get(mall_id):
        return jsonify({'error': 'Invalid mall_id'}), 400
    if not session_token:
        return jsonify({'error': 'Invalid session_id'}), 400
    if not VisitorSession.query.filter_by(session_token=session_token, mall_id=mall_id).first():
        return jsonify({'error': 'Visitor session not found'}), 404
    if metadata is None:
        return jsonify({'error': 'metadata must be a JSON object no larger than 8 KB'}), 400
    if search_query is not None and (not isinstance(search_query, str) or len(search_query) > MAX_SEARCH_QUERY_LENGTH):
        return jsonify({'error': 'Invalid search_query'}), 400
    for field in ('store_id', 'category_id', 'offer_id', 'event_id', 'facility_id'):
        if data.get(field) is not None and (not isinstance(data[field], int) or isinstance(data[field], bool)):
            return jsonify({'error': f'Invalid {field}'}), 400
    reference_error = _validate_references(data, mall_id)
    if reference_error:
        return jsonify({'error': reference_error}), 400
    try:
        user_id = _optional_user_id()
        event = track_event(
            mall_id=mall_id, session_token=session_token, user_id=user_id,
            event_type=event_type, store_id=data.get('store_id'),
            category_id=data.get('category_id'), offer_id=data.get('offer_id'),
            event_id=data.get('event_id'), facility_id=data.get('facility_id'),
            search_query=search_query, metadata=metadata,
            # Browser clients cannot set synthetic data; it is always false here.
            is_synthetic=False,
        )
        if event is None:
            return jsonify({'error': 'Analytics event was not recorded'}), 503
        return jsonify({'event_id': event.id}), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception:
        return jsonify({'error': 'Unable to record analytics event'}), 503


@bp.route('/session/end', methods=['POST'])
def end_session():
    data = request.get_json(silent=True) or {}
    mall_id = data.get('mall_id', 1)
    token = _parse_session_token(data)
    if not isinstance(mall_id, int) or not Mall.query.get(mall_id) or not token:
        return jsonify({'error': 'Invalid mall_id or session_id'}), 400
    if not end_visitor_session(token, mall_id):
        return jsonify({'error': 'Visitor session not found'}), 404
    return jsonify({'message': 'Visitor session ended'}), 200

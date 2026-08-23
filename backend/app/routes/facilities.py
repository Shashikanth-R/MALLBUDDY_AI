from flask import Blueprint, request, jsonify
from app import db
from app.models import Facility

bp = Blueprint('facilities', __name__, url_prefix='/api/facilities')


@bp.route('/', methods=['GET'])
def get_facilities():
    """Get all facilities"""
    mall_id = request.args.get('mall_id', type=int)
    facility_type = request.args.get('type')
    
    query = Facility.query.filter_by(is_active=True)
    
    if mall_id:
        query = query.filter_by(mall_id=mall_id)
    if facility_type:
        query = query.filter_by(type=facility_type)
    
    facilities = query.all()
    
    return jsonify({
        'facilities': [facility.to_dict() for facility in facilities],
        'count': len(facilities)
    }), 200


@bp.route('/<int:facility_id>', methods=['GET'])
def get_facility(facility_id):
    """Get facility details"""
    facility = Facility.query.get(facility_id)
    
    if not facility:
        return jsonify({'error': 'Facility not found'}), 404
    
    return jsonify({'facility': facility.to_dict()}), 200

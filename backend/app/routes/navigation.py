from flask import Blueprint, request, jsonify
from app import db
from app.models import Route, Store, Facility

bp = Blueprint('navigation', __name__, url_prefix='/api/navigation')


def calculate_route(from_location, to_location, mall_id=1):
    """Calculate route between two locations with intelligent pathfinding"""
    
    # Try to find direct route
    route = Route.query.filter_by(
        mall_id=mall_id,
        from_location=from_location,
        to_location=to_location,
        is_active=True
    ).first()
    
    if route:
        return route.to_dict()
    
    # Try reverse route
    route = Route.query.filter_by(
        mall_id=mall_id,
        from_location=to_location,
        to_location=from_location,
        is_active=True
    ).first()
    
    if route:
        # Reverse the steps
        reversed_route = route.to_dict()
        if reversed_route.get('steps'):
            reversed_route['steps'] = list(reversed(reversed_route['steps']))
        reversed_route['from_location'] = from_location
        reversed_route['to_location'] = to_location
        return reversed_route
    
    # If no route found, try to find store/facility and generate basic directions
    destination = Store.query.filter_by(name=to_location, mall_id=mall_id).first()
    if not destination:
        destination = Facility.query.filter_by(name=to_location, mall_id=mall_id).first()
    
    if destination:
        # Generate basic directions
        return {
            'from_location': from_location,
            'to_location': to_location,
            'distance_meters': 50,  # Estimated
            'estimated_time_minutes': 2,
            'steps': [
                f"Head to Floor {destination.floor}",
                f"Look for Unit {destination.unit}",
                f"You will find {to_location} there"
            ]
        }
    
    return None


@bp.route('/', methods=['GET'])
def get_route():
    """Get navigation route between two locations"""
    from_loc = request.args.get('from')
    to_loc = request.args.get('to')
    mall_id = request.args.get('mall_id', 1, type=int)
    
    if not from_loc or not to_loc:
        return jsonify({'error': 'from and to locations required'}), 400
    
    # Calculate route
    route_data = calculate_route(from_loc, to_loc, mall_id)
    
    if not route_data:
        return jsonify({
            'error': 'Route not found',
            'message': f'No route available from {from_loc} to {to_loc}'
        }), 404
    
    return jsonify({'route': route_data}), 200


@bp.route('/nearby', methods=['GET'])
def get_nearby_locations():
    """Get nearby stores and facilities from a location"""
    location = request.args.get('location')
    floor = request.args.get('floor')
    mall_id = request.args.get('mall_id', 1, type=int)
    radius = request.args.get('radius', 50, type=int)  # meters
    
    if not floor:
        return jsonify({'error': 'floor parameter required'}), 400
    
    # Get stores on the same floor
    stores = Store.query.filter_by(
        mall_id=mall_id,
        floor=floor,
        status='open'
    ).limit(10).all()
    
    # Get facilities on the same floor
    facilities = Facility.query.filter_by(
        mall_id=mall_id,
        floor=floor
    ).limit(5).all()
    
    return jsonify({
        'floor': floor,
        'stores': [s.to_dict() for s in stores],
        'facilities': [f.to_dict() for f in facilities],
        'count': len(stores) + len(facilities)
    }), 200


@bp.route('/map/<int:mall_id>', methods=['GET'])
def get_mall_map(mall_id):
    """Get mall map information"""
    floor = request.args.get('floor')
    
    if floor:
        # Get stores and facilities for specific floor
        stores = Store.query.filter_by(mall_id=mall_id, floor=floor).all()
        facilities = Facility.query.filter_by(mall_id=mall_id, floor=floor).all()
        
        return jsonify({
            'mall_id': mall_id,
            'floor': floor,
            'stores': [s.to_dict() for s in stores],
            'facilities': [f.to_dict() for f in facilities]
        }), 200
    else:
        # Get all floors
        floors_query = db.session.query(Store.floor).filter_by(
            mall_id=mall_id
        ).distinct().all()
        
        floors = [f[0] for f in floors_query]
        
        return jsonify({
            'mall_id': mall_id,
            'floors': sorted(floors),
            'message': 'Specify floor parameter to get detailed map'
        }), 200


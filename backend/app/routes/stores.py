from flask import Blueprint, request, jsonify
from app import db
from app.models import Store, Category
from sqlalchemy import or_, and_

bp = Blueprint('stores', __name__, url_prefix='/api/stores')


@bp.route('/', methods=['GET'])
def get_stores():
    """Get all stores with advanced filters"""
    mall_id = request.args.get('mall_id', type=int)
    category_ids = request.args.get('category_id')  # Can be comma-separated
    floors = request.args.get('floor')  # Can be comma-separated
    status = request.args.get('status')
    sort_by = request.args.get('sort', 'name')  # name, floor, category
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = Store.query
    
    # Apply filters
    if mall_id:
        query = query.filter_by(mall_id=mall_id)
    
    if category_ids:
        cat_list = [int(c.strip()) for c in category_ids.split(',')]
        query = query.filter(Store.category_id.in_(cat_list))
    
    if floors:
        floor_list = [f.strip() for f in floors.split(',')]
        query = query.filter(Store.floor.in_(floor_list))
    
    if status:
        query = query.filter_by(status=status)
    
    # Apply sorting
    if sort_by == 'name':
        query = query.order_by(Store.name)
    elif sort_by == 'floor':
        query = query.order_by(Store.floor, Store.unit)
    elif sort_by == 'category':
        query = query.join(Category).order_by(Category.name, Store.name)
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    stores = pagination.items
    
    return jsonify({
        'stores': [store.to_dict() for store in stores],
        'count': len(stores),
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }), 200


@bp.route('/<int:store_id>', methods=['GET'])
def get_store(store_id):
    """Get store details"""
    store = Store.query.get(store_id)
    
    if not store:
        return jsonify({'error': 'Store not found'}), 404
    
    return jsonify({'store': store.to_dict()}), 200


@bp.route('/search', methods=['GET'])
def search_stores():
    """Advanced search stores with fuzzy matching"""
    query_text = request.args.get('q', '')
    mall_id = request.args.get('mall_id', type=int)
    category_id = request.args.get('category_id', type=int)
    floor = request.args.get('floor')
    sort_by = request.args.get('sort', 'relevance')  # relevance, name, floor
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not query_text:
        return jsonify({'error': 'Search query required'}), 400
    
    # Build search query with fuzzy matching
    search_pattern = f'%{query_text}%'
    query = Store.query.filter(
        or_(
            Store.name.ilike(search_pattern),
            Store.description.ilike(search_pattern)
        )
    )
    
    # Apply additional filters
    if mall_id:
        query = query.filter_by(mall_id=mall_id)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if floor:
        query = query.filter_by(floor=floor)
    
    # Apply sorting
    if sort_by == 'name':
        query = query.order_by(Store.name)
    elif sort_by == 'floor':
        query = query.order_by(Store.floor, Store.unit)
    # For relevance, we keep the default order (exact matches first due to ilike)
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    stores = pagination.items
    
    return jsonify({
        'stores': [store.to_dict() for store in stores],
        'query': query_text,
        'count': len(stores),
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }), 200


@bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories with store counts"""
    categories = Category.query.all()
    
    result = []
    for cat in categories:
        cat_dict = cat.to_dict()
        cat_dict['store_count'] = Store.query.filter_by(category_id=cat.id).count()
        result.append(cat_dict)
    
    return jsonify({
        'categories': result,
        'count': len(result)
    }), 200


@bp.route('/floors', methods=['GET'])
def get_floors():
    """Get list of all floors with store counts"""
    mall_id = request.args.get('mall_id', 1, type=int)
    
    # Get distinct floors
    floors_query = db.session.query(
        Store.floor,
        db.func.count(Store.id).label('store_count')
    ).filter_by(mall_id=mall_id).group_by(Store.floor).all()
    
    floors = [
        {'floor': floor, 'store_count': count}
        for floor, count in floors_query
    ]
    
    return jsonify({
        'floors': floors,
        'count': len(floors)
    }), 200


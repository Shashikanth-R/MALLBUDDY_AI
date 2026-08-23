from flask import Blueprint, request, jsonify
from datetime import date
from app import db
from app.models import Offer

bp = Blueprint('offers', __name__, url_prefix='/api/offers')


@bp.route('/', methods=['GET'])
def get_offers():
    """Get all active offers"""
    mall_id = request.args.get('mall_id', type=int)
    store_id = request.args.get('store_id', type=int)
    
    query = Offer.query.filter(
        Offer.is_active == True,
        Offer.start_date <= date.today(),
        Offer.end_date >= date.today()
    )
    
    if mall_id:
        query = query.join(Offer.store).filter_by(mall_id=mall_id)
    if store_id:
        query = query.filter_by(store_id=store_id)
    
    offers = query.all()
    
    return jsonify({
        'offers': [offer.to_dict() for offer in offers],
        'count': len(offers)
    }), 200


@bp.route('/<int:offer_id>', methods=['GET'])
def get_offer(offer_id):
    """Get offer details"""
    offer = Offer.query.get(offer_id)
    
    if not offer:
        return jsonify({'error': 'Offer not found'}), 404
    
    return jsonify({'offer': offer.to_dict()}), 200


@bp.route('/featured', methods=['GET'])
def get_featured_offers():
    """Get featured offers"""
    mall_id = request.args.get('mall_id', type=int)
    
    query = Offer.query.filter(
        Offer.is_active == True,
        Offer.is_featured == True,
        Offer.start_date <= date.today(),
        Offer.end_date >= date.today()
    )
    
    if mall_id:
        query = query.join(Offer.store).filter_by(mall_id=mall_id)
    
    offers = query.all()
    
    return jsonify({
        'offers': [offer.to_dict() for offer in offers],
        'count': len(offers)
    }), 200

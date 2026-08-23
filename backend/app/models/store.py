from datetime import datetime
from app import db


class Store(db.Model):
    """Store model"""
    __tablename__ = 'stores'

    id = db.Column(db.Integer, primary_key=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False, index=True)
    floor = db.Column(db.String(20), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='open')  # open, closed, temporarily_closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    offers = db.relationship('Offer', backref='store', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Store {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mall_id': self.mall_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'name': self.name,
            'floor': self.floor,
            'unit': self.unit,
            'description': self.description,
            'logo_url': self.logo_url,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

from datetime import datetime
from app import db


class Mall(db.Model):
    """Mall model"""
    __tablename__ = 'malls'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    operating_hours = db.Column(db.JSON)  # {"mon-thu": "10:00-22:00", "fri-sun": "10:00-23:00"}
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stores = db.relationship('Store', backref='mall', lazy='dynamic', cascade='all, delete-orphan')
    facilities = db.relationship('Facility', backref='mall', lazy='dynamic', cascade='all, delete-orphan')
    routes = db.relationship('Route', backref='mall', lazy='dynamic', cascade='all, delete-orphan')
    events = db.relationship('Event', backref='mall', lazy='dynamic', cascade='all, delete-orphan')
    knowledge_docs = db.relationship('KnowledgeDoc', backref='mall', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Mall {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'address': self.address,
            'operating_hours': self.operating_hours,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Category(db.Model):
    """Store category model"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # emoji or icon name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    stores = db.relationship('Store', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon
        }


class Facility(db.Model):
    """Mall facility model (washroom, parking, ATM, etc.)"""
    __tablename__ = 'facilities'

    id = db.Column(db.Integer, primary_key=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # washroom, parking, atm, food_court, etc.
    floor = db.Column(db.String(20))
    unit = db.Column(db.String(50))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Facility {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mall_id': self.mall_id,
            'name': self.name,
            'type': self.type,
            'floor': self.floor,
            'unit': self.unit,
            'description': self.description,
            'is_active': self.is_active
        }

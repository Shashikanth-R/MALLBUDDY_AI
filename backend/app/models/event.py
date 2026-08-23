from datetime import datetime
from app import db


class Event(db.Model):
    """Event model"""
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))  # Floor/area in mall
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Event {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mall_id': self.mall_id,
            'mall_name': self.mall.name if self.mall else None,
            'name': self.name,
            'description': self.description,
            'event_date': self.event_date.isoformat(),
            'location': self.location,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Route(db.Model):
    """Navigation route model"""
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id'), nullable=False)
    from_location = db.Column(db.String(200), nullable=False)
    to_location = db.Column(db.String(200), nullable=False)
    steps = db.Column(db.JSON, nullable=False)  # List of step-by-step directions
    estimated_time = db.Column(db.Integer)  # in minutes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Route {self.from_location} -> {self.to_location}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mall_id': self.mall_id,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'steps': self.steps,
            'estimated_time': self.estimated_time,
            'is_active': self.is_active
        }

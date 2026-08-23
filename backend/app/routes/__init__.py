# Import all route blueprints
from app.routes.auth import bp as auth_bp
from app.routes.chat import bp as chat_bp
from app.routes.stores import bp as stores_bp
from app.routes.offers import bp as offers_bp
from app.routes.events import bp as events_bp
from app.routes.facilities import bp as facilities_bp
from app.routes.navigation import bp as navigation_bp

__all__ = [
    'auth_bp',
    'chat_bp',
    'stores_bp',
    'offers_bp',
    'events_bp',
    'facilities_bp',
    'navigation_bp'
]

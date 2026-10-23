# Python 3.14 compatibility fix
import sys
if sys.version_info >= (3, 14):
    # Workaround for metaclass issues in Python 3.14
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from app.config import Config

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


@jwt.user_identity_loader
def user_identity_lookup(identity):
    return str(identity) if identity is not None else None


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Verify primary database connectivity; if unreachable (e.g. suspended cloud database),
    # safely fall back to local SQLite so the application stays fully functional.
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///mallbuddy.db')
    if db_uri and not db_uri.startswith('sqlite'):
        try:
            from sqlalchemy import create_engine
            test_engine = create_engine(db_uri, connect_args={'connect_timeout': 3})
            with test_engine.connect() as conn:
                pass
            test_engine.dispose()
        except Exception as conn_err:
            app.logger.warning("Configured database connection failed (%s). Falling back to SQLite.", conn_err)
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mallbuddy.db'

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS to allow all origins in development
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Register blueprints
    from app.routes import auth, chat, stores, offers, events, facilities, navigation, tracking
    # Temporarily disable analytics to fix startup
    # Temporarily disable analytics to fix startup
    from app.routes import admin_routes
    app.register_blueprint(chat.bp, url_prefix='/api/chat')
    app.register_blueprint(navigation.bp, url_prefix='/api/navigation')
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(stores.bp)
    app.register_blueprint(offers.bp)
    app.register_blueprint(events.bp)
    app.register_blueprint(facilities.bp)
    app.register_blueprint(tracking.bp)
    # app.register_blueprint(analytics.bp)  # Temporarily disabled

    # Root endpoint - API documentation
    @app.route('/')
    def index():
        return {
            'service': 'MallBuddy API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/health',
                'auth': {
                    'register': 'POST /api/auth/register',
                    'login': 'POST /api/auth/login',
                    'profile': 'GET /api/auth/profile'
                },
                'stores': {
                    'list': 'GET /api/stores',
                    'get': 'GET /api/stores/<id>',
                    'search': 'GET /api/stores/search?q=<query>'
                },
                'offers': {
                    'list': 'GET /api/offers',
                    'featured': 'GET /api/offers/featured'
                },
                'events': {
                    'list': 'GET /api/events',
                    'upcoming': 'GET /api/events/upcoming'
                },
                'facilities': {
                    'list': 'GET /api/facilities',
                    'by_type': 'GET /api/facilities?type=<type>'
                },
                'navigation': {
                    'route': 'GET /api/navigation?from=<location>&to=<location>',
                    'map': 'GET /api/navigation/map/<mall_id>'
                },
                'chat': {
                    'send': 'POST /api/chat',
                    'history': 'GET /api/chat/history?session_id=<id>'
                },
                'admin': {
                    'stats': 'GET /api/admin/dashboard/stats'
                }
            },
            'documentation': 'Visit http://localhost:3000 for the frontend application'
        }, 200
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'MallBuddy API'}, 200

    @app.route('/api/debug/db')
    def debug_db():
        from sqlalchemy import inspect
        diag = {
            'dialect': db.engine.dialect.name,
            'driver': db.engine.url.drivername,
            'tables': [],
            'error': None
        }
        try:
            inspector = inspect(db.engine)
            diag['tables'] = inspector.get_table_names()
        except Exception as e:
            diag['error'] = str(e)
        return diag, 200

    @app.errorhandler(500)
    def handle_500(e):
        import traceback
        tb = traceback.format_exc()
        app.logger.error(f"500 Error: {e}\n{tb}")
        from flask import jsonify
        return jsonify({
            'error': 'Internal Server Error',
            'detail': str(e),
            'traceback': tb
        }), 500

    with app.app_context():
        using_sqlite = db.engine.dialect.name == 'sqlite'
        app.logger.info('Database dialect in use: %s', db.engine.dialect.name)
        try:
            db.create_all()
            app.logger.info('Database tables created/verified')
        except Exception as e:
            app.logger.error('Failed to create database tables: %s', e)

        
        # Seed default admin user if not exists
        try:
            from app.models import Admin
            from werkzeug.security import generate_password_hash
            
            admin_email = app.config.get('ADMIN_EMAIL', 'admin@mallbuddy.com')
            admin = Admin.query.filter_by(email=admin_email).first()
            
            if not admin:
                print(f"Creating default admin user: {admin_email}")
                admin_pass = app.config.get('ADMIN_PASSWORD', 'Admin@123')
                
                new_admin = Admin(
                    name='System Administrator',
                    email=admin_email,
                    password_hash=generate_password_hash(admin_pass),
                    role='super_admin',
                    is_active=True
                )
                db.session.add(new_admin)
                db.session.commit()
                print("✅ Default admin user created successfully")
            else:
                print("Admin user already exists")
        except Exception as e:
            print(f"❌ Failed to seed admin user: {e}")
        
        # Seed default Mall if not exists
        try:
            from app.models import Mall
            
            if Mall.query.count() == 0:
                print("Seeding default Mall...")
                mall = Mall(
                    name="Elements Mall",
                    city="Bangalore",
                    address="123 MG Road, Bangalore, Karnataka 560001",
                    operating_hours={
                        "mon-thu": "10:00 AM - 10:00 PM",
                        "fri-sun": "10:00 AM - 11:00 PM"
                    }
                )
                db.session.add(mall)
                db.session.commit()
                print("✅ Default Mall created successfully")
            else:
                print("Mall already exists")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to seed mall: {e}")
        
        # Seed default Categories if not exists
        try:
            from app.models import Category
            
            if Category.query.count() == 0:
                print("Seeding default Categories...")
                default_categories = [
                    {"name": "Fashion", "icon": "👗", "description": "Clothing and apparel stores"},
                    {"name": "Food & Beverages", "icon": "🍔", "description": "Restaurants and food courts"},
                    {"name": "Electronics", "icon": "📱", "description": "Electronics and gadgets"},
                    {"name": "Entertainment", "icon": "🎬", "description": "Movies, games, and entertainment"},
                    {"name": "Beauty", "icon": "💄", "description": "Beauty and cosmetics"},
                    {"name": "Sports", "icon": "⚽", "description": "Sports and fitness"},
                    {"name": "Home & Lifestyle", "icon": "🏠", "description": "Home decor and lifestyle products"},
                    {"name": "Kids", "icon": "🧸", "description": "Toys, kids clothing, and accessories"}
                ]
                
                for cat_data in default_categories:
                    cat = Category(**cat_data)
                    db.session.add(cat)
                
                db.session.commit()
                print(f"✅ {len(default_categories)} Categories created successfully")
            else:
                print(f"Categories already exist ({Category.query.count()} found)")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to seed categories: {e}")
        
        # Seed default Stores if not exists (based on floor-layouts.js)
        try:
            from app.models import Store
            
            if Store.query.count() == 0:
                print("Seeding default Stores...")
                # mall_id=1 (Elements Mall)
                # Categories: 1=Fashion, 2=Food&Beverages, 3=Electronics, 4=Entertainment, 5=Beauty, 6=Sports
                default_stores = [
                    # Floor 1 - Fashion & Lifestyle
                    {"name": "Zara", "mall_id": 1, "category_id": 1, "floor": "1", "unit": "105", "description": "International fashion brand", "status": "open"},
                    {"name": "H&M", "mall_id": 1, "category_id": 1, "floor": "1", "unit": "110", "description": "Affordable fashion for all", "status": "open"},
                    {"name": "Starbucks", "mall_id": 1, "category_id": 2, "floor": "1", "unit": "115", "description": "Premium coffee and beverages", "status": "open"},
                    
                    # Floor 2 - Sports & Electronics
                    {"name": "Adidas", "mall_id": 1, "category_id": 6, "floor": "2", "unit": "205", "description": "Sports apparel and shoes", "status": "open"},
                    {"name": "Nike", "mall_id": 1, "category_id": 6, "floor": "2", "unit": "210", "description": "Athletic footwear and apparel", "status": "open"},
                    {"name": "Croma Electronics", "mall_id": 1, "category_id": 3, "floor": "2", "unit": "215", "description": "Electronics and gadgets store", "status": "open"},
                    
                    # Floor 3 - Food Court (unit 300 left vacant)
                    {"name": "McDonald's", "mall_id": 1, "category_id": 2, "floor": "3", "unit": "301", "description": "Fast food restaurant", "status": "open"},
                    {"name": "Pizza Hut", "mall_id": 1, "category_id": 2, "floor": "3", "unit": "305", "description": "Pizza and Italian cuisine", "status": "open"},
                    
                    # Floor 4 - Entertainment (unit 410 left vacant)
                    {"name": "PVR Cinemas", "mall_id": 1, "category_id": 4, "floor": "4", "unit": "401", "description": "Multiplex cinema with IMAX", "status": "open"},
                ]
                
                for store_data in default_stores:
                    store = Store(**store_data)
                    db.session.add(store)
                
                db.session.commit()
                print(f"✅ {len(default_stores)} Stores created successfully (2 units left vacant: 300, 410)")
            else:
                print(f"Stores already exist ({Store.query.count()} found)")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to seed stores: {e}")

    return app

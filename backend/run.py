import os
from app import create_app, db
from app.models import *

# Create Flask app
app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Make database and models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Admin': Admin,
        'Mall': Mall,
        'Category': Category,
        'Facility': Facility,
        'Store': Store,
        'Offer': Offer,
        'Event': Event,
        'Route': Route,
        'ChatSession': ChatSession,
        'ChatMessage': ChatMessage,
        'Feedback': Feedback,
        'KnowledgeDoc': KnowledgeDoc,
        'ChatbotSettings': ChatbotSettings,
        'AuditLog': AuditLog
    }


@app.cli.command()
def init_db():
    """Initialize local SQLite development tables only."""
    if db.engine.dialect.name != 'sqlite':
        print("PostgreSQL schema is externally managed; init-db will not run db.create_all().")
        return
    db.create_all()
    print("Database initialized!")


@app.cli.command()
def seed_db():
    """Seed the database with sample data"""
    from datetime import date, datetime, timedelta
    from werkzeug.security import generate_password_hash
    
    print("Seeding database...")
    
    # Create admin
    admin = Admin(
        name="Admin User",
        email=app.config['ADMIN_EMAIL'],
        password_hash=generate_password_hash(app.config['ADMIN_PASSWORD']),
        role="super_admin"
    )
    db.session.add(admin)
    
    # Create sample mall
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
    
    # Create categories
    categories_data = [
        {"name": "Fashion", "icon": "👗", "description": "Clothing and apparel stores"},
        {"name": "Food", "icon": "🍔", "description": "Restaurants and food courts"},
        {"name": "Electronics", "icon": "📱", "description": "Electronics and gadgets"},
        {"name": "Entertainment", "icon": "🎬", "description": "Movies, games, and entertainment"},
        {"name": "Beauty", "icon": "💄", "description": "Beauty and cosmetics"},
        {"name": "Sports", "icon": "⚽", "description": "Sports and fitness"}
    ]
    
    categories = {}
    for cat_data in categories_data:
        cat = Category(**cat_data)
        db.session.add(cat)
        categories[cat_data['name']] = cat
    
    db.session.commit()
    
    # Create stores
    stores_data = [
        {"name": "Adidas", "category": "Sports", "floor": "2", "unit": "205", "status": "open"},
        {"name": "Zara", "category": "Fashion", "floor": "1", "unit": "105", "status": "open"},
        {"name": "Nike", "category": "Sports", "floor": "2", "unit": "210", "status": "open"},
        {"name": "H&M", "category": "Fashion", "floor": "1", "unit": "110", "status": "open"},
        {"name": "PVR Cinemas", "category": "Entertainment", "floor": "4", "unit": "401", "status": "open"},
        {"name": "McDonald's", "category": "Food", "floor": "3", "unit": "301", "status": "open"},
        {"name": "Starbucks", "category": "Food", "floor": "1", "unit": "115", "status": "open"},
    ]
    
    stores = {}
    for store_data in stores_data:
        cat_name = store_data.pop('category')
        store = Store(
            mall_id=mall.id,
            category_id=categories[cat_name].id,
            **store_data
        )
        db.session.add(store)
        stores[store_data['name']] = store
    
    db.session.commit()
    
    # Create facilities
    facilities_data = [
        {"name": "Washroom - Floor 1", "type": "washroom", "floor": "1", "unit": "101"},
        {"name": "Washroom - Floor 2", "type": "washroom", "floor": "2", "unit": "201"},
        {"name": "Parking - Basement", "type": "parking", "floor": "B1", "unit": "P1"},
        {"name": "ATM - HDFC", "type": "atm", "floor": "1", "unit": "102"},
        {"name": "Food Court", "type": "food_court", "floor": "3", "unit": "300"},
    ]
    
    for fac_data in facilities_data:
        facility = Facility(mall_id=mall.id, **fac_data)
        db.session.add(facility)
    
    db.session.commit()
    
    # Create offers
    today = date.today()
    offers_data = [
        {
            "store": "Zara",
            "title": "30% off on Winter Collection",
            "description": "Get 30% discount on all winter wear",
            "start_date": today,
            "end_date": today + timedelta(days=30),
            "is_featured": True
        },
        {
            "store": "Nike",
            "title": "Buy 2 Get 1 Free",
            "description": "Buy any 2 items and get 1 free",
            "start_date": today,
            "end_date": today + timedelta(days=15),
            "is_featured": True
        },
        {
            "store": "PVR Cinemas",
            "title": "20% off on Movie Tickets",
            "description": "Book tickets online and get 20% discount",
            "start_date": today,
            "end_date": today + timedelta(days=7),
            "is_featured": False
        }
    ]
    
    for offer_data in offers_data:
        store_name = offer_data.pop('store')
        offer = Offer(store_id=stores[store_name].id, **offer_data)
        db.session.add(offer)
    
    db.session.commit()
    
    # Create events
    events_data = [
        {
            "name": "Weekend Music Festival",
            "description": "Live music performances by local artists",
            "event_date": datetime.now() + timedelta(days=5),
            "location": "Central Atrium, Floor 1"
        },
        {
            "name": "Kids Carnival",
            "description": "Fun activities and games for children",
            "event_date": datetime.now() + timedelta(days=10),
            "location": "Food Court Area, Floor 3"
        }
    ]
    
    for event_data in events_data:
        event = Event(mall_id=mall.id, **event_data)
        db.session.add(event)
    
    db.session.commit()
    
    # Create chatbot settings
    settings_data = [
        {"key": "rag_enabled", "value": "true", "description": "Enable RAG retrieval"},
        {"key": "llm_fallback", "value": "true", "description": "Allow LLM fallback"},
        {"key": "verbosity", "value": "normal", "description": "Response verbosity level"},
        {"key": "guest_mode", "value": "true", "description": "Allow guest users"}
    ]
    
    for setting_data in settings_data:
        setting = ChatbotSettings(**setting_data)
        db.session.add(setting)
    
    db.session.commit()
    
    print("Database seeded successfully!")
    print(f"Admin email: {app.config['ADMIN_EMAIL']}")
    print(f"Admin password: {app.config['ADMIN_PASSWORD']}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

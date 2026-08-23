# Import all models for easy access
from app.models.user import User, Admin
from app.models.mall import Mall, Category, Facility
from app.models.store import Store
from app.models.offer import Offer
from app.models.event import Event, Route
from app.models.chat import (
    ChatSession,
    ChatMessage,
    Feedback,
    KnowledgeDoc,
    ChatbotSettings,
    AuditLog
)
from app.models.analytics import (
    VisitorSession, UserEvent, DailyMallMetric, StorePerformance,
    CategoryDemand, OfferPerformance, CustomerSegment, AIBusinessInsight
)

__all__ = [
    'User',
    'Admin',
    'Mall',
    'Category',
    'Facility',
    'Store',
    'Offer',
    'Event',
    'Route',
    'ChatSession',
    'ChatMessage',
    'Feedback',
    'KnowledgeDoc',
    'ChatbotSettings',
    'AuditLog',
    'VisitorSession',
    'UserEvent',
    'DailyMallMetric',
    'StorePerformance',
    'CategoryDemand',
    'OfferPerformance',
    'CustomerSegment',
    'AIBusinessInsight'
]

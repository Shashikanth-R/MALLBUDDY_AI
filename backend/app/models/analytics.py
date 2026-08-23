"""SQLAlchemy mappings for the existing PostgreSQL analytics extension.

The database/mallbuddy_schema.sql file remains the schema source of truth.
These models intentionally map its existing columns without creating or
altering analytics tables at runtime.
"""
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app import db


# PostgreSQL receives JSONB, exactly as defined by the analytics schema.  The
# SQLite variant exists solely so the project's unit tests can run locally.
JSONB_COMPAT = db.JSON().with_variant(JSONB, 'postgresql')
NOW_DEFAULT = db.text('CURRENT_TIMESTAMP')
ZERO_DEFAULT = db.text('0')
TRUE_DEFAULT = db.text('TRUE')
FALSE_DEFAULT = db.text('FALSE')
EMPTY_JSON_DEFAULT = db.text("'{}'")


class VisitorSession(db.Model):
    __tablename__ = 'visitor_sessions'

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=NOW_DEFAULT)
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)
    device_type = db.Column(db.String(30), nullable=True)
    is_guest = db.Column(db.Boolean, nullable=False, default=True, server_default=TRUE_DEFAULT)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=NOW_DEFAULT)

    __table_args__ = (
        db.Index('idx_visitor_sessions_mall_time', 'mall_id', 'started_at'),
        db.Index('idx_visitor_sessions_user', 'user_id'),
    )


class UserEvent(db.Model):
    __tablename__ = 'user_events'

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    session_id = db.Column(db.BigInteger, db.ForeignKey('visitor_sessions.id', ondelete='SET NULL'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    event_type = db.Column(db.String(60), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id', ondelete='SET NULL'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='SET NULL'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='SET NULL'), nullable=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id', ondelete='SET NULL'), nullable=True)
    search_query = db.Column(db.Text, nullable=True)
    metadata_ = db.Column('metadata', JSONB_COMPAT, nullable=False, default=dict, server_default=EMPTY_JSON_DEFAULT)
    is_synthetic = db.Column(db.Boolean, nullable=False, default=False, server_default=FALSE_DEFAULT)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=NOW_DEFAULT)

    __table_args__ = (
        db.Index('idx_user_events_mall_time', 'mall_id', 'created_at'),
        db.Index('idx_user_events_type_time', 'event_type', 'created_at'),
        db.Index('idx_user_events_store_time', 'store_id', 'created_at'),
        db.Index('idx_user_events_category_time', 'category_id', 'created_at'),
        db.Index('idx_user_events_offer_time', 'offer_id', 'created_at'),
        db.Index('idx_user_events_session', 'session_id'),
        db.Index('idx_user_events_search', 'search_query'),
        db.Index('idx_user_events_metadata', 'metadata', postgresql_using='gin'),
    )


class DailyMallMetric(db.Model):
    __tablename__ = 'daily_mall_metrics'
    __table_args__ = (db.UniqueConstraint('mall_id', 'metric_date'), db.Index('idx_daily_mall_metrics_date', 'mall_id', 'metric_date'))

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    metric_date = db.Column(db.Date, nullable=False)
    total_sessions = db.Column(db.Integer, nullable=False, default=0, server_default=ZERO_DEFAULT)
    unique_visitors = db.Column(db.Integer, nullable=False, default=0)
    total_events = db.Column(db.Integer, nullable=False, default=0)
    store_searches = db.Column(db.Integer, nullable=False, default=0)
    store_views = db.Column(db.Integer, nullable=False, default=0)
    navigation_requests = db.Column(db.Integer, nullable=False, default=0)
    offer_views = db.Column(db.Integer, nullable=False, default=0)
    offer_clicks = db.Column(db.Integer, nullable=False, default=0)
    recommendation_views = db.Column(db.Integer, nullable=False, default=0)
    recommendation_clicks = db.Column(db.Integer, nullable=False, default=0)
    ai_queries = db.Column(db.Integer, nullable=False, default=0)
    feedback_count = db.Column(db.Integer, nullable=False, default=0)
    avg_session_seconds = db.Column(db.Numeric(12, 2), default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=NOW_DEFAULT)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=NOW_DEFAULT)


class StorePerformance(db.Model):
    __tablename__ = 'store_performance'
    __table_args__ = (db.UniqueConstraint('mall_id', 'store_id', 'period_start', 'period_end'), db.Index('idx_store_performance_mall_period', 'mall_id', 'period_start', 'period_end'), db.Index('idx_store_performance_store', 'store_id'))

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    search_count = db.Column(db.Integer, nullable=False, default=0)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    navigation_count = db.Column(db.Integer, nullable=False, default=0)
    offer_views = db.Column(db.Integer, nullable=False, default=0)
    offer_clicks = db.Column(db.Integer, nullable=False, default=0)
    recommendation_views = db.Column(db.Integer, nullable=False, default=0)
    recommendation_clicks = db.Column(db.Integer, nullable=False, default=0)
    favorite_count = db.Column(db.Integer, nullable=False, default=0)
    feedback_count = db.Column(db.Integer, nullable=False, default=0)
    engagement_score = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class CategoryDemand(db.Model):
    __tablename__ = 'category_demand'
    __table_args__ = (db.UniqueConstraint('mall_id', 'category_id', 'period_start', 'period_end'), db.Index('idx_category_demand_mall_period', 'mall_id', 'period_start', 'period_end'), db.Index('idx_category_demand_score', db.desc('demand_score')))

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    search_count = db.Column(db.Integer, nullable=False, default=0)
    unique_sessions = db.Column(db.Integer, nullable=False, default=0)
    store_views = db.Column(db.Integer, nullable=False, default=0)
    navigation_count = db.Column(db.Integer, nullable=False, default=0)
    offer_interactions = db.Column(db.Integer, nullable=False, default=0)
    active_store_count = db.Column(db.Integer, nullable=False, default=0)
    previous_period_search_count = db.Column(db.Integer, nullable=False, default=0)
    growth_rate = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    demand_score = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    supply_gap_score = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    demand_level = db.Column(db.String(30), nullable=False, default='normal')
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class OfferPerformance(db.Model):
    __tablename__ = 'offer_performance'
    __table_args__ = (db.UniqueConstraint('offer_id', 'period_start', 'period_end'), db.Index('idx_offer_performance_mall_period', 'mall_id', 'period_start', 'period_end'), db.Index('idx_offer_performance_offer', 'offer_id'))

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    impressions = db.Column(db.Integer, nullable=False, default=0)
    views = db.Column(db.Integer, nullable=False, default=0)
    clicks = db.Column(db.Integer, nullable=False, default=0)
    saves = db.Column(db.Integer, nullable=False, default=0)
    redemptions = db.Column(db.Integer, nullable=False, default=0)
    ctr = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    conversion_rate = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class CustomerSegment(db.Model):
    __tablename__ = 'customer_segments'
    __table_args__ = (db.UniqueConstraint('mall_id', 'user_id', 'model_version'), db.Index('idx_customer_segments_mall', 'mall_id'), db.Index('idx_customer_segments_segment', 'mall_id', 'segment_number'))

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    session_id = db.Column(db.BigInteger, db.ForeignKey('visitor_sessions.id', ondelete='SET NULL'), nullable=True)
    segment_number = db.Column(db.Integer, nullable=False)
    segment_name = db.Column(db.String(100), nullable=True)
    model_version = db.Column(db.String(50), nullable=False)
    feature_snapshot = db.Column(JSONB_COMPAT, nullable=False, default=dict)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AIBusinessInsight(db.Model):
    __tablename__ = 'ai_business_insights'

    id = db.Column(db.BigInteger().with_variant(db.Integer(), 'sqlite'), primary_key=True, autoincrement=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id', ondelete='CASCADE'), nullable=False)
    insight_type = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(30), default='info')
    evidence = db.Column(JSONB_COMPAT, nullable=False, default=dict)
    model_name = db.Column(db.String(100), nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    period_start = db.Column(db.Date, nullable=True)
    period_end = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='active')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.Index('idx_ai_insights_mall_status', 'mall_id', 'status'),
        db.Index('idx_ai_insights_created', db.desc('created_at')),
    )

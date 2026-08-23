"""Failure-isolated analytics event and visitor-session tracking."""
import logging
import secrets
from datetime import datetime, timezone

from app import db
from app.models.analytics import UserEvent, VisitorSession

logger = logging.getLogger(__name__)


def create_visitor_session(mall_id, user_id=None, device_type=None, session_token=None):
    """Create or return an opaque visitor session token for a mall visit."""
    session = VisitorSession.query.filter_by(session_token=session_token).first() if session_token else None
    if session:
        if session.mall_id != mall_id:
            raise ValueError('Visitor session does not belong to this mall')
        if user_id and session.user_id is None:
            session.user_id = user_id
            session.is_guest = False
            db.session.commit()
        return session

    # Never use a caller-supplied unknown token.  New sessions are always
    # assigned high-entropy, server-generated identifiers.
    token = secrets.token_urlsafe(32)
    session = VisitorSession(
        session_token=token,
        mall_id=mall_id,
        user_id=user_id,
        device_type=device_type,
        is_guest=user_id is None,
    )
    db.session.add(session)
    db.session.commit()
    return session


def track_event(*, mall_id, session_token, event_type, user_id=None, store_id=None,
                category_id=None, offer_id=None, event_id=None, facility_id=None,
                search_query=None, metadata=None, is_synthetic=False):
    """Persist a normalized event without allowing telemetry failures to escape."""
    try:
        visitor_session = create_visitor_session(
            mall_id=mall_id, user_id=user_id, session_token=session_token
        )
        event = UserEvent(
            session_id=visitor_session.id,
            user_id=user_id,
            mall_id=mall_id,
            event_type=event_type,
            store_id=store_id,
            category_id=category_id,
            offer_id=offer_id,
            event_id=event_id,
            facility_id=facility_id,
            search_query=search_query,
            metadata_=metadata or {},
            is_synthetic=bool(is_synthetic),
        )
        db.session.add(event)
        db.session.commit()
        return event
    except Exception:
        db.session.rollback()
        logger.exception('Analytics event tracking failed for %s', event_type)
        return None


def end_visitor_session(session_token, mall_id):
    """Mark a visitor session ended. Returns False for an unknown/mismatched token."""
    try:
        session = VisitorSession.query.filter_by(session_token=session_token, mall_id=mall_id).first()
        if not session:
            return False
        if session.ended_at is None:
            session.ended_at = datetime.now(timezone.utc)
            db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        logger.exception('Unable to end analytics visitor session')
        return False

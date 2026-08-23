from datetime import datetime
from app import db


class ChatSession(db.Model):
    """Chat session model"""
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for guest users
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ChatSession {self.session_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'mall_id': self.mall_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class ChatMessage(db.Model):
    """Chat message model"""
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, bot
    message = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50))  # Detected intent
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<ChatMessage {self.role}: {self.message[:30]}>'

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'message': self.message,
            'intent': self.intent,
            'timestamp': self.timestamp.isoformat()
        }


class Feedback(db.Model):
    """User feedback model"""
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100))
    type = db.Column(db.String(50), nullable=False)  # wrong_navigation, missing_store, incorrect_response, etc.
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Feedback {self.type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'type': self.type,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class KnowledgeDoc(db.Model):
    """Knowledge base document model for RAG"""
    __tablename__ = 'knowledge_docs'

    id = db.Column(db.Integer, primary_key=True)
    mall_id = db.Column(db.Integer, db.ForeignKey('malls.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    doc_type = db.Column(db.String(50))  # pdf, txt, md
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    indexed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<KnowledgeDoc {self.filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mall_id': self.mall_id,
            'filename': self.filename,
            'doc_type': self.doc_type,
            'is_active': self.is_active,
            'uploaded_at': self.uploaded_at.isoformat(),
            'indexed_at': self.indexed_at.isoformat() if self.indexed_at else None
        }


class ChatbotSettings(db.Model):
    """Chatbot configuration settings"""
    __tablename__ = 'chatbot_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ChatbotSettings {self.key}>'

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat()
        }


class AuditLog(db.Model):
    """Admin action audit log"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # create, update, delete
    entity_type = db.Column(db.String(50), nullable=False)  # store, offer, event, etc.
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'admin_email': self.admin.email if self.admin else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

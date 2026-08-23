from flask import Blueprint, request, jsonify
from app import db
from app.models import ChatSession, ChatMessage, Store, Offer, Event
from app.services.gemini_chatbot import get_gemini_chatbot

bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Initialize Gemini-powered chatbot
chatbot = get_gemini_chatbot()



@bp.route('/', methods=['POST'])
def chat():
    """Main chatbot endpoint with OpenAI integration"""
    data = request.get_json()
    
    if not data or not data.get('user_message'):
        return jsonify({'error': 'user_message required'}), 400
    
    session_id = data.get('session_id')
    user_message = data.get('user_message')
    mall_id = data.get('mall_id', 1)
    
    # Get or create session
    session = ChatSession.query.filter_by(session_id=session_id).first()
    if not session:
        session = ChatSession(
            session_id=session_id,
            mall_id=mall_id
        )
        db.session.add(session)
        db.session.commit()
    
    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role='user',
        message=user_message
    )
    db.session.add(user_msg)
    db.session.commit()
    
    # Get session history for context
    history = ChatMessage.query.filter_by(
        session_id=session.id
    ).order_by(ChatMessage.timestamp).all()
    
    # Gather database context for better responses
    db_context = {
        'stores': [s.to_dict() for s in Store.query.filter_by(mall_id=mall_id).limit(10).all()],
        'offers': [o.to_dict() for o in Offer.query.limit(5).all()],
        'events': [e.to_dict() for e in Event.query.limit(3).all()]
    }
    
    # Generate intelligent response using conversational chatbot
    try:
        result = chatbot.generate_response(
            user_message=user_message,
            session_id=session_id,
            db_context=db_context
        )
        
        response_text = result.get('response', 'I apologize, but I encountered an error.')
        suggestions = result.get('suggestions', [])
        intent = 'conversational'
        
    except Exception as e:
        # Fallback if chatbot service fails
        print(f"❌ Chatbot Error: {e}")
        import traceback
        traceback.print_exc()
        response_text = "I'm having a bit of trouble right now. Please try again! 😊"
        intent = 'error'
        suggestions = ['Show me stores', 'What offers are available?', 'Upcoming events']
    
    # Save bot response
    bot_msg = ChatMessage(
        session_id=session.id,
        role='bot',
        message=response_text
    )
    db.session.add(bot_msg)
    db.session.commit()
    
    return jsonify({
        'response': response_text,
        'intent': intent,
        'suggestions': suggestions
    }), 200


@bp.route('/history', methods=['GET'])
def get_chat_history():
    """Get chat history for a session"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    
    session = ChatSession.query.filter_by(session_id=session_id).first()
    
    if not session:
        return jsonify({'messages': []}), 200
    
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.timestamp).all()
    
    return jsonify({
        'messages': [msg.to_dict() for msg in messages],
        'count': len(messages)
    }), 200


@bp.route('/clear', methods=['POST'])
def clear_history():
    """Clear chat history for a session"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    
    session = ChatSession.query.filter_by(session_id=session_id).first()
    
    if session:
        # Delete all messages for this session
        ChatMessage.query.filter_by(session_id=session.id).delete()
        db.session.commit()
    
    return jsonify({'message': 'Chat history cleared'}), 200


"""
Chatbot service module for MallBuddy
Handles intelligent conversation using OpenAI API
"""
import os
from app.models import Store, Offer, Event, Facility, Category
from app import db

# Try to import OpenAI, but make it optional
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ChatbotService:
    """Intelligent chatbot service using OpenAI"""
    
    def __init__(self):
        self.client = None
        api_key = os.getenv('OPENAI_API_KEY')
        
        if OPENAI_AVAILABLE and api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {e}")
                self.client = None
        
        self.model = "gpt-3.5-turbo"
    
    def detect_intent(self, message):
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Store/location queries
        if any(word in message_lower for word in ['where', 'location', 'find', 'floor']):
            return 'store_location'
        
        # Offer queries
        if any(word in message_lower for word in ['offer', 'discount', 'sale', 'deal', 'promotion']):
            return 'offers'
        
        # Event queries
        if any(word in message_lower for word in ['event', 'happening', 'activity', 'festival', 'show']):
            return 'events'
        
        # Facility queries
        if any(word in message_lower for word in ['washroom', 'toilet', 'parking', 'atm', 'food court']):
            return 'facilities'
        
        # Category/shopping queries
        if any(word in message_lower for word in ['shop', 'buy', 'looking for', 'need']):
            return 'shopping'
        
        return 'general'
    
    def get_context_data(self, intent, mall_id=1):
        """Get relevant data from database based on intent"""
        context = {}
        
        if intent == 'store_location':
            stores = Store.query.filter_by(mall_id=mall_id).all()
            context['stores'] = [
                {
                    'name': s.name,
                    'floor': s.floor,
                    'unit': s.unit,
                    'category': s.category.name if s.category else 'N/A'
                }
                for s in stores
            ]
        
        elif intent == 'offers':
            offers = Offer.query.join(Store).filter(
                Store.mall_id == mall_id,
                Offer.is_active == True
            ).all()
            context['offers'] = [
                {
                    'title': o.title,
                    'description': o.description,
                    'store': o.store.name,
                    'end_date': o.end_date.strftime('%Y-%m-%d')
                }
                for o in offers
            ]
        
        elif intent == 'events':
            events = Event.query.filter_by(mall_id=mall_id).all()
            context['events'] = [
                {
                    'name': e.name,
                    'description': e.description,
                    'date': e.event_date.strftime('%Y-%m-%d %H:%M'),
                    'location': e.location
                }
                for e in events
            ]
        
        elif intent == 'facilities':
            facilities = Facility.query.filter_by(mall_id=mall_id).all()
            context['facilities'] = [
                {
                    'name': f.name,
                    'type': f.type,
                    'floor': f.floor,
                    'unit': f.unit
                }
                for f in facilities
            ]
        
        elif intent == 'shopping':
            categories = Category.query.all()
            stores = Store.query.filter_by(mall_id=mall_id).all()
            context['categories'] = [c.name for c in categories]
            context['stores'] = [
                {
                    'name': s.name,
                    'category': s.category.name if s.category else 'N/A',
                    'floor': s.floor
                }
                for s in stores
            ]
        
        return context
    
    def generate_response(self, user_message, mall_id=1, session_history=None):
        """Generate intelligent response using OpenAI"""
        
        # Check if OpenAI client is available
        if not self.client:
            return self._fallback_response(user_message, mall_id)
        
        # Detect intent
        intent = self.detect_intent(user_message)
        
        # Get relevant context
        context_data = self.get_context_data(intent, mall_id)
        
        # Build system prompt
        system_prompt = f"""You are MallBuddy, a friendly and helpful AI assistant for Elements Mall in Bangalore.
Your role is to help visitors find stores, learn about offers, discover events, and navigate the mall.

Be conversational, friendly, and concise. Use emojis occasionally to be more engaging.

Current mall data:
{context_data}

Guidelines:
- If asked about store locations, provide the floor and unit number
- If asked about offers, mention the store name and discount details
- If asked about events, share the name, date, and location
- If the information isn't in the data, politely say you don't have that information
- Keep responses under 100 words unless more detail is needed
- Always be helpful and suggest related information when relevant
"""
        
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add session history if available (last 5 messages)
        if session_history:
            for msg in session_history[-5:]:
                messages.append({
                    "role": msg.role if msg.role != 'bot' else 'assistant',
                    "content": msg.message
                })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            
            bot_response = response.choices[0].message.content
            
            # Generate suggestions based on intent
            suggestions = self._generate_suggestions(intent)
            
            return {
                'response': bot_response,
                'intent': intent,
                'suggestions': suggestions
            }
        
        except Exception as e:
            # Fallback response if OpenAI fails
            return self._fallback_response(user_message, mall_id)
    
    def _fallback_response(self, user_message, mall_id=1):
        """Generate fallback response without OpenAI"""
        intent = self.detect_intent(user_message)
        context_data = self.get_context_data(intent, mall_id)
        
        # Simple rule-based responses
        if intent == 'store_location':
            stores = context_data.get('stores', [])
            if stores:
                store_list = ', '.join([s['name'] for s in stores[:5]])
                response = f"We have these stores: {store_list}. Which one are you looking for? 🏪"
            else:
                response = "I can help you find stores! What are you looking for? 🔍"
        
        elif intent == 'offers':
            offers = context_data.get('offers', [])
            if offers:
                offer_text = offers[0]
                response = f"🎉 {offer_text['title']} at {offer_text['store']}! {offer_text['description']}"
            else:
                response = "Check out our amazing offers! Visit our stores for the latest deals. 🛍️"
        
        elif intent == 'events':
            events = context_data.get('events', [])
            if events:
                event = events[0]
                response = f"📅 {event['name']} - {event['description']} at {event['location']}"
            else:
                response = "We have exciting events coming up! Stay tuned for updates. 🎪"
        
        elif intent == 'facilities':
            facilities = context_data.get('facilities', [])
            if facilities:
                fac_list = ', '.join([f['name'] for f in facilities[:3]])
                response = f"Our facilities include: {fac_list}. What do you need? 🚻"
            else:
                response = "We have washrooms, parking, ATMs, and food courts. What are you looking for? 🏢"
        
        else:
            response = "Hi! I'm MallBuddy 👋 I can help you find stores, discover offers, learn about events, and navigate the mall. What would you like to know?"
        
        suggestions = self._generate_suggestions(intent)
        
        return {
            'response': response,
            'intent': intent,
            'suggestions': suggestions
        }
    
    def _generate_suggestions(self, intent):
        """Generate follow-up suggestions based on intent"""
        suggestions_map = {
            'store_location': [
                'Show me all stores',
                'What categories are available?',
                'Where is the food court?'
            ],
            'offers': [
                'Show me featured offers',
                'Any discounts on fashion?',
                'What events are happening?'
            ],
            'events': [
                'Tell me about upcoming events',
                'Show me stores',
                'What offers are available?'
            ],
            'facilities': [
                'Where is parking?',
                'Show me washrooms',
                'Where is the ATM?'
            ],
            'shopping': [
                'Show me fashion stores',
                'Where is the food court?',
                'What offers are available?'
            ],
            'general': [
                'Show me stores',
                'What offers are available?',
                'Upcoming events'
            ]
        }
        
        return suggestions_map.get(intent, suggestions_map['general'])

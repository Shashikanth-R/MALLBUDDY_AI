"""
Enhanced Chatbot Service with Conversation Memory
Simple rule-based chatbot with database context
"""
import os
import re
from typing import List, Dict


class ConversationalChatbot:
    """Enhanced chatbot with conversation memory and database context"""
    
    def __init__(self):
        """Initialize chatbot"""
        self.conversation_history = {}
        print("✅ Conversational chatbot initialized")
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        return self.conversation_history[session_id]
    
    def add_to_history(self, session_id: str, role: str, content: str):
        """Add message to conversation history"""
        history = self.get_conversation_history(session_id)
        history.append({"role": role, "content": content})
        if len(history) > 10:
            self.conversation_history[session_id] = history[-10:]
    
    def find_store(self, query: str, stores: List[Dict]) -> Dict:
        """Find store by name"""
        query_lower = query.lower()
        for store in stores:
            if store['name'].lower() in query_lower or query_lower in store['name'].lower():
                return store
        return None
    
    def generate_response(self, user_message: str, session_id: str, db_context: Dict = None) -> Dict:
        """Generate conversational response with database context"""
        
        try:
            message_lower = user_message.lower()
            db_context = db_context or {}
            stores = db_context.get('stores', [])
            offers = db_context.get('offers', [])
            events = db_context.get('events', [])
            
            # Store location queries
            if any(word in message_lower for word in ['where', 'location', 'find', 'located']):
                store = self.find_store(user_message, stores)
                if store:
                    response = f"{store['name']} is located on Floor {store['floor']}, Unit {store['unit']}. "
                    if store.get('category_name'):
                        response += f"It's a {store['category_name']} store. "
                    response += "Would you like to know about their current offers?"
                    suggestions = ["What offers do they have?", "Show me more stores", "Upcoming events"]
                else:
                    response = f"I can help you find stores! We have {len(stores)} stores including "
                    response += ", ".join([s['name'] for s in stores[:3]])
                    if len(stores) > 3:
                        response += f" and {len(stores) - 3} more. Which store are you looking for?"
                    suggestions = [stores[0]['name'] if stores else "Show all stores", "Show me offers", "Upcoming events"]
            
            # Offers queries
            elif any(word in message_lower for word in ['offer', 'deal', 'discount', 'sale', 'promotion']):
                if offers:
                    response = f"We have {len(offers)} great offers! "
                    response += offers[0]['title'] + " at " + offers[0].get('store_name', 'our stores') + ". "
                    if len(offers) > 1:
                        response += f"Plus {len(offers) - 1} more offers available!"
                    suggestions = ["Tell me more", "Where is this store?", "Show all offers"]
                else:
                    response = "We don't have any active offers right now, but check back soon! Would you like to explore our stores or events?"
                    suggestions = ["Show me stores", "Upcoming events", "Store categories"]
            
            # Events queries
            elif any(word in message_lower for word in ['event', 'happening', 'activity', 'program']):
                if events:
                    event = events[0]
                    response = f"We have an exciting event: {event['name']} on {event['event_date']} at {event['location']}. "
                    if len(events) > 1:
                        response += f"Plus {len(events) - 1} more events coming up!"
                    suggestions = ["Tell me more", "Other events", "Show me stores"]
                else:
                    response = "No events scheduled right now, but stay tuned! Would you like to explore our stores or offers?"
                    suggestions = ["Show me stores", "Current offers", "Store directory"]
            
            # Greeting
            elif any(word in message_lower for word in ['hi', 'hello', 'hey', 'greetings']):
                response = "Hello! Welcome to MallBuddy! 👋 I'm here to help you find stores, discover offers, and learn about events. What can I help you with today?"
                suggestions = ["Find a store", "Show me offers", "Upcoming events"]
            
            # Thanks
            elif any(word in message_lower for word in ['thank', 'thanks', 'appreciate']):
                response = "You're welcome! Happy to help! Is there anything else you'd like to know about our mall?"
                suggestions = ["Find another store", "Show me offers", "Upcoming events"]
            
            # Default response
            else:
                response = f"I'm MallBuddy, your shopping assistant! We have {len(stores)} stores, {len(offers)} offers, and {len(events)} events. "
                response += "I can help you find stores, discover deals, or learn about upcoming events. What would you like to know?"
                suggestions = ["Find a store", "Show me offers", "Upcoming events"]
            
            # Add to history
            self.add_to_history(session_id, "user", user_message)
            self.add_to_history(session_id, "assistant", response)
            
            return {"response": response, "suggestions": suggestions}
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return self._fallback_response(user_message)
    
    def _fallback_response(self, user_message: str) -> Dict:
        """Fallback response"""
        return {
            "response": "Hello! I'm MallBuddy. I can help you find stores, discover offers, and learn about events. What would you like to know?",
            "suggestions": ["Find a store", "Show me offers", "Upcoming events"]
        }
    
    def clear_history(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]


_chatbot = None

def get_conversational_chatbot():
    """Get or create chatbot instance"""
    global _chatbot
    if _chatbot is None:
        _chatbot = ConversationalChatbot()
    return _chatbot

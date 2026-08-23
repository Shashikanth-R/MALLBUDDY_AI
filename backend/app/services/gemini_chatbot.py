"""
Enhanced Gemini-powered Chatbot Service for MallBuddy
Provides intelligent, context-aware responses using Google Gemini AI
"""
import os
import json
from typing import Dict, List, Optional
from google import genai
from google.genai import types

class GeminiChatbotService:
    """Advanced chatbot service using Google Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini chatbot service"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.client = None
        
        if not self.api_key:
            print("⚠️ WARNING: GEMINI_API_KEY not found. Chatbot will run in fallback mode.")
            # Do not raise error to prevent app crash
        else:
            try:
                # Configure Gemini client with new SDK
                self.client = genai.Client(api_key=self.api_key)
                print("✅ Gemini Chatbot Service initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini client: {e}")
        
        # Model name
        self.model_name = 'models/gemini-3.6-flash'
        
        # Conversation history storage
        self.conversations = {}
    
    def _build_system_context(self, db_context: Dict) -> str:
        """Build comprehensive system context from database"""
        stores = db_context.get('stores', [])
        offers = db_context.get('offers', [])
        events = db_context.get('events', [])
        
        context = """You are MallBuddy, a friendly and intelligent AI assistant for Elements Mall in Bangalore.

Your personality:
- Warm, helpful, and conversational
- Use emojis occasionally to be engaging (but not excessively)
- Keep responses concise but informative
- Always be positive and solution-oriented

Your capabilities:
- Help visitors find stores and their locations
- Share information about current offers and deals
- Inform about upcoming events
- Provide navigation assistance
- Answer general mall-related questions

CRITICAL FORMATTING RULES (YOU MUST FOLLOW THESE):
1. NEVER use asterisks (*) or markdown formatting
2. Use the bullet point character (•) for list items
3. Put each bullet point item on its OWN LINE
4. Add a BLANK LINE between each bullet point for readability
5. Use CAPITAL LETTERS for store names and emphasis
6. Use emojis at the START of each bullet point
7. Include location info (Floor, Unit) on the SAME line after a dash

EXACT FORMAT TO USE FOR OFFERS:
Hey there! 👋 Here are today's exciting offers:

• 🛍️ ZARA - 30% off Winter Collection - Floor 1, Unit 105

• 👟 NIKE - Buy 2 Get 1 Free - Floor 2, Unit 210

• 🎬 PVR CINEMAS - 20% off Movie Tickets - Floor 4, Unit 401

Let me know if you need directions to any store!

EXACT FORMAT TO USE FOR STORE LOCATIONS:
Here's where you can find that store:

• 📍 ADIDAS - Floor 2, Unit 205 (Sports section)

Need directions? Just ask!

"""
        
        # Add stores information
        if stores:
            context += "\nAvailable Stores:\n"
            for store in stores[:15]:  # Limit to avoid token overflow
                context += f"- {store.get('name', 'Unknown')}: Floor {store.get('floor', 'N/A')}, Unit {store.get('unit', 'N/A')}"
                if store.get('category_name'):
                    context += f" ({store['category_name']})"
                context += "\n"
        
        # Add offers information
        if offers:
            context += "\nCurrent Offers:\n"
            for offer in offers[:10]:
                context += f"- {offer.get('title', 'Special Offer')}"
                if offer.get('store_name'):
                    context += f" at {offer['store_name']}"
                context += "\n"
        
        # Add events information
        if events:
            context += "\nUpcoming Events:\n"
            for event in events[:5]:
                context += f"- {event.get('name', 'Event')}: {event.get('description', '')}\n"
        
        context += """
Important Guidelines:
- When asked about store locations, provide floor and unit numbers
- If you don't have specific information, politely say so and offer alternatives
- Keep responses under 150 words unless detailed explanation is needed
- Suggest related information when relevant
- Be conversational and natural in your responses
- REMEMBER: No asterisks or markdown formatting in responses!
"""
        
        return context
    
    def _get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
    
    def _add_to_history(self, session_id: str, role: str, content: str):
        """Add message to conversation history"""
        history = self._get_conversation_history(session_id)
        history.append({"role": role, "content": content})
        
        # Keep only last 10 messages to manage context size
        if len(history) > 10:
            self.conversations[session_id] = history[-10:]
    
    def _generate_suggestions(self, user_message: str, response: str) -> List[str]:
        """Generate contextual follow-up suggestions"""
        message_lower = user_message.lower()
        
        # Store location queries
        if any(word in message_lower for word in ['where', 'location', 'find']):
            return [
                "What are their timings?",
                "Show me current offers",
                "How do I get there?"
            ]
        
        # Offers queries
        elif any(word in message_lower for word in ['offer', 'deal', 'discount']):
            return [
                "Where is this store?",
                "Show me more offers",
                "What events are happening?"
            ]
        
        # Events queries
        elif any(word in message_lower for word in ['event', 'happening', 'activity']):
            return [
                "Tell me more",
                "Show me stores",
                "Current offers"
            ]
        
        # Default suggestions
        else:
            return [
                "Find a store",
                "Show me offers",
                "Upcoming events"
            ]
    
    def generate_response(
        self, 
        user_message: str, 
        session_id: str, 
        db_context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate intelligent response using Gemini AI
        
        Args:
            user_message: User's input message
            session_id: Unique session identifier
            db_context: Database context with stores, offers, events
        
        Returns:
            Dict with response, suggestions, and metadata
        """
        try:
            db_context = db_context or {}
            
            # Build system context
            system_context = self._build_system_context(db_context)
            
            # Get conversation history
            history = self._get_conversation_history(session_id)
            
            # Build complete prompt
            prompt = f"{system_context}\n\n"
            
            # Add conversation history
            if history:
                prompt += "**Conversation History:**\n"
                for msg in history[-4:]:  # Last 4 messages for context
                    role_label = "User" if msg['role'] == 'user' else "MallBuddy"
                    prompt += f"{role_label}: {msg['content']}\n"
                prompt += "\n"
            
            # Add current user message
            prompt += f"**Current User Message:**\n{user_message}\n\n"
            prompt += "**Your Response (as MallBuddy):**"
            
            # Check if client is initialized
            if not self.client:
                print("⚠️ Gemini client not initialized, using fallback")
                return self._fallback_response(user_message)

            # Generate response using Gemini
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            bot_response = response.text.strip()
            
            # Post-process: Ensure bullet points are on new lines
            # Add newline before each bullet point (•) if not already there
            import re
            bot_response = re.sub(r'(?<!\n)•', '\n\n•', bot_response)
            # Also handle emoji bullet patterns like "🛍️ " that start offers
            bot_response = re.sub(r'(?<!\n)(• [🛍️👟🎬📍🔥🎉💰🏪])', r'\n\n\1', bot_response)
            # Clean up any triple+ newlines to double
            bot_response = re.sub(r'\n{3,}', '\n\n', bot_response)
            # Ensure first line doesn't start with newlines
            bot_response = bot_response.strip()
            
            # Add to conversation history
            self._add_to_history(session_id, 'user', user_message)
            self._add_to_history(session_id, 'assistant', bot_response)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(user_message, bot_response)
            
            return {
                'response': bot_response,
                'suggestions': suggestions,
                'intent': 'gemini_powered',
                'success': True
            }
        
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            return self._fallback_response(user_message)
    
    def _fallback_response(self, user_message: str) -> Dict:
        """Fallback response when Gemini API fails"""
        return {
            'response': "I'm having a bit of trouble right now, but I'm here to help! 😊 Could you please rephrase your question?",
            'suggestions': [
                "Find a store",
                "Show me offers",
                "Upcoming events"
            ],
            'intent': 'fallback',
            'success': False
        }
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
    
    def get_conversation_summary(self, session_id: str) -> Dict:
        """Get summary of conversation for a session"""
        history = self._get_conversation_history(session_id)
        return {
            'session_id': session_id,
            'message_count': len(history),
            'messages': history
        }


# Singleton instance
_gemini_chatbot = None

def get_gemini_chatbot() -> GeminiChatbotService:
    """Get or create Gemini chatbot instance"""
    global _gemini_chatbot
    if _gemini_chatbot is None:
        _gemini_chatbot = GeminiChatbotService()
    return _gemini_chatbot

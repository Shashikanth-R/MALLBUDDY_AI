"""
Enhanced Chatbot Service with LangChain RAG
Provides human-like, context-aware conversations with memory
"""
import os
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage
from app.services.vector_store_service import get_vector_store


class EnhancedChatbotService:
    """LangChain-based chatbot with RAG and conversation memory"""
    
    def __init__(self):
        """Initialize chatbot with LLM and vector store"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.llm = None
        self.vector_store = None
        self.memory_store = {}  # Session-based memory storage
        
        if self.api_key:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    openai_api_key=self.api_key
                )
                self.vector_store = get_vector_store()
                print("✅ Enhanced chatbot initialized with LangChain")
            except Exception as e:
                print(f"⚠️  Error initializing LangChain chatbot: {e}")
        else:
            print("⚠️  No OpenAI API key found")
    
    def get_or_create_memory(self, session_id: str) -> ConversationBufferMemory:
        """Get or create conversation memory for session"""
        if session_id not in self.memory_store:
            self.memory_store[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
        return self.memory_store[session_id]
    
    def create_rag_chain(self, session_id: str):
        """Create RAG chain with conversation memory"""
        if not self.llm or not self.vector_store or not self.vector_store.vectorstore:
            return None
        
        memory = self.get_or_create_memory(session_id)
        
        # Custom prompt for mall assistant
        prompt_template = """You are MallBuddy, a friendly and helpful shopping mall assistant. 
You help visitors find stores, discover offers, get directions, and learn about events.

Use the following context to answer the question. If you don't know the answer based on the context, 
say so politely and offer to help with something else.

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Helpful Answer (be conversational and friendly):"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "chat_history", "question"]
        )
        
        # Create conversational retrieval chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            combine_docs_chain_kwargs={"prompt": PROMPT},
            return_source_documents=True,
            verbose=False
        )
        
        return chain
    
    def generate_response(self, user_message: str, session_id: str, context: Dict = None) -> Dict:
        """Generate response using RAG chain"""
        
        # Try LangChain RAG first
        if self.llm and self.vector_store and self.vector_store.vectorstore:
            try:
                chain = self.create_rag_chain(session_id)
                if chain:
                    result = chain({"question": user_message})
                    
                    # Extract suggestions from source documents
                    suggestions = self._generate_suggestions(result.get('source_documents', []))
                    
                    return {
                        'response': result['answer'],
                        'suggestions': suggestions,
                        'sources': [doc.metadata for doc in result.get('source_documents', [])]
                    }
            except Exception as e:
                print(f"⚠️  RAG chain error: {e}")
        
        # Fallback to simple response
        return self._fallback_response(user_message, context)
    
    def _generate_suggestions(self, source_docs: List) -> List[str]:
        """Generate follow-up suggestions based on retrieved documents"""
        suggestions = []
        
        if not source_docs:
            return ["What stores are you looking for?", "Tell me about current offers"]
        
        # Analyze source types
        doc_types = [doc.metadata.get('type') for doc in source_docs]
        
        if 'store' in doc_types:
            suggestions.append("Tell me more about this store")
            suggestions.append("What offers does this store have?")
        
        if 'offer' in doc_types:
            suggestions.append("Show me more offers")
            suggestions.append("Where is this store located?")
        
        if 'event' in doc_types:
            suggestions.append("Tell me about upcoming events")
        
        # Limit to 3 suggestions
        return suggestions[:3]
    
    def _fallback_response(self, user_message: str, context: Dict = None) -> Dict:
        """Fallback response when RAG is not available"""
        message_lower = user_message.lower()
        
        # Simple keyword matching
        if any(word in message_lower for word in ['where', 'location', 'find']):
            return {
                'response': "I can help you find stores! Please tell me which store you're looking for, or browse by category.",
                'suggestions': ["Show me fashion stores", "Where is the food court?", "List all stores"]
            }
        elif any(word in message_lower for word in ['offer', 'deal', 'discount', 'sale']):
            return {
                'response': "Let me show you our current offers! We have great deals across various stores.",
                'suggestions': ["Show all offers", "Fashion deals", "Food offers"]
            }
        elif any(word in message_lower for word in ['event', 'happening', 'activity']):
            return {
                'response': "Check out our upcoming events! We have exciting activities planned.",
                'suggestions': ["Show upcoming events", "What's happening this weekend?"]
            }
        else:
            return {
                'response': "Hello! I'm MallBuddy, your shopping assistant. I can help you find stores, discover offers, and learn about events. What would you like to know?",
                'suggestions': ["Find a store", "Show me offers", "Upcoming events"]
            }
    
    def clear_memory(self, session_id: str):
        """Clear conversation memory for a session"""
        if session_id in self.memory_store:
            del self.memory_store[session_id]


# Global instance
_chatbot_service = None

def get_chatbot_service() -> EnhancedChatbotService:
    """Get or create chatbot service instance"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = EnhancedChatbotService()
    return _chatbot_service

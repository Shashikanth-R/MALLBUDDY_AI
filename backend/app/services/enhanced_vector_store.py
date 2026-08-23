"""
Enhanced Vector Store Service using Google Gemini Embeddings
Provides semantic search and RAG capabilities for MallBuddy
"""
import os
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai


class EnhancedVectorStore:
    """Vector store service using Gemini embeddings for semantic search"""
    
    def __init__(self):
        """Initialize vector store with Gemini"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            print("⚠️ WARNING: GEMINI_API_KEY not found. Vector store will be disabled.")
            self.model = None
            self.documents = []
            return
            
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            print("✅ Enhanced Vector Store initialized with Gemini")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini Vector Store: {e}")
            self.model = None
        
        # In-memory storage for embeddings (for demo)
        # In production, use ChromaDB or similar
        self.documents = []
        self.embeddings_cache = {}
    
    def add_stores(self, stores: List[Dict]):
        """Add stores to vector store"""
        for store in stores:
            doc = {
                'id': f"store_{store['id']}",
                'type': 'store',
                'content': f"{store['name']} - {store.get('category_name', '')} store on Floor {store['floor']}, Unit {store['unit']}. {store.get('description', '')}",
                'metadata': {
                    'store_id': store['id'],
                    'name': store['name'],
                    'category': store.get('category_name', ''),
                    'floor': store['floor'],
                    'unit': store['unit'],
                    'status': store.get('status', 'open')
                }
            }
            self.documents.append(doc)
        print(f"✅ Added {len(stores)} stores to vector store")
    
    def add_offers(self, offers: List[Dict]):
        """Add offers to vector store"""
        for offer in offers:
            doc = {
                'id': f"offer_{offer['id']}",
                'type': 'offer',
                'content': f"{offer['title']} at {offer.get('store_name', 'store')}. {offer.get('description', '')}. Valid until {offer.get('end_date', 'TBD')}.",
                'metadata': {
                    'offer_id': offer['id'],
                    'title': offer['title'],
                    'store_name': offer.get('store_name', ''),
                    'end_date': offer.get('end_date', '')
                }
            }
            self.documents.append(doc)
        print(f"✅ Added {len(offers)} offers to vector store")
    
    def add_events(self, events: List[Dict]):
        """Add events to vector store"""
        for event in events:
            doc = {
                'id': f"event_{event['id']}",
                'type': 'event',
                'content': f"{event['name']} - {event.get('description', '')}. Date: {event.get('event_date', 'TBD')}. Location: {event.get('location', 'TBD')}.",
                'metadata': {
                    'event_id': event['id'],
                    'name': event['name'],
                    'event_date': event.get('event_date', ''),
                    'location': event.get('location', '')
                }
            }
            self.documents.append(doc)
        print(f"✅ Added {len(events)} events to vector store")
    
    def semantic_search(self, query: str, k: int = 5, doc_type: Optional[str] = None) -> List[Dict]:
        """
        Perform semantic search using simple text matching
        In production, this would use actual embeddings
        """
        results = []
        query_lower = query.lower()
        
        # Filter by type if specified
        docs_to_search = self.documents
        if doc_type:
            docs_to_search = [d for d in self.documents if d['type'] == doc_type]
        
        # Simple keyword matching (in production, use embeddings)
        for doc in docs_to_search:
            content_lower = doc['content'].lower()
            
            # Calculate simple relevance score
            score = 0
            for word in query_lower.split():
                if word in content_lower:
                    score += 1
            
            if score > 0:
                results.append({
                    'document': doc,
                    'score': score
                })
        
        # Sort by score and return top k
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['document'] for r in results[:k]]
    
    def get_relevant_context(self, query: str, k: int = 3) -> str:
        """Get relevant context for RAG"""
        results = self.semantic_search(query, k=k)
        
        if not results:
            return "No relevant information found in the mall database."
        
        context_parts = []
        for i, doc in enumerate(results, 1):
            context_parts.append(f"[{i}] {doc['content']}")
        
        return "\n\n".join(context_parts)
    
    def get_stats(self) -> Dict:
        """Get vector store statistics"""
        return {
            'total_documents': len(self.documents),
            'stores': len([d for d in self.documents if d['type'] == 'store']),
            'offers': len([d for d in self.documents if d['type'] == 'offer']),
            'events': len([d for d in self.documents if d['type'] == 'event'])
        }


# Global instance
_vector_store = None

def get_enhanced_vector_store() -> EnhancedVectorStore:
    """Get or create enhanced vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = EnhancedVectorStore()
    return _vector_store


def initialize_vector_store_with_data(stores, offers, events):
    """Initialize vector store with mall data"""
    vs = get_enhanced_vector_store()
    vs.add_stores(stores)
    vs.add_offers(offers)
    vs.add_events(events)
    return vs

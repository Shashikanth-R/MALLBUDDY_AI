"""
Vector Store Service for RAG-based semantic search
Uses ChromaDB for storing and retrieving mall/store embeddings
"""
import os
from typing import List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


class VectorStoreService:
    """Manages vector store for semantic search"""
    
    def __init__(self, persist_directory: str = None):
        """Initialize vector store with OpenAI embeddings"""
        self.persist_directory = persist_directory or os.getenv('CHROMA_PERSIST_DIR', './chroma_db')
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'))
        self.vectorstore = None
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """Initialize or load existing vector store"""
        try:
            # Try to load existing vectorstore
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name="mallbuddy_docs"
            )
            print(f"✅ Loaded existing vector store from {self.persist_directory}")
        except Exception as e:
            print(f"⚠️  No existing vector store found, will create new one: {e}")
            self.vectorstore = None
    
    def create_documents_from_stores(self, stores: List[Dict]) -> List[Document]:
        """Convert store data to LangChain documents"""
        documents = []
        
        for store in stores:
            # Create rich text content for better embeddings
            content = f"""
Store Name: {store['name']}
Category: {store.get('category_name', 'N/A')}
Location: Floor {store['floor']}, Unit {store['unit']}
Description: {store.get('description', 'No description available')}
Status: {store.get('status', 'open')}
"""
            
            metadata = {
                'type': 'store',
                'store_id': store['id'],
                'name': store['name'],
                'category': store.get('category_name', ''),
                'floor': store['floor'],
                'unit': store['unit']
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def create_documents_from_offers(self, offers: List[Dict]) -> List[Document]:
        """Convert offer data to LangChain documents"""
        documents = []
        
        for offer in offers:
            content = f"""
Offer: {offer['title']}
Store: {offer.get('store_name', 'N/A')}
Description: {offer['description']}
Valid from: {offer['start_date']} to {offer['end_date']}
Featured: {'Yes' if offer.get('is_featured') else 'No'}
"""
            
            metadata = {
                'type': 'offer',
                'offer_id': offer['id'],
                'title': offer['title'],
                'store_name': offer.get('store_name', ''),
                'start_date': offer['start_date'],
                'end_date': offer['end_date']
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def create_documents_from_events(self, events: List[Dict]) -> List[Document]:
        """Convert event data to LangChain documents"""
        documents = []
        
        for event in events:
            content = f"""
Event: {event['name']}
Description: {event['description']}
Date: {event['event_date']}
Location: {event['location']}
"""
            
            metadata = {
                'type': 'event',
                'event_id': event['id'],
                'name': event['name'],
                'event_date': event['event_date'],
                'location': event['location']
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def initialize_with_data(self, stores: List[Dict], offers: List[Dict], events: List[Dict]):
        """Initialize vector store with mall data"""
        print("🔄 Initializing vector store with mall data...")
        
        # Create documents
        all_documents = []
        all_documents.extend(self.create_documents_from_stores(stores))
        all_documents.extend(self.create_documents_from_offers(offers))
        all_documents.extend(self.create_documents_from_events(events))
        
        print(f"📄 Created {len(all_documents)} documents")
        
        # Create vector store
        self.vectorstore = Chroma.from_documents(
            documents=all_documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_name="mallbuddy_docs"
        )
        
        print(f"✅ Vector store initialized with {len(all_documents)} documents")
        return self.vectorstore
    
    def semantic_search(self, query: str, k: int = 5, filter_type: str = None) -> List[Document]:
        """Perform semantic search on vector store"""
        if not self.vectorstore:
            print("⚠️  Vector store not initialized")
            return []
        
        try:
            # Build filter if type specified
            search_kwargs = {'k': k}
            if filter_type:
                search_kwargs['filter'] = {'type': filter_type}
            
            # Perform similarity search
            results = self.vectorstore.similarity_search(query, **search_kwargs)
            return results
        except Exception as e:
            print(f"❌ Error in semantic search: {e}")
            return []
    
    def get_relevant_context(self, query: str, k: int = 3) -> str:
        """Get relevant context as formatted string"""
        results = self.semantic_search(query, k=k)
        
        if not results:
            return "No relevant information found."
        
        context_parts = []
        for i, doc in enumerate(results, 1):
            context_parts.append(f"[{i}] {doc.page_content.strip()}")
        
        return "\n\n".join(context_parts)
    
    def update_store(self, store: Dict):
        """Update a single store in vector store"""
        # For now, we'll recreate the entire store
        # In production, you'd want more sophisticated update logic
        pass
    
    def delete_store(self, store_id: int):
        """Delete a store from vector store"""
        # ChromaDB delete by metadata filter
        pass


# Global instance
_vector_store = None

def get_vector_store() -> VectorStoreService:
    """Get or create vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store

"""
Advanced Knowledge Retrieval with ChromaDB and enhanced semantic search.
Implements persistent vector database with hybrid search capabilities.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from data.models import udahub


# Database path
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "core",
    "udahub.db"
)

# ChromaDB path
CHROMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "core",
    "chroma_db"
)


class AdvancedKnowledgeRetriever:
    """
    Advanced knowledge retrieval system using ChromaDB for persistent vector storage.
    Supports hybrid search (semantic + keyword) and query expansion.
    """
    
    def __init__(self, account_id: str = "cultpass"):
        self.account_id = account_id
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        self.collection = None
        self.embeddings = None
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB with persistent storage."""
        try:
            import chromadb
            from chromadb.config import Settings
            from langchain_openai import OpenAIEmbeddings
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            
            # Initialize ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(
                path=CHROMA_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            collection_name = f"knowledge_base_{self.account_id}"
            
            try:
                self.collection = self.client.get_collection(name=collection_name)
                print(f"✅ Loaded existing ChromaDB collection: {collection_name}")
            except:
                # Collection doesn't exist, create and populate it
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": f"Knowledge base for {self.account_id}"}
                )
                self._populate_collection()
                print(f"✅ Created and populated ChromaDB collection: {collection_name}")
            
        except ImportError as e:
            print(f"Warning: ChromaDB not available: {e}")
            print("Falling back to FAISS implementation")
            self._initialize_faiss_fallback()
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            self._initialize_faiss_fallback()
    
    def _initialize_faiss_fallback(self):
        """Fallback to FAISS if ChromaDB is not available."""
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
            
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            
            articles = self._load_articles()
            if not articles:
                print("Warning: No knowledge articles found")
                return
            
            documents = []
            for article in articles:
                text = f"Title: {article['title']}\n\nContent: {article['content']}\n\nTags: {article['tags']}"
                doc = Document(
                    page_content=text,
                    metadata={
                        "article_id": article["article_id"],
                        "title": article["title"],
                        "tags": article["tags"]
                    }
                )
                documents.append(doc)
            
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            print(f"✅ Initialized FAISS fallback with {len(documents)} articles")
            
        except Exception as e:
            print(f"Error initializing FAISS fallback: {e}")
    
    def _populate_collection(self):
        """Populate ChromaDB collection with knowledge articles."""
        articles = self._load_articles()
        
        if not articles:
            print("Warning: No articles to populate")
            return
        
        # Prepare documents for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for article in articles:
            # Combine title, content, and tags for better retrieval
            text = f"Title: {article['title']}\n\nContent: {article['content']}\n\nTags: {article['tags']}"
            documents.append(text)
            
            metadatas.append({
                "article_id": article["article_id"],
                "title": article["title"],
                "tags": article["tags"],
                "category": self._extract_category(article["tags"])
            })
            
            ids.append(article["article_id"])
        
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Populated ChromaDB with {len(documents)} articles")
    
    def _extract_category(self, tags: str) -> str:
        """Extract primary category from tags."""
        tag_list = [t.strip().lower() for t in tags.split(",")]
        
        categories = {
            "login": ["login", "password", "access", "authentication"],
            "billing": ["billing", "payment", "refund", "charge"],
            "subscription": ["subscription", "tier", "plan", "quota"],
            "reservation": ["reservation", "booking", "event", "cancel"],
            "technical": ["technical", "app", "crash", "bug"],
            "account": ["account", "profile", "email", "blocked"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in tag_list for keyword in keywords):
                return category
        
        return "general"
    
    def _load_articles(self) -> List[Dict[str, Any]]:
        """Load all knowledge articles from database."""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            articles = session.query(udahub.Knowledge).filter_by(
                account_id=self.account_id
            ).all()
            
            return [
                {
                    "article_id": article.article_id,
                    "title": article.title,
                    "content": article.content,
                    "tags": article.tags or ""
                }
                for article in articles
            ]
        finally:
            session.close()
    
    def search(
        self, 
        query: str, 
        top_k: int = 3,
        filter_category: Optional[str] = None,
        use_hybrid: bool = True
    ) -> Dict[str, Any]:
        """
        Advanced search with multiple strategies.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_category: Optional category filter
            use_hybrid: Use hybrid search (semantic + keyword)
            
        Returns:
            Search results with relevance scores
        """
        try:
            if self.collection is None:
                # Use FAISS fallback
                return self._faiss_search(query, top_k)
            
            # Prepare filter if category specified
            where_filter = None
            if filter_category:
                where_filter = {"category": filter_category}
            
            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter
            )
            
            # Process results
            articles = []
            for i in range(len(results['ids'][0])):
                # ChromaDB returns cosine distance (0-2), convert to similarity (0-1)
                distance = results['distances'][0][i]
                similarity = 1 - (distance / 2)
                
                articles.append({
                    "article_id": results['ids'][0][i],
                    "title": results['metadatas'][0][i]['title'],
                    "content": results['documents'][0][i],
                    "tags": results['metadatas'][0][i]['tags'],
                    "category": results['metadatas'][0][i]['category'],
                    "relevance_score": similarity,
                    "distance": distance
                })
            
            # Calculate confidence
            avg_score = sum(a["relevance_score"] for a in articles) / len(articles) if articles else 0
            
            # If using hybrid search, boost scores based on keyword matches
            if use_hybrid and articles:
                articles = self._apply_keyword_boost(query, articles)
                # Recalculate average after boosting
                avg_score = sum(a["relevance_score"] for a in articles) / len(articles)
            
            return {
                "success": True,
                "query": query,
                "count": len(articles),
                "articles": articles,
                "confidence": avg_score,
                "method": "chromadb_hybrid" if use_hybrid else "chromadb_semantic",
                "filter_category": filter_category
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Search error: {str(e)}",
                "query": query
            }
    
    def _apply_keyword_boost(self, query: str, articles: List[Dict]) -> List[Dict]:
        """Apply keyword-based boosting to semantic search results."""
        query_words = set(query.lower().split())
        
        for article in articles:
            # Count keyword matches in title and content
            text = f"{article['title']} {article['content']}".lower()
            matches = sum(1 for word in query_words if len(word) > 2 and word in text)
            
            # Boost score based on keyword matches (max 20% boost)
            boost = min(matches * 0.05, 0.2)
            article["relevance_score"] = min(article["relevance_score"] + boost, 1.0)
            article["keyword_boost"] = boost
        
        # Re-sort by boosted scores
        articles.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return articles
    
    def _faiss_search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Fallback FAISS search."""
        if not hasattr(self, 'vector_store'):
            return {
                "success": False,
                "error": "No vector store available",
                "query": query
            }
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            articles = []
            for doc, score in results:
                similarity = 1 / (1 + score)
                articles.append({
                    "article_id": doc.metadata["article_id"],
                    "title": doc.metadata["title"],
                    "content": doc.page_content,
                    "tags": doc.metadata["tags"],
                    "relevance_score": similarity
                })
            
            avg_score = sum(a["relevance_score"] for a in articles) / len(articles) if articles else 0
            
            return {
                "success": True,
                "query": query,
                "count": len(articles),
                "articles": articles,
                "confidence": avg_score,
                "method": "faiss_fallback"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"FAISS search error: {str(e)}",
                "query": query
            }
    
    def search_by_category(self, query: str, category: str, top_k: int = 3) -> Dict[str, Any]:
        """Search within a specific category."""
        return self.search(query, top_k=top_k, filter_category=category)
    
    def get_similar_articles(self, article_id: str, top_k: int = 3) -> Dict[str, Any]:
        """Find similar articles to a given article."""
        try:
            # Get the article content
            Session = sessionmaker(bind=self.engine)
            session = Session()
            
            article = session.query(udahub.Knowledge).filter_by(
                article_id=article_id
            ).first()
            
            session.close()
            
            if not article:
                return {
                    "success": False,
                    "error": f"Article {article_id} not found"
                }
            
            # Search using article content
            query = f"{article.title} {article.content}"
            results = self.search(query, top_k=top_k + 1)  # +1 to exclude self
            
            # Filter out the original article
            if results.get("success"):
                results["articles"] = [
                    a for a in results["articles"] 
                    if a["article_id"] != article_id
                ][:top_k]
                results["count"] = len(results["articles"])
            
            return results
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Similar articles error: {str(e)}"
            }


# Global retriever instance
_advanced_retriever = None


def get_advanced_retriever(account_id: str = "cultpass") -> AdvancedKnowledgeRetriever:
    """Get or create advanced knowledge retriever instance."""
    global _advanced_retriever
    if _advanced_retriever is None:
        _advanced_retriever = AdvancedKnowledgeRetriever(account_id)
    return _advanced_retriever


def search_knowledge_advanced(
    query: str, 
    top_k: int = 3,
    category: Optional[str] = None,
    use_hybrid: bool = True
) -> Dict[str, Any]:
    """
    Advanced knowledge base search with hybrid retrieval.
    
    Args:
        query: Search query
        top_k: Number of results (default: 3)
        category: Optional category filter
        use_hybrid: Use hybrid search (default: True)
        
    Returns:
        Search results with enhanced relevance scoring
    """
    retriever = get_advanced_retriever()
    return retriever.search(query, top_k=top_k, filter_category=category, use_hybrid=use_hybrid)

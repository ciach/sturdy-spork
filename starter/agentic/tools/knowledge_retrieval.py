"""
Knowledge retrieval tool using RAG (Retrieval-Augmented Generation).
Implements semantic search over the knowledge base articles.
"""

import os
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from data.models import udahub


# Database path
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "core",
    "udahub.db"
)


class KnowledgeRetriever:
    """
    Knowledge retrieval system using embeddings and semantic search.
    Uses lazy loading to avoid slow initialization on import.
    """
    
    def __init__(self, account_id: str = "cultpass", lazy_load: bool = True):
        self.account_id = account_id
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        self.embeddings = None
        self.vector_store = None
        self._initialized = False
        
        # Only initialize immediately if lazy_load is False
        if not lazy_load:
            self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize embeddings model and vector store."""
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            
            # Check if cached vector store exists
            cache_path = os.path.join(
                os.path.dirname(DB_PATH),
                f"faiss_cache_{self.account_id}"
            )
            
            if os.path.exists(cache_path):
                try:
                    # Load from cache
                    self.vector_store = FAISS.load_local(
                        cache_path, 
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    print(f"✅ Loaded cached knowledge base from {cache_path}")
                    return
                except Exception as e:
                    print(f"Warning: Could not load cache: {e}, rebuilding...")
            
            # Load knowledge articles from database
            articles = self._load_articles()
            
            if not articles:
                print("Warning: No knowledge articles found in database")
                return
            
            # Create documents for vector store
            documents = []
            for article in articles:
                # Combine title and content for better retrieval
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
            
            # Create FAISS vector store
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            
            # Save to cache
            try:
                self.vector_store.save_local(cache_path)
                print(f"✅ Initialized and cached knowledge base with {len(documents)} articles")
            except Exception as e:
                print(f"✅ Initialized knowledge base with {len(documents)} articles (cache save failed: {e})")
            
        except ImportError as e:
            print(f"Warning: Could not initialize embeddings: {e}")
            print("Knowledge retrieval will use fallback keyword search")
        except Exception as e:
            print(f"Error initializing embeddings: {e}")
    
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
    
    def search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Search knowledge base for relevant articles.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            # Lazy initialize embeddings on first search
            if not self._initialized:
                self._initialize_embeddings()
                self._initialized = True
            
            if self.vector_store is None:
                # Fallback to keyword search
                return self._keyword_search(query, top_k)
            
            # Semantic search using vector store
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            articles = []
            for doc, score in results:
                # Convert distance to similarity score (lower distance = higher similarity)
                # FAISS returns L2 distance, convert to similarity score
                # Convert numpy.float32 to Python float for serialization
                similarity = float(1 / (1 + float(score)))
                
                articles.append({
                    "article_id": doc.metadata["article_id"],
                    "title": doc.metadata["title"],
                    "content": doc.page_content,
                    "tags": doc.metadata["tags"],
                    "relevance_score": similarity
                })
            
            # Calculate overall confidence
            avg_score = sum(a["relevance_score"] for a in articles) / len(articles) if articles else 0
            
            return {
                "success": True,
                "query": query,
                "count": len(articles),
                "articles": articles,
                "confidence": avg_score,
                "method": "semantic_search"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Search error: {str(e)}",
                "query": query
            }
    
    def _keyword_search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Fallback keyword-based search when embeddings are not available.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            Dictionary containing search results
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            # Simple keyword matching
            query_lower = query.lower()
            articles = session.query(udahub.Knowledge).filter_by(
                account_id=self.account_id
            ).all()
            
            # Score articles based on keyword matches
            scored_articles = []
            for article in articles:
                score = 0
                text = f"{article.title} {article.content} {article.tags}".lower()
                
                # Count keyword matches
                for word in query_lower.split():
                    if len(word) > 2:  # Ignore very short words
                        score += text.count(word)
                
                if score > 0:
                    scored_articles.append({
                        "article_id": article.article_id,
                        "title": article.title,
                        "content": f"Title: {article.title}\n\nContent: {article.content}\n\nTags: {article.tags}",
                        "tags": article.tags or "",
                        "relevance_score": min(score / 10, 1.0),  # Normalize score
                        "match_count": score
                    })
            
            # Sort by score and take top_k
            scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
            top_articles = scored_articles[:top_k]
            
            avg_score = sum(a["relevance_score"] for a in top_articles) / len(top_articles) if top_articles else 0
            
            return {
                "success": True,
                "query": query,
                "count": len(top_articles),
                "articles": top_articles,
                "confidence": avg_score,
                "method": "keyword_search"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Search error: {str(e)}",
                "query": query
            }
        finally:
            session.close()


# Global retriever instance
_retriever = None


def get_retriever(account_id: str = "cultpass") -> KnowledgeRetriever:
    """Get or create knowledge retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever(account_id)
    return _retriever


def search_knowledge_base(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Search the knowledge base for relevant articles.
    
    Args:
        query: Search query
        top_k: Number of top results to return (default: 3)
        
    Returns:
        Dictionary containing search results
    """
    retriever = get_retriever()
    return retriever.search(query, top_k)


# Tool description for LLM
KNOWLEDGE_TOOL_DESCRIPTION = {
    "name": "search_knowledge_base",
    "description": "Search the knowledge base for relevant support articles using semantic search. Returns top matching articles with relevance scores.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant knowledge articles"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top results to return (default: 3)",
                "default": 3
            }
        },
        "required": ["query"]
    }
}

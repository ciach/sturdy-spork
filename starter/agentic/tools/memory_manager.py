"""
Memory Manager - Persistent storage and retrieval of customer interaction history.
Stores conversations in the database for cross-session personalization.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

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


class MemoryManager:
    """
    Manages persistent storage and retrieval of customer interaction history.
    Stores messages in the database for cross-session memory and personalization.
    """
    
    def __init__(self, account_id: str = "cultpass"):
        self.account_id = account_id
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        self.Session = sessionmaker(bind=self.engine)
    
    def save_interaction(
        self,
        ticket_id: str,
        customer_id: Optional[str],
        messages: List[BaseMessage],
        classification: Optional[Dict[str, Any]] = None,
        resolution_status: str = "open"
    ) -> str:
        """
        Save a complete interaction to the database.
        
        Args:
            ticket_id: Unique ticket identifier
            customer_id: Customer identifier (email, external ID, etc.)
            messages: List of conversation messages
            classification: Ticket classification data
            resolution_status: Status of the ticket (open, resolved, escalated)
            
        Returns:
            Ticket ID
        """
        session = self.Session()
        
        try:
            # Get or create user for this customer
            user_id = customer_id or f"guest_{ticket_id}"
            user = session.query(udahub.User).filter_by(
                account_id=self.account_id,
                external_user_id=user_id
            ).first()
            
            if not user:
                # Create new user
                user = udahub.User(
                    user_id=f"{self.account_id}_{user_id}",
                    account_id=self.account_id,
                    external_user_id=user_id,
                    user_name=customer_id or "Guest User",
                    created_at=datetime.utcnow()
                )
                session.add(user)
                session.flush()
            
            # Check if ticket exists
            ticket = session.query(udahub.Ticket).filter_by(
                ticket_id=ticket_id
            ).first()
            
            if not ticket:
                # Create new ticket
                ticket = udahub.Ticket(
                    ticket_id=ticket_id,
                    account_id=self.account_id,
                    user_id=user.user_id,
                    channel="web",
                    created_at=datetime.utcnow()
                )
                session.add(ticket)
                session.flush()
                
                # Create ticket metadata
                main_issue = "general"
                tags = ""
                
                # Add classification data if available
                if classification:
                    cat = classification.get("classification", {})
                    main_issue = cat.get("category", "general")
                    tags = cat.get("subject", "Customer inquiry")
                
                metadata = udahub.TicketMetadata(
                    ticket_id=ticket_id,
                    status=resolution_status,
                    main_issue_type=main_issue,
                    tags=tags
                )
                session.add(metadata)
            else:
                # Update existing ticket metadata
                metadata = ticket.ticket_metadata
                if metadata:
                    metadata.status = resolution_status
                    metadata.updated_at = datetime.utcnow()
            
            # Save messages
            for msg in messages:
                # Skip internal system messages
                if hasattr(msg, 'name') and msg.name in ['supervisor', 'classifier']:
                    continue
                
                # Determine role
                if isinstance(msg, HumanMessage):
                    role = udahub.RoleEnum.user
                elif isinstance(msg, AIMessage):
                    role = udahub.RoleEnum.ai
                else:
                    role = udahub.RoleEnum.system
                
                # Generate message ID
                import hashlib
                msg_hash = hashlib.md5(f"{ticket_id}_{msg.content}_{role.value}".encode()).hexdigest()[:16]
                message_id = f"msg_{msg_hash}"
                
                # Check if message already exists (avoid duplicates)
                existing = session.query(udahub.TicketMessage).filter_by(
                    message_id=message_id
                ).first()
                
                if not existing:
                    ticket_msg = udahub.TicketMessage(
                        message_id=message_id,
                        ticket_id=ticket_id,
                        role=role,
                        content=msg.content,
                        created_at=datetime.utcnow()
                    )
                    session.add(ticket_msg)
            
            session.commit()
            return ticket_id
            
        except Exception as e:
            session.rollback()
            print(f"Error saving interaction: {e}")
            raise
        finally:
            session.close()
    
    def get_customer_history(
        self,
        customer_id: str,
        limit: int = 5,
        include_messages: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve interaction history for a specific customer.
        
        Args:
            customer_id: Customer identifier (external_user_id)
            limit: Maximum number of tickets to retrieve
            include_messages: Whether to include message details
            
        Returns:
            List of ticket dictionaries with messages
        """
        session = self.Session()
        
        try:
            # Find user by external_user_id
            user = session.query(udahub.User).filter_by(
                account_id=self.account_id,
                external_user_id=customer_id
            ).first()
            
            if not user:
                return []
            
            # Get customer's tickets
            tickets = session.query(udahub.Ticket).filter_by(
                account_id=self.account_id,
                user_id=user.user_id
            ).order_by(desc(udahub.Ticket.created_at)).limit(limit).all()
            
            history = []
            for ticket in tickets:
                metadata = ticket.ticket_metadata
                ticket_data = {
                    "ticket_id": ticket.ticket_id,
                    "status": metadata.status if metadata else "unknown",
                    "category": metadata.main_issue_type if metadata else "general",
                    "priority": "medium",  # Not in schema, default value
                    "subject": metadata.tags if metadata else "No subject",
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    "resolved_at": None,  # Not in schema
                }
                
                if include_messages:
                    messages = session.query(udahub.TicketMessage).filter_by(
                        ticket_id=ticket.ticket_id
                    ).order_by(udahub.TicketMessage.created_at).all()
                    
                    ticket_data["messages"] = [
                        {
                            "sender_type": msg.role.value if msg.role else "unknown",
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None
                        }
                        for msg in messages
                    ]
                    
                    # Extract summary
                    ticket_data["message_count"] = len(messages)
                    if messages:
                        ticket_data["last_message"] = messages[-1].content[:100] if messages[-1].content else ""
                
                history.append(ticket_data)
            
            return history
            
        finally:
            session.close()
    
    def get_resolved_issues(
        self,
        customer_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve resolved issues for reference and learning.
        
        Args:
            customer_id: Optional filter by customer
            category: Optional filter by category
            limit: Maximum number of issues to retrieve
            
        Returns:
            List of resolved ticket summaries
        """
        session = self.Session()
        
        try:
            # Query tickets with resolved status in metadata
            query = session.query(udahub.Ticket).join(udahub.TicketMetadata).filter(
                udahub.Ticket.account_id == self.account_id,
                udahub.TicketMetadata.status == "resolved"
            )
            
            if customer_id:
                # Find user first
                user = session.query(udahub.User).filter_by(
                    account_id=self.account_id,
                    external_user_id=customer_id
                ).first()
                if user:
                    query = query.filter(udahub.Ticket.user_id == user.user_id)
            
            if category:
                query = query.filter(udahub.TicketMetadata.main_issue_type == category)
            
            tickets = query.order_by(desc(udahub.Ticket.created_at)).limit(limit).all()
            
            resolved = []
            for ticket in tickets:
                metadata = ticket.ticket_metadata
                # Get resolution message (last AI message)
                messages = session.query(udahub.TicketMessage).filter_by(
                    ticket_id=ticket.ticket_id,
                    role=udahub.RoleEnum.ai
                ).order_by(desc(udahub.TicketMessage.created_at)).first()
                
                resolved.append({
                    "ticket_id": ticket.ticket_id,
                    "customer_id": ticket.user.external_user_id if ticket.user else None,
                    "category": metadata.main_issue_type if metadata else None,
                    "subject": metadata.tags if metadata else None,
                    "resolution": messages.content if messages else None,
                    "resolved_at": metadata.updated_at.isoformat() if metadata and metadata.updated_at else None
                })
            
            return resolved
            
        finally:
            session.close()
    
    def get_customer_preferences(self, customer_id: str) -> Dict[str, Any]:
        """
        Extract customer preferences from interaction history.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Dictionary of inferred preferences
        """
        session = self.Session()
        
        try:
            # Find user first
            user = session.query(udahub.User).filter_by(
                account_id=self.account_id,
                external_user_id=customer_id
            ).first()
            
            if not user:
                return {
                    "is_returning_customer": False,
                    "total_interactions": 0
                }
            
            tickets = session.query(udahub.Ticket).filter_by(
                account_id=self.account_id,
                user_id=user.user_id
            ).all()
            
            if not tickets:
                return {
                    "is_returning_customer": False,
                    "total_interactions": 0
                }
            
            # Analyze interaction patterns
            categories = {}
            total_resolved = 0
            
            for ticket in tickets:
                metadata = ticket.ticket_metadata
                if metadata:
                    # Count categories
                    if metadata.main_issue_type:
                        categories[metadata.main_issue_type] = categories.get(metadata.main_issue_type, 0) + 1
                    
                    if metadata.status == "resolved":
                        total_resolved += 1
            
            # Most common category
            most_common_category = max(categories.items(), key=lambda x: x[1])[0] if categories else None
            
            return {
                "is_returning_customer": True,
                "total_interactions": len(tickets),
                "resolved_tickets": total_resolved,
                "most_common_category": most_common_category,
                "category_distribution": categories,
                "last_interaction": tickets[-1].created_at.isoformat() if tickets else None
            }
            
        finally:
            session.close()
    
    def find_similar_resolved_issues(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find similar resolved issues for reference.
        Uses simple keyword matching (can be enhanced with embeddings).
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of similar resolved issues
        """
        session = self.Session()
        
        try:
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            # Get resolved tickets
            tickets_query = session.query(udahub.Ticket).join(udahub.TicketMetadata).filter(
                udahub.Ticket.account_id == self.account_id,
                udahub.TicketMetadata.status == "resolved"
            )
            
            if category:
                tickets_query = tickets_query.filter(udahub.TicketMetadata.main_issue_type == category)
            
            tickets = tickets_query.all()
            
            # Score tickets by keyword matches
            scored_tickets = []
            for ticket in tickets:
                metadata = ticket.ticket_metadata
                score = 0
                text = f"{metadata.tags or ''} {metadata.main_issue_type or ''}".lower() if metadata else ""
                
                # Get ticket messages
                messages = session.query(udahub.TicketMessage).filter_by(
                    ticket_id=ticket.ticket_id
                ).all()
                
                for msg in messages:
                    if msg.content:
                        text += f" {msg.content}".lower()
                
                # Count keyword matches
                for word in query_words:
                    if len(word) > 2:
                        score += text.count(word)
                
                if score > 0:
                    # Get resolution (last AI message)
                    resolution_msg = next(
                        (m for m in reversed(messages) 
                         if m.role == udahub.RoleEnum.ai),
                        None
                    )
                    
                    scored_tickets.append({
                        "ticket_id": ticket.ticket_id,
                        "category": metadata.main_issue_type if metadata else None,
                        "subject": metadata.tags if metadata else None,
                        "resolution": resolution_msg.content if resolution_msg else None,
                        "relevance_score": score,
                        "resolved_at": metadata.updated_at.isoformat() if metadata and metadata.updated_at else None
                    })
            
            # Sort by score and return top results
            scored_tickets.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored_tickets[:limit]
            
        finally:
            session.close()


# Global memory manager instance
_memory_manager = None


def get_memory_manager(account_id: str = "cultpass") -> MemoryManager:
    """Get or create memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(account_id)
    return _memory_manager

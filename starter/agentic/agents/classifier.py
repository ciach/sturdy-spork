"""
Classifier Agent - Categorizes tickets and extracts key information.
"""

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import json
import re


class ClassifierAgent:
    """
    Agent responsible for classifying tickets and extracting entities.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.system_prompt = """You are a ticket classification expert for CultPass customer support.

Your task is to analyze customer support tickets and extract structured information.

Classify tickets into these categories:
- login: Login and authentication issues
- billing: Payment, refunds, subscription charges
- subscription: Subscription management, tier changes, cancellation
- reservation: Event booking, cancellation, viewing reservations
- technical: App crashes, bugs, performance issues
- account: Account settings, email changes, blocked accounts
- general: General inquiries, feedback, other

Extract these entities if present:
- user_id: User identifier (format: 6 character alphanumeric)
- reservation_id: Reservation identifier (format: 6 character alphanumeric)
- email: Email address

Determine urgency:
- critical: Account blocked, payment failures, cannot access service
- high: Cannot complete important action, event soon
- medium: General issues, questions
- low: Feedback, suggestions, general inquiries

Return your analysis as JSON with this structure:
{
    "category": "category_name",
    "urgency": "urgency_level",
    "entities": {
        "user_id": "extracted_user_id or null",
        "reservation_id": "extracted_reservation_id or null",
        "email": "extracted_email or null"
    },
    "intent": "brief description of user intent",
    "requires_tools": ["list", "of", "tool", "names"],
    "confidence": 0.0-1.0
}

Available tools: get_user_info, get_subscription_status, get_reservations, cancel_reservation, check_account_status, request_refund, search_knowledge_base"""
    
    def classify(self, ticket_text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify a ticket and extract structured information.
        
        Args:
            ticket_text: The ticket content
            metadata: Optional metadata about the ticket
            
        Returns:
            Classification results
        """
        try:
            # Prepare messages
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Ticket: {ticket_text}")
            ]
            
            if metadata:
                messages.append(HumanMessage(content=f"Metadata: {json.dumps(metadata)}"))
            
            # Get classification from LLM
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            try:
                classification = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    classification = json.loads(json_match.group())
                else:
                    # Fallback classification
                    classification = {
                        "category": "general",
                        "urgency": "medium",
                        "entities": {},
                        "intent": "Unable to parse classification",
                        "requires_tools": ["search_knowledge_base"],
                        "confidence": 0.3
                    }
            
            # Ensure all required fields exist
            classification.setdefault("category", "general")
            classification.setdefault("urgency", "medium")
            classification.setdefault("entities", {})
            classification.setdefault("intent", "")
            classification.setdefault("requires_tools", [])
            classification.setdefault("confidence", 0.5)
            
            return {
                "success": True,
                "classification": classification
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Classification error: {str(e)}",
                "classification": {
                    "category": "general",
                    "urgency": "medium",
                    "entities": {},
                    "intent": "",
                    "requires_tools": [],
                    "confidence": 0.0
                }
            }
    
    def extract_user_id(self, text: str) -> str:
        """Extract user ID from text using pattern matching."""
        # Look for 6-character alphanumeric user IDs
        match = re.search(r'\b([a-f0-9]{6})\b', text.lower())
        return match.group(1) if match else None
    
    def extract_email(self, text: str) -> str:
        """Extract email address from text."""
        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        return match.group(0) if match else None

"""
Escalation Agent - Handles cases requiring human intervention.
"""

from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import json
from datetime import datetime


class EscalationAgent:
    """
    Agent responsible for escalating complex cases to human agents.
    """

    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.system_prompt = """You are an escalation specialist for CultPass customer support.

Your role is to:
1. Prepare clear, concise escalation summaries for human agents
2. Provide appropriate interim responses to customers
3. Identify the key issues and attempted resolutions

When creating an escalation summary, include:
- Main issue/concern
- Classification and urgency
- What was attempted
- Why escalation is needed
- Relevant user/account information

Keep summaries professional and actionable."""

    def escalate(
        self,
        ticket_text: str,
        classification: Dict[str, Any],
        conversation_history: List[BaseMessage],
        escalation_reason: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Prepare escalation for human agent.

        Args:
            ticket_text: Original ticket text
            classification: Classification results
            conversation_history: Full conversation history
            escalation_reason: Reason for escalation
            context: Additional context (tool results, etc.)

        Returns:
            Escalation package with summary and user notification
        """
        try:
            # Prepare escalation summary
            summary_prompt = f"""Create an escalation summary for this support ticket.

Original Ticket: {ticket_text}

Classification:
- Category: {classification.get('category', 'unknown')}
- Urgency: {classification.get('urgency', 'medium')}
- Intent: {classification.get('intent', '')}

Escalation Reason: {escalation_reason}

Conversation History:
{self._format_conversation_history(conversation_history)}

Additional Context:
{json.dumps(context, indent=2) if context else 'None'}

Provide a concise escalation summary for the human agent."""

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=summary_prompt),
            ]

            summary_response = self.llm.invoke(messages)
            escalation_summary = summary_response.content

            # Generate user notification
            user_notification = self._generate_user_notification(
                classification.get("urgency", "medium"), escalation_reason
            )

            # Prepare escalation package
            escalation_package = {
                "success": True,
                "escalation_id": f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "summary": escalation_summary,
                "user_notification": user_notification,
                "classification": classification,
                "escalation_reason": escalation_reason,
                "urgency": classification.get("urgency", "medium"),
                "context": context or {},
            }

            return escalation_package

        except Exception as e:
            return {
                "success": False,
                "error": f"Escalation error: {str(e)}",
                "user_notification": "We're transferring you to a specialist who can better assist you. Please hold.",
            }

    def _format_conversation_history(self, messages: List[BaseMessage]) -> str:
        """Format conversation history for escalation summary."""
        formatted = []
        for msg in messages[-10:]:  # Last 10 messages
            role = msg.__class__.__name__.replace("Message", "")
            content = (
                msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            )
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _generate_user_notification(self, urgency: str, reason: str) -> str:
        """Generate appropriate user notification message."""
        if urgency == "critical":
            return "I understand this is urgent. I'm connecting you with a senior support specialist who can help you immediately. They'll be with you shortly."

        elif urgency == "high":
            return "I'm transferring your case to a specialist who can provide more detailed assistance. They'll reach out to you within the next few hours."

        elif "blocked" in reason.lower() or "suspended" in reason.lower():
            return "I see there's an issue with your account status. I'm escalating this to our account management team who will review your case and contact you within 24 hours."

        elif "refund" in reason.lower():
            return "I've submitted your refund request to our billing team for approval. You'll receive an update via email within 2-3 business days."

        else:
            return "I want to make sure you get the best possible help. I'm connecting you with a specialist who has more expertise in this area. They'll follow up with you soon."

    def create_interim_response(self, urgency: str, category: str) -> str:
        """
        Create an interim response while escalation is processed.

        Args:
            urgency: Urgency level
            category: Ticket category

        Returns:
            Interim response text
        """
        base_message = "Thank you for your patience. "

        if urgency == "critical":
            return (
                base_message
                + "A senior support specialist will contact you within the next hour to resolve this issue."
            )

        elif urgency == "high":
            return (
                base_message
                + "A specialist will review your case and respond within 4 hours."
            )

        else:
            return (
                base_message
                + "Our support team will review your case and get back to you within 24 hours."
            )

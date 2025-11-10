"""
Resolver Agent - Generates responses using knowledge base retrieval (RAG).
"""

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agentic.tools.knowledge_retrieval import search_knowledge_base


class ResolverAgent:
    """
    Agent responsible for resolving tickets using knowledge base.
    """

    def __init__(self, model_name: str = "gpt-4", confidence_threshold: float = 0.6):
        self.llm = ChatOpenAI(model=model_name, temperature=0.3)
        self.confidence_threshold = confidence_threshold
        self.system_prompt = """You are a helpful customer support agent for CultPass.

Your role is to provide accurate, friendly responses based on the knowledge base articles provided.

Guidelines:
1. Base your response ONLY on the provided knowledge articles
2. Be concise but complete
3. Use a friendly, professional tone
4. If the articles don't contain enough information, acknowledge this
5. Include specific steps when applicable
6. Reference relevant policies when needed

Format your response naturally, as if speaking directly to the customer.
Do not mention "knowledge base" or "articles" in your response - just provide the information."""

    def resolve(
        self,
        query: str,
        classification: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Attempt to resolve a ticket using knowledge base.

        Args:
            query: The user's question or issue
            classification: Classification results from ClassifierAgent
            context: Additional context (user info, tool results, etc.)

        Returns:
            Resolution attempt with confidence score
        """
        try:
            # Search knowledge base
            search_results = search_knowledge_base(query, top_k=3)

            if not search_results.get("success"):
                return {
                    "success": False,
                    "error": "Knowledge base search failed",
                    "should_escalate": True,
                }

            articles = search_results.get("articles", [])
            kb_confidence = search_results.get("confidence", 0.0)

            if not articles:
                return {
                    "success": True,
                    "response": None,
                    "confidence": 0.0,
                    "should_escalate": True,
                    "reason": "No relevant knowledge articles found",
                }

            # Prepare context for LLM
            articles_text = "\n\n---\n\n".join(
                [
                    f"Article: {article['title']}\n{article['content']}"
                    for article in articles
                ]
            )

            # Build prompt with context
            user_message = f"Customer Question: {query}\n\n"

            if context:
                # Add customer history for personalization
                if context.get("customer_history"):
                    history = context["customer_history"]
                    if history:
                        user_message += f"Customer History: This customer has {len(history)} previous interactions.\n"
                        # Add most recent issue
                        recent = history[0]
                        user_message += f"Most recent: {recent.get('category', 'N/A')} - {recent.get('subject', 'N/A')}\n\n"

                if context.get("user_info"):
                    user_message += f"User Info: {context['user_info']}\n"
                if context.get("tool_results"):
                    user_message += f"Additional Info: {context['tool_results']}\n"

            user_message += f"\nRelevant Knowledge Articles:\n{articles_text}\n\n"
            user_message += "Provide a helpful, personalized response based on the articles above and customer history."

            # Generate response
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_message),
            ]

            response = self.llm.invoke(messages)

            # Calculate overall confidence
            # Combine knowledge base confidence with article relevance
            response_confidence = kb_confidence

            # Adjust confidence based on classification if available
            if classification:
                class_confidence = classification.get("confidence", 0.5)
                response_confidence = (response_confidence + class_confidence) / 2

            should_escalate = response_confidence < self.confidence_threshold

            return {
                "success": True,
                "response": response.content,
                "confidence": response_confidence,
                "should_escalate": should_escalate,
                "articles_used": [
                    {
                        "title": article["title"],
                        "relevance": article.get("relevance_score", 0.0),
                    }
                    for article in articles
                ],
                "search_method": search_results.get("method", "unknown"),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Resolution error: {str(e)}",
                "should_escalate": True,
            }

    def generate_response_with_context(
        self, query: str, knowledge_articles: List[Dict], additional_context: str = ""
    ) -> str:
        """
        Generate a response using provided knowledge articles and context.

        Args:
            query: User question
            knowledge_articles: List of relevant articles
            additional_context: Any additional context to include

        Returns:
            Generated response text
        """
        articles_text = "\n\n---\n\n".join(
            [
                f"Article: {article['title']}\n{article.get('content', '')}"
                for article in knowledge_articles
            ]
        )

        user_message = f"Customer Question: {query}\n\n"
        if additional_context:
            user_message += f"Context: {additional_context}\n\n"
        user_message += (
            f"Knowledge Articles:\n{articles_text}\n\nProvide a helpful response."
        )

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

        response = self.llm.invoke(messages)
        return response.content

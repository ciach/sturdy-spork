"""
Enhanced Classifier Agent - Integrates sentiment analysis with classification.
"""

from typing import Dict, Any
from agentic.agents.classifier import ClassifierAgent
from agentic.agents.sentiment_analyzer import SentimentAnalyzer


class EnhancedClassifier:
    """
    Enhanced classifier that combines ticket classification with sentiment analysis.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        self.classifier = ClassifierAgent(model_name)
        self.sentiment_analyzer = SentimentAnalyzer(model_name)
    
    def classify_with_sentiment(self, ticket_text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify ticket and analyze sentiment in one pass.
        
        Args:
            ticket_text: The ticket content
            metadata: Optional metadata
            
        Returns:
            Combined classification and sentiment analysis
        """
        # Get base classification
        classification_result = self.classifier.classify(ticket_text, metadata)
        
        # Get sentiment analysis
        sentiment_result = self.sentiment_analyzer.analyze(ticket_text, metadata)
        
        if not classification_result.get("success"):
            return classification_result
        
        # Combine results
        classification = classification_result["classification"]
        
        # Adjust urgency based on sentiment
        if sentiment_result.get("success"):
            original_urgency = classification.get("urgency", "medium")
            adjusted_urgency = self.sentiment_analyzer.adjust_urgency(
                original_urgency,
                sentiment_result
            )
            
            # Get response guidelines
            guidelines = self.sentiment_analyzer.get_response_guidelines(sentiment_result)
            
            # Update classification with sentiment data
            classification["original_urgency"] = original_urgency
            classification["urgency"] = adjusted_urgency
            classification["urgency_adjusted"] = (original_urgency != adjusted_urgency)
            classification["sentiment"] = sentiment_result
            classification["response_guidelines"] = guidelines
            
            # Boost confidence if sentiment is clear
            if sentiment_result.get("urgency_score", 0) > 0.7:
                classification["confidence"] = min(classification.get("confidence", 0.5) + 0.1, 1.0)
        
        return {
            "success": True,
            "classification": classification,
            "sentiment_enhanced": sentiment_result.get("success", False)
        }

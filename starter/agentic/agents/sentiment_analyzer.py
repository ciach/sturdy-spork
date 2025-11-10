"""
Sentiment Analyzer Agent - Analyzes customer sentiment to prioritize tickets.
Detects frustration, urgency, and emotional tone to improve response quality.
"""

from typing import Dict, Any, Literal
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import json
import re


class SentimentAnalyzer:
    """
    Analyzes customer sentiment and emotional state to prioritize tickets.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.system_prompt = """You are an expert in customer sentiment analysis for support tickets.

Analyze the customer's message and determine:

1. **Sentiment**: positive, neutral, negative, or very_negative
2. **Emotion**: calm, concerned, frustrated, angry, urgent, or desperate
3. **Urgency Score**: 0.0 (low) to 1.0 (critical)
4. **Frustration Level**: 0.0 (none) to 1.0 (extreme)
5. **Key Indicators**: Specific words/phrases indicating emotional state

Urgency indicators:
- Time-sensitive language: "urgent", "immediately", "ASAP", "right now"
- Financial impact: "charged", "money", "refund", "billing"
- Service blocking: "can't access", "blocked", "locked out", "not working"
- Repeated issues: "again", "still", "multiple times"

Frustration indicators:
- Negative language: "terrible", "awful", "worst", "horrible"
- Capitalization: "HELP", "PLEASE", "WHY"
- Exclamation marks: "!!!", "?!?"
- Complaint language: "disappointed", "unacceptable", "ridiculous"

Return JSON format:
{
    "sentiment": "negative",
    "emotion": "frustrated",
    "urgency_score": 0.8,
    "frustration_level": 0.7,
    "priority_boost": 0.3,
    "key_indicators": ["can't access", "multiple times", "urgent"],
    "recommended_tone": "empathetic and solution-focused",
    "escalation_recommended": true/false
}"""
    
    def analyze(self, ticket_text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze sentiment and emotional state of a ticket.
        
        Args:
            ticket_text: The ticket content
            metadata: Optional metadata (existing classification, etc.)
            
        Returns:
            Sentiment analysis results
        """
        try:
            # Quick rule-based pre-analysis for efficiency
            quick_analysis = self._quick_sentiment_check(ticket_text)
            
            # If clearly urgent/frustrated, use LLM for detailed analysis
            if quick_analysis["urgency_score"] > 0.5 or quick_analysis["frustration_level"] > 0.5:
                return self._llm_sentiment_analysis(ticket_text, metadata)
            
            # Otherwise, use quick analysis with some LLM enhancement
            return self._enhanced_quick_analysis(ticket_text, quick_analysis, metadata)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Sentiment analysis error: {str(e)}",
                "sentiment": "neutral",
                "emotion": "calm",
                "urgency_score": 0.5,
                "frustration_level": 0.0,
                "priority_boost": 0.0
            }
    
    def _quick_sentiment_check(self, text: str) -> Dict[str, Any]:
        """Fast rule-based sentiment check."""
        text_lower = text.lower()
        
        # Urgency keywords
        urgency_keywords = {
            "urgent": 0.3, "immediately": 0.3, "asap": 0.3, "right now": 0.3,
            "critical": 0.4, "emergency": 0.5, "can't access": 0.4,
            "blocked": 0.4, "locked out": 0.4, "not working": 0.3,
            "broken": 0.3, "down": 0.2, "help": 0.2
        }
        
        # Frustration keywords
        frustration_keywords = {
            "frustrated": 0.3, "angry": 0.4, "disappointed": 0.3,
            "unacceptable": 0.4, "ridiculous": 0.4, "terrible": 0.4,
            "awful": 0.4, "worst": 0.4, "horrible": 0.4,
            "again": 0.2, "still": 0.2, "multiple times": 0.3
        }
        
        # Calculate scores
        urgency_score = 0.0
        frustration_score = 0.0
        indicators = []
        
        for keyword, weight in urgency_keywords.items():
            if keyword in text_lower:
                urgency_score += weight
                indicators.append(keyword)
        
        for keyword, weight in frustration_keywords.items():
            if keyword in text_lower:
                frustration_score += weight
                indicators.append(keyword)
        
        # Check for caps and exclamation marks
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:
            frustration_score += 0.2
            indicators.append("excessive capitalization")
        
        exclamation_count = text.count("!")
        if exclamation_count > 2:
            frustration_score += min(exclamation_count * 0.1, 0.3)
            indicators.append("multiple exclamation marks")
        
        # Normalize scores
        urgency_score = min(urgency_score, 1.0)
        frustration_score = min(frustration_score, 1.0)
        
        # Determine sentiment
        if frustration_score > 0.6:
            sentiment = "very_negative"
        elif frustration_score > 0.3:
            sentiment = "negative"
        elif urgency_score > 0.5:
            sentiment = "neutral"
        else:
            sentiment = "neutral"
        
        # Determine emotion
        if frustration_score > 0.6:
            emotion = "angry"
        elif frustration_score > 0.3:
            emotion = "frustrated"
        elif urgency_score > 0.6:
            emotion = "urgent"
        elif urgency_score > 0.3:
            emotion = "concerned"
        else:
            emotion = "calm"
        
        return {
            "sentiment": sentiment,
            "emotion": emotion,
            "urgency_score": urgency_score,
            "frustration_level": frustration_score,
            "key_indicators": indicators
        }
    
    def _llm_sentiment_analysis(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Detailed LLM-based sentiment analysis."""
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Ticket: {text}")
            ]
            
            if metadata:
                messages.append(HumanMessage(content=f"Context: {json.dumps(metadata)}"))
            
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    # Fallback to quick analysis
                    return self._quick_sentiment_check(text)
            
            # Ensure all required fields
            analysis.setdefault("sentiment", "neutral")
            analysis.setdefault("emotion", "calm")
            analysis.setdefault("urgency_score", 0.5)
            analysis.setdefault("frustration_level", 0.0)
            analysis.setdefault("priority_boost", 0.0)
            analysis.setdefault("key_indicators", [])
            analysis.setdefault("recommended_tone", "professional and helpful")
            analysis.setdefault("escalation_recommended", False)
            
            analysis["success"] = True
            analysis["method"] = "llm_analysis"
            
            return analysis
            
        except Exception as e:
            print(f"LLM sentiment analysis error: {e}")
            return self._quick_sentiment_check(text)
    
    def _enhanced_quick_analysis(self, text: str, quick_result: Dict, metadata: Dict = None) -> Dict[str, Any]:
        """Enhance quick analysis with additional context."""
        result = quick_result.copy()
        
        # Calculate priority boost
        priority_boost = (result["urgency_score"] * 0.6 + result["frustration_level"] * 0.4) * 0.5
        result["priority_boost"] = min(priority_boost, 0.5)
        
        # Recommend tone
        if result["frustration_level"] > 0.5:
            result["recommended_tone"] = "empathetic and apologetic"
        elif result["urgency_score"] > 0.7:
            result["recommended_tone"] = "prompt and solution-focused"
        else:
            result["recommended_tone"] = "professional and helpful"
        
        # Escalation recommendation
        result["escalation_recommended"] = (
            result["frustration_level"] > 0.7 or 
            result["urgency_score"] > 0.8
        )
        
        result["success"] = True
        result["method"] = "rule_based"
        
        return result
    
    def adjust_urgency(self, base_urgency: str, sentiment_data: Dict[str, Any]) -> str:
        """
        Adjust urgency level based on sentiment analysis.
        
        Args:
            base_urgency: Original urgency from classifier (low, medium, high, critical)
            sentiment_data: Sentiment analysis results
            
        Returns:
            Adjusted urgency level
        """
        urgency_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        reverse_map = {0: "low", 1: "medium", 2: "high", 3: "critical"}
        
        current_level = urgency_map.get(base_urgency, 1)
        
        # Boost based on sentiment
        if sentiment_data.get("frustration_level", 0) > 0.7:
            current_level = min(current_level + 1, 3)
        
        if sentiment_data.get("urgency_score", 0) > 0.8:
            current_level = min(current_level + 1, 3)
        
        if sentiment_data.get("emotion") == "angry":
            current_level = min(current_level + 1, 3)
        
        return reverse_map[current_level]
    
    def get_response_guidelines(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get response guidelines based on sentiment.
        
        Args:
            sentiment_data: Sentiment analysis results
            
        Returns:
            Response guidelines for agents
        """
        guidelines = {
            "tone": sentiment_data.get("recommended_tone", "professional and helpful"),
            "priority": "high" if sentiment_data.get("priority_boost", 0) > 0.3 else "normal",
            "empathy_level": "high" if sentiment_data.get("frustration_level", 0) > 0.5 else "standard",
            "response_speed": "immediate" if sentiment_data.get("urgency_score", 0) > 0.7 else "standard"
        }
        
        # Specific recommendations
        recommendations = []
        
        if sentiment_data.get("frustration_level", 0) > 0.5:
            recommendations.append("Acknowledge customer frustration")
            recommendations.append("Apologize for inconvenience")
        
        if sentiment_data.get("urgency_score", 0) > 0.7:
            recommendations.append("Prioritize immediate resolution")
            recommendations.append("Provide clear timeline")
        
        if sentiment_data.get("escalation_recommended"):
            recommendations.append("Consider escalation to senior agent")
        
        guidelines["recommendations"] = recommendations
        
        return guidelines

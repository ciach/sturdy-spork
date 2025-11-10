"""
Supervisor Agent - Coordinates and routes between specialized agents.
"""

from typing import Dict, Any, List, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import json


class SupervisorAgent:
    """
    Supervisor agent that coordinates the multi-agent workflow.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.system_prompt = """You are the supervisor agent for UDA-Hub customer support system.

Your role is to analyze the current state and decide which specialized agent should handle the next step.

Available agents:
1. CLASSIFIER - Categorizes tickets and extracts entities (use first for new tickets)
2. RESOLVER - Provides knowledge-based responses using RAG
3. TOOL - Executes database operations (user lookup, reservations, etc.)
4. ESCALATION - Handles complex cases requiring human intervention
5. FINISH - Concludes the ticket (use when resolved or escalated)

Decision logic:
- New ticket → CLASSIFIER
- After classification, if knowledge needed → RESOLVER
- If database operation needed → TOOL
- If low confidence or complex → ESCALATION
- If resolved or escalated → FINISH

Analyze the conversation state and return ONLY the name of the next agent: CLASSIFIER, RESOLVER, TOOL, ESCALATION, or FINISH.

Consider:
- What has been done already
- What information is still needed
- Whether the issue can be resolved
- Confidence levels
- User satisfaction"""
    
    def route(self, state: Dict[str, Any]) -> str:
        """
        Determine which agent should handle the next step.
        
        Args:
            state: Current workflow state
            
        Returns:
            Name of next agent to invoke
        """
        try:
            # Extract state information
            messages = state.get("messages", [])
            classification = state.get("classification")
            knowledge_results = state.get("knowledge_results")
            tool_results = state.get("tool_results")
            confidence_score = state.get("confidence_score", 0.0)
            escalation_needed = state.get("escalation_needed", False)
            
            # Count how many times we've visited each agent (to prevent loops)
            agent_visits = {}
            for msg in messages:
                if hasattr(msg, 'name') and msg.name:
                    agent_visits[msg.name] = agent_visits.get(msg.name, 0) + 1
            
            # Rule-based routing for efficiency
            
            # If escalation is explicitly needed
            if escalation_needed:
                return "ESCALATION"
            
            # If no classification yet, classify first
            if not classification:
                return "CLASSIFIER"
            
            # If classified but no resolution attempted
            if classification and not knowledge_results and not tool_results:
                # Check if tools are required
                required_tools = classification.get("classification", {}).get("requires_tools", [])
                
                # If specific database tools needed and tool agent hasn't been tried yet
                if any(tool in required_tools for tool in ["get_user_info", "get_subscription_status", "get_reservations", "cancel_reservation", "check_account_status", "request_refund"]):
                    # Only try tool once - if it didn't work, move to resolver
                    if agent_visits.get("tool_agent", 0) == 0:
                        return "TOOL"
                
                # Otherwise try knowledge-based resolution
                return "RESOLVER"
            
            # If knowledge resolution attempted
            if knowledge_results:
                should_escalate = knowledge_results.get("should_escalate", False)
                has_response = knowledge_results.get("response") is not None
                
                # If low confidence or no response, escalate
                if should_escalate or not has_response:
                    return "ESCALATION"
                
                # If good response, finish
                if has_response and confidence_score > 0.6:
                    return "FINISH"
                
                # If medium confidence, might need tools
                required_tools = classification.get("classification", {}).get("requires_tools", [])
                if required_tools and not tool_results:
                    return "TOOL"
                
                return "FINISH"
            
            # If tools executed but no resolution
            if tool_results and not knowledge_results:
                # Try to generate response with tool results
                return "RESOLVER"
            
            # Default: use LLM for complex routing
            return self._llm_route(state)
            
        except Exception as e:
            print(f"Routing error: {e}")
            # Safe fallback
            return "ESCALATION"
    
    def _llm_route(self, state: Dict[str, Any]) -> str:
        """Use LLM for complex routing decisions."""
        try:
            state_summary = self._summarize_state(state)
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Current state:\n{state_summary}\n\nWhich agent should handle the next step? Respond with ONLY the agent name.")
            ]
            
            response = self.llm.invoke(messages)
            agent_name = response.content.strip().upper()
            
            # Validate response
            valid_agents = ["CLASSIFIER", "RESOLVER", "TOOL", "ESCALATION", "FINISH"]
            if agent_name in valid_agents:
                return agent_name
            
            # Extract agent name if embedded in text
            for agent in valid_agents:
                if agent in agent_name:
                    return agent
            
            # Fallback
            return "RESOLVER"
            
        except Exception as e:
            print(f"LLM routing error: {e}")
            return "RESOLVER"
    
    def _summarize_state(self, state: Dict[str, Any]) -> str:
        """Create a summary of current state for LLM routing."""
        summary_parts = []
        
        messages = state.get("messages", [])
        if messages:
            last_user_msg = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    last_user_msg = msg.content
                    break
            if last_user_msg:
                summary_parts.append(f"User query: {last_user_msg[:200]}")
        
        classification = state.get("classification")
        if classification:
            cls = classification.get("classification", {})
            summary_parts.append(f"Category: {cls.get('category')}, Urgency: {cls.get('urgency')}")
        
        knowledge_results = state.get("knowledge_results")
        if knowledge_results:
            summary_parts.append(f"Knowledge search: {knowledge_results.get('count', 0)} articles found, confidence: {knowledge_results.get('confidence', 0):.2f}")
        
        tool_results = state.get("tool_results")
        if tool_results:
            summary_parts.append(f"Tools executed: {len(tool_results) if isinstance(tool_results, list) else 1}")
        
        confidence = state.get("confidence_score", 0.0)
        summary_parts.append(f"Overall confidence: {confidence:.2f}")
        
        return "\n".join(summary_parts)
    
    def should_continue(self, state: Dict[str, Any]) -> Literal["continue", "end"]:
        """
        Determine if workflow should continue or end.
        
        Args:
            state: Current workflow state
            
        Returns:
            "continue" or "end"
        """
        next_agent = state.get("next_agent")
        
        if next_agent == "FINISH":
            return "end"
        
        # Safety check: limit iterations
        messages = state.get("messages", [])
        if len(messages) > 20:  # Prevent infinite loops
            return "end"
        
        return "continue"

"""
UDA-Hub Workflow Orchestration using LangGraph.
Implements a supervisor pattern with specialized agents.
"""

import os
import sqlite3
from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
import operator

# Import agents
from agentic.agents.supervisor import SupervisorAgent
from agentic.agents.classifier import ClassifierAgent
from agentic.agents.resolver import ResolverAgent
from agentic.agents.tool_agent import ToolAgent
from agentic.agents.escalation import EscalationAgent

# Import memory manager
from agentic.tools.memory_manager import get_memory_manager


# Define the state schema
class AgentState(TypedDict):
    """State schema for the agent workflow."""
    messages: Annotated[List[BaseMessage], operator.add]
    ticket_id: str
    user_id: Optional[str]
    customer_id: Optional[str]  # For persistent memory
    classification: Optional[Dict[str, Any]]
    knowledge_results: Optional[Dict[str, Any]]
    tool_results: Optional[List[Dict[str, Any]]]
    confidence_score: float
    next_agent: Optional[str]
    escalation_needed: bool
    resolution: Optional[str]
    escalation_data: Optional[Dict[str, Any]]
    customer_history: Optional[List[Dict[str, Any]]]  # Historical interactions


# Initialize agents
supervisor = SupervisorAgent()
classifier = ClassifierAgent()
resolver = ResolverAgent()
tool_agent = ToolAgent()
escalation_agent = EscalationAgent()


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor node - determines next agent to invoke.
    """
    next_agent = supervisor.route(state)
    state["next_agent"] = next_agent
    
    # Add supervisor decision to messages
    decision_msg = AIMessage(
        content=f"[Supervisor: Routing to {next_agent}]",
        name="supervisor"
    )
    
    return {
        **state,
        "messages": [decision_msg],
        "next_agent": next_agent
    }


def classifier_node(state: AgentState) -> AgentState:
    """
    Classifier node - categorizes ticket and extracts entities.
    """
    # Get the last user message
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage) and not msg.content.startswith("["):
            user_message = msg.content
            break
    
    if not user_message:
        return state
    
    # Classify the ticket
    result = classifier.classify(user_message)
    
    if result["success"]:
        classification = result["classification"]
        state["classification"] = result
        
        # Extract user_id if found
        entities = classification.get("entities", {})
        if entities.get("user_id"):
            state["user_id"] = entities["user_id"]
        
        # Update confidence
        state["confidence_score"] = classification.get("confidence", 0.5)
        
        # Add classification result to messages
        class_msg = AIMessage(
            content=f"[Classified as: {classification['category']}, Urgency: {classification['urgency']}]",
            name="classifier"
        )
        
        return {
            **state,
            "messages": [class_msg]
        }
    
    return state


def resolver_node(state: AgentState) -> AgentState:
    """
    Resolver node - attempts knowledge-based resolution.
    """
    # Get the user query
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage) and not msg.content.startswith("["):
            user_message = msg.content
            break
    
    if not user_message:
        return state
    
    # Prepare context with customer history
    context = {}
    if state.get("tool_results"):
        context["tool_results"] = state["tool_results"]
    if state.get("user_id"):
        context["user_id"] = state["user_id"]
    if state.get("customer_history"):
        context["customer_history"] = state["customer_history"]
    
    # Attempt resolution
    result = resolver.resolve(
        query=user_message,
        classification=state.get("classification", {}).get("classification"),
        context=context
    )
    
    state["knowledge_results"] = result
    
    if result.get("success") and result.get("response"):
        state["resolution"] = result["response"]
        state["confidence_score"] = result.get("confidence", 0.5)
        state["escalation_needed"] = result.get("should_escalate", False)
        
        # Add response to messages
        response_msg = AIMessage(
            content=result["response"],
            name="resolver"
        )
        
        return {
            **state,
            "messages": [response_msg]
        }
    else:
        state["escalation_needed"] = True
        
        no_answer_msg = AIMessage(
            content="[No sufficient knowledge found - escalation needed]",
            name="resolver"
        )
        
        return {
            **state,
            "messages": [no_answer_msg]
        }


def tool_node(state: AgentState) -> AgentState:
    """
    Tool node - executes database operations.
    """
    classification = state.get("classification", {}).get("classification", {})
    required_tools = classification.get("requires_tools", [])
    entities = classification.get("entities", {})
    
    # Filter for database tools only
    db_tools = [
        tool for tool in required_tools 
        if tool in tool_agent.get_available_tools()
    ]
    
    if not db_tools:
        # No tools to execute - add message to mark we tried
        tool_msg = AIMessage(
            content="[Tool Agent: No tools to execute]",
            name="tool_agent"
        )
        return {
            **state,
            "messages": [tool_msg]
        }
    
    # Execute tools
    tool_results = []
    skipped_tools = []
    
    for tool_name in db_tools:
        # Prepare parameters based on tool
        params = {}
        
        if "user_id" in tool_name or tool_name in ["get_user_info", "get_subscription_status", "get_reservations", "check_account_status"]:
            if state.get("user_id"):
                params["user_id"] = state["user_id"]
            elif entities.get("user_id"):
                params["user_id"] = entities["user_id"]
            else:
                skipped_tools.append(f"{tool_name} (no user_id)")
                continue  # Skip if no user_id
        
        if tool_name == "cancel_reservation" and entities.get("reservation_id"):
            params["reservation_id"] = entities["reservation_id"]
            if state.get("user_id"):
                params["user_id"] = state["user_id"]
        
        if tool_name == "request_refund":
            if entities.get("reservation_id") and state.get("user_id"):
                params["reservation_id"] = entities["reservation_id"]
                params["user_id"] = state["user_id"]
                params["reason"] = "User requested refund"
        
        # Execute tool
        if params:
            result = tool_agent.execute_tool(tool_name, params)
            tool_results.append(result)
    
    # Always add a message to mark tool agent was invoked
    if tool_results:
        state["tool_results"] = tool_results
        
        # Format results for message
        results_text = "\n".join([
            tool_agent.format_tool_result(result)
            for result in tool_results
        ])
        
        tool_msg = AIMessage(
            content=f"[Tool Results]\n{results_text}",
            name="tool_agent"
        )
    else:
        # No results but we tried - important for loop detection
        skip_msg = f"Skipped: {', '.join(skipped_tools)}" if skipped_tools else "No tools could be executed"
        tool_msg = AIMessage(
            content=f"[Tool Agent: {skip_msg}]",
            name="tool_agent"
        )
    
    return {
        **state,
        "messages": [tool_msg]
    }


def escalation_node(state: AgentState) -> AgentState:
    """
    Escalation node - prepares case for human agent.
    """
    # Get conversation history
    conversation_history = state.get("messages", [])
    
    # Get original ticket
    ticket_text = None
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage) and not msg.content.startswith("["):
            ticket_text = msg.content
            break
    
    if not ticket_text:
        ticket_text = "No ticket text available"
    
    # Determine escalation reason
    escalation_reason = "Unable to resolve with available knowledge and tools"
    
    knowledge_results = state.get("knowledge_results")
    if knowledge_results:
        if knowledge_results.get("reason"):
            escalation_reason = knowledge_results["reason"]
        elif knowledge_results.get("confidence", 0) < 0.5:
            escalation_reason = "Low confidence in knowledge-based resolution"
    
    # Prepare context
    context = {
        "user_id": state.get("user_id"),
        "tool_results": state.get("tool_results"),
        "knowledge_results": state.get("knowledge_results")
    }
    
    # Create escalation
    classification = state.get("classification", {}).get("classification", {})
    
    escalation_result = escalation_agent.escalate(
        ticket_text=ticket_text,
        classification=classification,
        conversation_history=conversation_history,
        escalation_reason=escalation_reason,
        context=context
    )
    
    state["escalation_data"] = escalation_result
    state["resolution"] = escalation_result.get("user_notification")
    
    # Add escalation message
    escalation_msg = AIMessage(
        content=escalation_result.get("user_notification", "Escalating to human agent..."),
        name="escalation_agent"
    )
    
    return {
        **state,
        "messages": [escalation_msg]
    }


def load_customer_history_node(state: AgentState) -> AgentState:
    """
    Load customer interaction history for personalization.
    """
    customer_id = state.get("customer_id") or state.get("user_id")
    
    if not customer_id:
        return state
    
    try:
        memory_mgr = get_memory_manager()
        
        # Get customer history
        history = memory_mgr.get_customer_history(customer_id, limit=3, include_messages=True)
        
        # Get customer preferences
        preferences = memory_mgr.get_customer_preferences(customer_id)
        
        state["customer_history"] = history
        
        # Add context message if returning customer
        if preferences.get("is_returning_customer"):
            context_msg = AIMessage(
                content=f"[Customer Context: Returning customer with {preferences['total_interactions']} previous interactions. Most common category: {preferences.get('most_common_category', 'N/A')}]",
                name="memory_system"
            )
            return {
                **state,
                "messages": [context_msg]
            }
    except Exception as e:
        print(f"Error loading customer history: {e}")
    
    return state


def save_interaction_node(state: AgentState) -> AgentState:
    """
    Save interaction to persistent database.
    """
    # Get ticket_id from state or generate from thread_id
    ticket_id = state.get("ticket_id")
    if not ticket_id:
        # Generate ticket_id from thread config if not provided
        import uuid
        ticket_id = f"ticket_{uuid.uuid4().hex[:12]}"
        state["ticket_id"] = ticket_id
    
    customer_id = state.get("customer_id") or state.get("user_id")
    messages = state.get("messages", [])
    classification = state.get("classification")
    
    # Determine resolution status
    if state.get("escalation_needed") or state.get("escalation_data"):
        status = "escalated"
    elif state.get("resolution"):
        status = "resolved"
    else:
        status = "open"
    
    try:
        memory_mgr = get_memory_manager()
        memory_mgr.save_interaction(
            ticket_id=ticket_id,
            customer_id=customer_id,
            messages=messages,
            classification=classification,
            resolution_status=status
        )
    except Exception as e:
        print(f"Error saving interaction: {e}")
    
    return state


def route_after_supervisor(state: AgentState) -> str:
    """
    Routing function after supervisor decision.
    """
    next_agent = state.get("next_agent", "FINISH")
    
    if next_agent == "FINISH":
        return END
    
    return next_agent.lower()


# Build the workflow graph
def create_workflow():
    """
    Create the LangGraph workflow.
    """
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("load_history", load_customer_history_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("resolver", resolver_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("escalation", escalation_node)
    workflow.add_node("save_interaction", save_interaction_node)
    
    # Set entry point - load history first
    workflow.set_entry_point("load_history")
    
    # Load history then go to supervisor
    workflow.add_edge("load_history", "supervisor")
    
    # Add edges from supervisor to agents
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "classifier": "classifier",
            "resolver": "resolver",
            "tool": "tool",
            "escalation": "escalation",
            END: "save_interaction"  # Save before ending
        }
    )
    
    # All agents return to supervisor for next decision
    workflow.add_edge("classifier", "supervisor")
    workflow.add_edge("resolver", "supervisor")
    workflow.add_edge("tool", "supervisor")
    workflow.add_edge("escalation", "save_interaction")
    
    # Save interaction then end
    workflow.add_edge("save_interaction", END)
    
    # Setup memory with SQLite checkpointer
    memory_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "core",
        "checkpoints.db"
    )
    # Ensure the directory exists
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)
    # Create SQLite connection and SqliteSaver
    conn = sqlite3.connect(os.path.abspath(memory_path), check_same_thread=False)
    memory = SqliteSaver(conn)
    
    # Compile graph
    app = workflow.compile(checkpointer=memory)
    
    return app


# Create the orchestrator
orchestrator = create_workflow()

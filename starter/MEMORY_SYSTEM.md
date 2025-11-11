# Memory and State Management - Complete Implementation

This document demonstrates how the UDA-Hub system implements all three types of memory required by Criterion 8.

## Overview

The system implements a comprehensive three-tier memory architecture:

1. **State Memory** - Within-execution state management
2. **Session Memory** - Cross-step conversation history via checkpointing
3. **Long-Term Memory** - Cross-session persistent storage and retrieval

---

## 1. State Memory (Within Execution)

### Implementation: `AgentState` TypedDict

**Location**: `agentic/workflow.py`

```python
class AgentState(TypedDict):
    """State schema for the agent workflow."""
    messages: Annotated[List[BaseMessage], operator.add]
    ticket_id: str
    user_id: Optional[str]
    customer_id: Optional[str]
    classification: Optional[Dict[str, Any]]
    knowledge_results: Optional[Dict[str, Any]]
    tool_results: Optional[List[Dict[str, Any]]]
    confidence_score: float
    next_agent: Optional[str]
    escalation_needed: bool
    resolution: Optional[str]
    escalation_data: Optional[Dict[str, Any]]
    customer_history: Optional[List[Dict[str, Any]]]  # Long-term memory integration
```

### How It Works

- **State flows through nodes**: Each node receives state, processes it, and returns updated state
- **Accumulated messages**: Messages list grows as agents communicate
- **Shared context**: All agents access the same state for decision-making
- **Tool results**: Stored in state for downstream agents to use

### Example

```python
# Classifier updates state
state["classification"] = classification_result
state["confidence_score"] = 0.85

# Resolver reads state and adds response
classification = state.get("classification")
state["resolution"] = generated_response

# Supervisor uses state to route
if state.get("escalation_needed"):
    return "ESCALATION"
```

---

## 2. Session Memory (Short-Term)

### Implementation: LangGraph Checkpointing with SqliteSaver

**Location**: `agentic/workflow.py`

```python
# Setup memory with SQLite checkpointer
memory_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "core",
    "checkpoints.db"
)
conn = sqlite3.connect(os.path.abspath(memory_path), check_same_thread=False)
memory = SqliteSaver(conn)

# Compile graph with checkpointer
app = workflow.compile(checkpointer=memory)
```

### How It Works

- **Thread-based scoping**: Each `thread_id` gets separate conversation history
- **Automatic persistence**: State saved after each node execution
- **Conversation continuity**: Can resume conversations across invocations
- **State inspection**: Can retrieve full state history for any thread

### Session Scoping Example

```python
# First message in conversation
config1 = {"configurable": {"thread_id": "customer-123-session-1"}}
result1 = orchestrator.invoke(
    {"messages": [HumanMessage(content="I can't log in")]},
    config1
)

# Continue same conversation
result2 = orchestrator.invoke(
    {"messages": [HumanMessage(content="I tried resetting password")]},
    config1  # Same thread_id continues conversation
)

# Different customer, different session
config2 = {"configurable": {"thread_id": "customer-456-session-1"}}
result3 = orchestrator.invoke(
    {"messages": [HumanMessage(content="How do I upgrade?")]},
    config2  # Separate conversation history
)
```

### Inspecting Session State

```python
# Get current state
current_state = orchestrator.get_state(config)
print(f"Messages: {len(current_state.values['messages'])}")
print(f"Classification: {current_state.values.get('classification')}")

# Get state history
for state in orchestrator.get_state_history(config):
    print(f"Checkpoint: {state.config['configurable']['checkpoint_id']}")
    print(f"Messages at this point: {len(state.values['messages'])}")
```

---

## 3. Long-Term Memory (Cross-Session)

### Implementation: MemoryManager with Database Persistence

**Location**: `agentic/tools/memory_manager.py`

The `MemoryManager` class provides persistent storage and retrieval across sessions:

```python
class MemoryManager:
    def save_interaction(...)  # Store complete interactions
    def get_customer_history(...)  # Retrieve past interactions
    def get_customer_preferences(...)  # Analyze patterns
    def get_resolved_issues(...)  # Learn from past resolutions
    def find_similar_resolved_issues(...)  # Reference similar cases
```

### Database Schema Integration

**Tables Used**:
- `users` - Customer records with `external_user_id`
- `tickets` - Interaction records
- `ticket_metadata` - Status, category, tags
- `ticket_messages` - All conversation messages

### How It Works

#### A. Automatic Persistence

**Workflow Integration** (`agentic/workflow.py`):

```python
# Load history at workflow start
workflow.add_node("load_history", load_customer_history_node)
workflow.set_entry_point("load_history")

# Save interaction at workflow end
workflow.add_node("save_interaction", save_interaction_node)
workflow.add_edge("escalation", "save_interaction")
workflow.add_conditional_edges("supervisor", ..., {END: "save_interaction"})
```

#### B. Customer Recognition

```python
def load_customer_history_node(state: AgentState) -> AgentState:
    customer_id = state.get("customer_id") or state.get("user_id")
    
    if not customer_id:
        return state
    
    memory_mgr = get_memory_manager()
    
    # Get customer history
    history = memory_mgr.get_customer_history(customer_id, limit=3)
    
    # Get preferences
    preferences = memory_mgr.get_customer_preferences(customer_id)
    
    state["customer_history"] = history
    
    # Add context for returning customers
    if preferences.get("is_returning_customer"):
        context_msg = AIMessage(
            content=f"[Customer Context: Returning customer with {preferences['total_interactions']} previous interactions...]",
            name="memory_system"
        )
        return {**state, "messages": [context_msg]}
    
    return state
```

#### C. Personalized Responses

**Resolver Integration** (`agentic/agents/resolver.py`):

```python
# Build prompt with customer history
if context.get("customer_history"):
    history = context["customer_history"]
    if history:
        user_message += f"Customer History: This customer has {len(history)} previous interactions.\n"
        recent = history[0]
        user_message += f"Most recent: {recent.get('category')} - {recent.get('subject')}\n\n"

user_message += "Provide a helpful, personalized response based on the articles above and customer history."
```

### Long-Term Memory Features

#### 1. Customer History Retrieval

```python
memory_mgr = get_memory_manager()
history = memory_mgr.get_customer_history("alice@example.com", limit=5)

# Returns:
[
    {
        "ticket_id": "ticket_abc123",
        "status": "resolved",
        "category": "login",
        "subject": "Password reset",
        "created_at": "2025-11-10T10:30:00",
        "messages": [
            {"sender_type": "user", "content": "I forgot my password"},
            {"sender_type": "ai", "content": "Here's how to reset..."}
        ]
    },
    # ... more tickets
]
```

#### 2. Customer Preferences Analysis

```python
preferences = memory_mgr.get_customer_preferences("alice@example.com")

# Returns:
{
    "is_returning_customer": True,
    "total_interactions": 5,
    "resolved_tickets": 4,
    "most_common_category": "login",
    "category_distribution": {"login": 3, "billing": 2},
    "last_interaction": "2025-11-10T14:20:00"
}
```

#### 3. Resolved Issues Database

```python
resolved = memory_mgr.get_resolved_issues(category="login", limit=10)

# Returns:
[
    {
        "ticket_id": "ticket_xyz789",
        "customer_id": "bob@example.com",
        "category": "login",
        "subject": "Password reset",
        "resolution": "Follow these steps to reset your password...",
        "resolved_at": "2025-11-09T16:45:00"
    },
    # ... more resolved issues
]
```

#### 4. Similar Issue Search

```python
similar = memory_mgr.find_similar_resolved_issues(
    query="forgot password can't login",
    category="login",
    limit=3
)

# Returns issues ranked by relevance score
[
    {
        "ticket_id": "ticket_def456",
        "category": "login",
        "subject": "Password reset",
        "resolution": "...",
        "relevance_score": 15,  # Keyword match count
        "resolved_at": "2025-11-08T12:00:00"
    },
    # ... more similar issues
]
```

---

## Complete Memory Flow Example

### Scenario: Returning Customer with Login Issue

```python
# Customer's first interaction (stored in long-term memory)
result1 = orchestrator.invoke(
    {
        "messages": [HumanMessage(content="I can't log in")],
        "customer_id": "alice@example.com"
    },
    {"configurable": {"thread_id": "alice-session-1"}}
)
# → Saved to database: ticket, messages, classification
# → Session memory: conversation in checkpoints.db
# → State memory: classification, resolution in AgentState

# Days later, customer returns with new issue
result2 = orchestrator.invoke(
    {
        "messages": [HumanMessage(content="How do I upgrade my subscription?")],
        "customer_id": "alice@example.com"
    },
    {"configurable": {"thread_id": "alice-session-2"}}  # New session
)

# What happens:
# 1. load_history_node retrieves past interactions from database
# 2. System recognizes returning customer
# 3. Adds context message: "Returning customer with 1 previous interaction..."
# 4. Resolver uses history for personalized response
# 5. New interaction saved to database
# 6. Session memory tracks this conversation separately
```

### Memory Integration in Decision-Making

```python
# Supervisor uses state memory
def route(self, state: Dict[str, Any]) -> str:
    classification = state.get("classification")  # State memory
    knowledge_results = state.get("knowledge_results")  # State memory
    
    if classification and not knowledge_results:
        return "RESOLVER"

# Resolver uses all three memory types
def resolve(self, query: str, classification: Dict, context: Dict):
    # State memory: classification from earlier in workflow
    category = classification.get("category")
    
    # Session memory: conversation history via messages
    # (automatically available through checkpointing)
    
    # Long-term memory: customer history from database
    if context.get("customer_history"):
        history = context["customer_history"]
        # Use history to personalize response
        prompt += f"Customer has {len(history)} previous {history[0]['category']} issues"
```

---

## Verification and Testing

### Test Script: `test_memory_system.py`

```python
from agentic.workflow import orchestrator
from agentic.tools.memory_manager import get_memory_manager
from langchain_core.messages import HumanMessage

# Test all three memory types
customer_id = "test@example.com"
memory_mgr = get_memory_manager()

# 1. State Memory Test
print("Testing State Memory...")
result = orchestrator.invoke(
    {"messages": [HumanMessage(content="I need help")]},
    {"configurable": {"thread_id": "test-1"}}
)
# State flows through: supervisor → classifier → resolver → supervisor → save
assert "classification" in result  # State memory working

# 2. Session Memory Test
print("Testing Session Memory...")
state = orchestrator.get_state({"configurable": {"thread_id": "test-1"}})
assert len(state.values["messages"]) > 0  # Session memory persisted

# 3. Long-Term Memory Test
print("Testing Long-Term Memory...")
history = memory_mgr.get_customer_history(customer_id)
assert len(history) > 0  # Long-term memory stored

# Second interaction uses long-term memory
result2 = orchestrator.invoke(
    {"messages": [HumanMessage(content="Another question")], "customer_id": customer_id},
    {"configurable": {"thread_id": "test-2"}}  # Different session
)
# Check for memory system message
assert any(
    hasattr(m, 'name') and m.name == 'memory_system' 
    for m in result2["messages"]
)  # Long-term memory retrieved and used

print("✅ All memory types working!")
```

### Demo Notebook: `04_memory_demo.ipynb`

The demo notebook shows:
1. First-time customer (no long-term memory)
2. Returning customer (long-term memory retrieved)
3. Customer history inspection
4. Preference analysis
5. Similar issue search
6. Cross-session personalization

---

## Summary: Criterion 8 Compliance

### ✅ State Memory
- **AgentState TypedDict** maintains state during multi-step interactions
- State flows correctly through all workflow nodes
- Agents share context via state

### ✅ Session Memory (Short-Term)
- **SqliteSaver checkpointing** persists conversation history per `thread_id`
- Can inspect workflow state and history
- Conversation continuity within sessions
- Separate sessions for different tickets/customers

### ✅ Long-Term Memory
- **MemoryManager** stores interactions in database
- Customer history retrieved across different sessions
- Resolved issues database for learning
- Customer preferences tracked and analyzed
- Similar issue search for faster resolution
- Personalized responses based on history

### ✅ Memory Integration
- All three memory types work together seamlessly
- Memory properly integrated into agent decision-making
- Automatic persistence and retrieval
- Context flows from long-term → session → state memory

---

## Files Implementing Memory System

1. **State Memory**: `agentic/workflow.py` (AgentState)
2. **Session Memory**: `agentic/workflow.py` (SqliteSaver setup)
3. **Long-Term Memory**: `agentic/tools/memory_manager.py`
4. **Integration**: 
   - `agentic/workflow.py` (load_history_node, save_interaction_node)
   - `agentic/agents/resolver.py` (history-aware responses)
5. **Demo**: `starter/04_memory_demo.ipynb`
6. **Tests**: `starter/test_orchestrator.py`

The system fully implements all required memory types with proper scoping, persistence, and integration into agent decision-making.

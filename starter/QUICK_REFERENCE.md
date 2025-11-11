# Quick Reference - Memory System

## Using the Memory System

### Basic Usage

```python
from langchain_core.messages import HumanMessage
from agentic.workflow import orchestrator

# Include customer_id to enable long-term memory
result = orchestrator.invoke(
    {
        "messages": [HumanMessage(content="Your question here")],
        "customer_id": "customer@example.com"  # Optional but recommended
    },
    {
        "configurable": {
            "thread_id": "unique-session-id"  # Required for session memory
        }
    }
)
```

### Accessing Different Memory Types

#### 1. State Memory (Current Execution)

```python
# Access state during workflow
result = orchestrator.invoke(state, config)

# State contains:
result["classification"]      # Classification results
result["knowledge_results"]   # RAG search results
result["tool_results"]        # Database query results
result["customer_history"]    # Long-term memory
result["messages"]            # All messages
```

#### 2. Session Memory (Checkpointing)

```python
config = {"configurable": {"thread_id": "session-123"}}

# Get current state
current_state = orchestrator.get_state(config)
print(f"Messages: {len(current_state.values['messages'])}")

# Get state history
for state in orchestrator.get_state_history(config):
    print(f"Checkpoint: {state.config['configurable']['checkpoint_id']}")
    print(f"Messages: {len(state.values['messages'])}")
```

#### 3. Long-Term Memory (Database)

```python
from agentic.tools.memory_manager import get_memory_manager

memory_mgr = get_memory_manager()

# Get customer history
history = memory_mgr.get_customer_history("customer@example.com", limit=5)
for ticket in history:
    print(f"Ticket: {ticket['ticket_id']}")
    print(f"Category: {ticket['category']}")
    print(f"Messages: {ticket['message_count']}")

# Get customer preferences
prefs = memory_mgr.get_customer_preferences("customer@example.com")
print(f"Total interactions: {prefs['total_interactions']}")
print(f"Most common category: {prefs['most_common_category']}")

# Find similar resolved issues
similar = memory_mgr.find_similar_resolved_issues(
    query="password reset problem",
    limit=3
)
for issue in similar:
    print(f"Similar: {issue['subject']} (score: {issue['relevance_score']})")
```

## Common Patterns

### Pattern 1: New Customer

```python
# First interaction - no history
result = orchestrator.invoke(
    {
        "messages": [HumanMessage(content="I need help")],
        "customer_id": "new_customer@example.com"
    },
    {"configurable": {"thread_id": "new-session-1"}}
)
# → System treats as new customer
# → Interaction saved to database
```

### Pattern 2: Returning Customer

```python
# Customer returns (different session)
result = orchestrator.invoke(
    {
        "messages": [HumanMessage(content="Another question")],
        "customer_id": "new_customer@example.com"  # Same customer
    },
    {"configurable": {"thread_id": "new-session-2"}}  # Different session
)
# → System recognizes returning customer
# → Loads history from database
# → Adds context message
# → Personalizes response
```

### Pattern 3: Continuing Conversation

```python
config = {"configurable": {"thread_id": "ongoing-conversation"}}

# First message
result1 = orchestrator.invoke(
    {"messages": [HumanMessage(content="I can't log in")]},
    config
)

# Follow-up in same session
result2 = orchestrator.invoke(
    {"messages": [HumanMessage(content="I tried resetting my password")]},
    config  # Same thread_id
)
# → Conversation continues
# → Full history available via checkpointing
```

### Pattern 4: Inspecting Memory

```python
# Check what's stored for a customer
memory_mgr = get_memory_manager()

customer_id = "alice@example.com"

# History
history = memory_mgr.get_customer_history(customer_id)
print(f"Total tickets: {len(history)}")

# Preferences
prefs = memory_mgr.get_customer_preferences(customer_id)
print(f"Returning customer: {prefs['is_returning_customer']}")
print(f"Most common issue: {prefs['most_common_category']}")

# Session state
config = {"configurable": {"thread_id": "alice-session-1"}}
state = orchestrator.get_state(config)
print(f"Session messages: {len(state.values['messages'])}")
```

## Testing

### Quick Test

```bash
cd starter
python test_memory_system.py
```

### Interactive Demo

```bash
jupyter notebook 04_memory_demo.ipynb
```

### Manual Test

```python
from langchain_core.messages import HumanMessage
from agentic.workflow import orchestrator
from agentic.tools.memory_manager import get_memory_manager

# Create some history
customer_id = "test@example.com"

for i in range(3):
    orchestrator.invoke(
        {
            "messages": [HumanMessage(content=f"Question {i+1}")],
            "customer_id": customer_id
        },
        {"configurable": {"thread_id": f"test-session-{i}"}}
    )

# Check what was stored
memory_mgr = get_memory_manager()
history = memory_mgr.get_customer_history(customer_id)
print(f"Stored {len(history)} interactions")

# New interaction should recognize customer
result = orchestrator.invoke(
    {
        "messages": [HumanMessage(content="New question")],
        "customer_id": customer_id
    },
    {"configurable": {"thread_id": "test-session-final"}}
)

# Look for memory system message
for msg in result["messages"]:
    if hasattr(msg, 'name') and msg.name == 'memory_system':
        print(f"Memory recognized: {msg.content}")
```

## Troubleshooting

### Memory Not Persisting

**Problem**: Long-term memory not saving

**Solution**: Make sure to include `customer_id` in state:
```python
result = orchestrator.invoke(
    {
        "messages": [...],
        "customer_id": "customer@example.com"  # Required!
    },
    config
)
```

### Session Not Continuing

**Problem**: Each invocation starts fresh

**Solution**: Use same `thread_id` for continuation:
```python
config = {"configurable": {"thread_id": "same-session-id"}}
result1 = orchestrator.invoke(state1, config)
result2 = orchestrator.invoke(state2, config)  # Same config!
```

### Customer Not Recognized

**Problem**: Returning customer not recognized

**Solution**: 
1. Check customer_id is consistent
2. Verify data was saved:
```python
memory_mgr = get_memory_manager()
history = memory_mgr.get_customer_history("customer@example.com")
print(f"Found {len(history)} tickets")
```

### Slow Performance

**Problem**: First query takes too long

**Solution**: This is normal - building FAISS cache. Subsequent queries are faster.
- First query: ~10-15s (builds cache)
- Later queries: ~2-5s (uses cache)

## Key Files

- **Workflow**: `agentic/workflow.py`
- **Memory Manager**: `agentic/tools/memory_manager.py`
- **Tests**: `test_memory_system.py`
- **Demo**: `04_memory_demo.ipynb`
- **Docs**: `MEMORY_SYSTEM.md`

## Memory Types Summary

| Type | Scope | Storage | Use Case |
|------|-------|---------|----------|
| **State** | Single execution | In-memory | Agent coordination |
| **Session** | Thread/conversation | SQLite checkpoints | Conversation continuity |
| **Long-Term** | Customer/cross-session | Database tables | Personalization, learning |

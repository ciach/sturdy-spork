# UDA-Hub: Universal Decision Agent for Customer Support

## Overview

UDA-Hub is an intelligent multi-agent system built with LangGraph that automates customer support ticket resolution for CultPass. The system uses a supervisor pattern to coordinate specialized agents that classify, resolve, and escalate tickets based on knowledge base articles and database operations.

## Architecture

The system implements a **Hierarchical Supervisor Pattern** with the following agents:

1. **Supervisor Agent** - Central coordinator that routes tickets to specialized agents
2. **Classifier Agent** - Categorizes tickets and extracts entities
3. **Resolver Agent** - Provides knowledge-based responses using RAG
4. **Tool Agent** - Executes database operations
5. **Escalation Agent** - Handles complex cases requiring human intervention

See `agentic/design/architecture.md` for detailed architecture documentation.

## Project Structure

```
starter/
├── agentic/
│   ├── agents/
│   │   ├── supervisor.py       # Supervisor agent
│   │   ├── classifier.py       # Classification agent
│   │   ├── resolver.py         # Knowledge-based resolution
│   │   ├── tool_agent.py       # Database operations
│   │   └── escalation.py       # Escalation handling
│   ├── design/
│   │   └── architecture.md     # Architecture documentation
│   ├── tools/
│   │   ├── database_tools.py   # CultPass database tools
│   │   └── knowledge_retrieval.py  # RAG implementation
│   └── workflow.py             # LangGraph orchestration
├── data/
│   ├── core/
│   │   ├── udahub.db          # Core application database
│   │   └── checkpoints.db     # LangGraph checkpoints
│   ├── external/
│   │   ├── cultpass.db        # CultPass customer database
│   │   ├── cultpass_articles.jsonl  # Knowledge base (14 articles)
│   │   ├── cultpass_experiences.jsonl
│   │   └── cultpass_users.jsonl
│   └── models/
│       ├── cultpass.py        # CultPass data models
│       └── udahub.py          # UdaHub data models
├── .env.example               # Environment variables template
├── 01_external_db_setup.ipynb # Setup CultPass database
├── 02_core_db_setup.ipynb     # Setup UdaHub database
├── 03_agentic_app.ipynb       # Run the agentic system
├── test_workflow.py           # Test cases
├── utils.py                   # Utility functions
└── README.md                  # This file
```

## Requirements

- Python 3.13
- OpenAI API key

### Dependencies

```
fastmcp>=2.10.6
httpx>=0.28.1
ipykernel>=6.30.0
langchain>=0.3.27
langchain-core>=0.3.72
langchain-mcp-adapters>=0.1.9
langchain-openai>=0.3.28
langgraph-supervisor>=0.0.28
langgraph>=0.5.4
python-dotenv>=1.1.1
sqlalchemy>=2.0.41
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd starter
pip install -r ../requirements.txt
```

### 2. Configure Environment

Copy the example environment file and add your OpenAI API key:

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=your_actual_api_key_here
```

### 3. Setup Databases

Run the notebooks in order:

**Step 1: Setup External Database (CultPass)**

```bash
jupyter notebook 01_external_db_setup.ipynb
```

This creates the CultPass database with:
- Users
- Subscriptions
- Experiences
- Reservations

**Step 2: Setup Core Database (UdaHub)**

```bash
jupyter notebook 02_core_db_setup.ipynb
```

This creates the UdaHub database with:
- Accounts
- Users
- Tickets
- Knowledge base (14 articles covering diverse topics)

### 4. Run the System

**Option A: Using Jupyter Notebook**

```bash
jupyter notebook 03_agentic_app.ipynb
```

**Option B: Using Python Script**

```python
from agentic.workflow import orchestrator
from utils import chat_interface

# Start interactive chat
chat_interface(orchestrator, "ticket_001")
```

### 5. Run Tests

```bash
python test_workflow.py
```

## Features

### Multi-Agent Workflow

- **Automatic Classification**: Categorizes tickets into login, billing, subscription, reservation, technical, account, or general
- **Knowledge Retrieval**: Uses RAG with OpenAI embeddings to find relevant support articles
- **Database Operations**: Executes tools for user lookup, subscription checks, reservation management
- **Intelligent Escalation**: Escalates complex cases to human agents with detailed summaries
- **Memory Management**: 
  - Short-term: Thread-based conversation history using LangGraph checkpointing
  - Long-term: Persistent ticket history in database

### Available Tools

1. **get_user_info** - Lookup user details
2. **get_subscription_status** - Check subscription tier and status
3. **get_reservations** - Retrieve user reservations
4. **cancel_reservation** - Cancel a specific reservation
5. **check_account_status** - Verify if account is blocked
6. **request_refund** - Initiate refund process

### Knowledge Base

14 comprehensive articles covering:
- Event reservations
- Subscription management
- Login issues
- Payment and billing
- Account settings
- Technical troubleshooting
- Refund policies
- Accessibility features
- And more...

## Usage Examples

### Example 1: Simple Knowledge Query

```python
from langchain_core.messages import HumanMessage
from agentic.workflow import orchestrator

config = {"configurable": {"thread_id": "ticket_001"}}

state = {
    "messages": [HumanMessage(content="How do I reserve an event?")],
    "ticket_id": "ticket_001",
    "user_id": None,
    "classification": None,
    "knowledge_results": None,
    "tool_results": None,
    "confidence_score": 0.0,
    "next_agent": None,
    "escalation_needed": False,
    "resolution": None,
    "escalation_data": None
}

result = orchestrator.invoke(state, config=config)

# Get response
for msg in reversed(result["messages"]):
    if hasattr(msg, 'name') and msg.name == 'resolver':
        print(msg.content)
        break
```

### Example 2: User Lookup with Tools

```python
state = {
    "messages": [HumanMessage(content="Check my account status. User ID: f556c0")],
    "ticket_id": "ticket_002",
    # ... other fields
}

result = orchestrator.invoke(state, config={"configurable": {"thread_id": "ticket_002"}})
```

### Example 3: Blocked Account (Escalation)

```python
state = {
    "messages": [HumanMessage(content="My account is blocked. User ID: a4ab87")],
    "ticket_id": "ticket_003",
    # ... other fields
}

result = orchestrator.invoke(state, config={"configurable": {"thread_id": "ticket_003"}})

# Check if escalated
print(f"Escalated: {result['escalation_needed']}")
```

## Testing

The project includes comprehensive test cases:

1. **Login Issue** - Tests classification and knowledge retrieval
2. **Reservation Query** - Tests knowledge-based resolution
3. **Subscription Info** - Tests RAG with subscription articles
4. **Blocked Account** - Tests tool execution and escalation
5. **User Lookup** - Tests database tool integration

Run all tests:

```bash
python test_workflow.py
```

## Memory and State Management

### Short-term Memory (Session-based)

- Implemented using LangGraph's SQLite checkpointer
- Stores conversation history per thread_id
- Maintains agent state transitions
- Tracks tool invocations

### Long-term Memory (Persistent)

- Ticket history stored in UdaHub database
- User interaction patterns
- Resolved issue summaries
- Can be queried for similar past issues

## Logging and Observability

The system logs:
- Agent routing decisions
- Classification results
- Knowledge retrieval queries
- Tool invocations
- Confidence scores
- Escalation reasons

## Extending the System

### Adding New Agents

1. Create agent class in `agentic/agents/`
2. Add node function in `workflow.py`
3. Register with supervisor routing logic

### Adding New Tools

1. Implement tool function in `agentic/tools/database_tools.py`
2. Add to `AVAILABLE_TOOLS` dictionary
3. Update tool descriptions

### Adding Knowledge Articles

Add articles to `data/external/cultpass_articles.jsonl`:

```json
{"title": "Article Title", "content": "Article content...", "tags": "tag1, tag2"}
```

Then re-run `02_core_db_setup.ipynb` to update the knowledge base.

## Troubleshooting

### OpenAI API Errors

- Ensure `OPENAI_API_KEY` is set in `.env`
- Check API quota and billing

### Database Errors

- Re-run setup notebooks to recreate databases
- Check file paths in configuration

### Import Errors

- Ensure all dependencies are installed
- Check Python version (3.13 required)

## Performance Metrics

- **Response Time**: < 5 seconds for simple queries
- **Knowledge Retrieval Accuracy**: > 80%
- **Escalation Rate**: < 30% (target)

## License

This project is part of the UDA-Hub final project submission.

## Contact

For questions or issues, please refer to the project documentation.

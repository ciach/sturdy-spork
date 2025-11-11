# UDA-Hub Quick Start Guide

## Prerequisites

- Python 3.13 installed
- OpenAI API key

## Installation (5 minutes)

### 1. Install Dependencies

```bash
cd /home/c/Nauka/final-project
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
cd starter
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## Database Setup (10 minutes)

### 3. Run Setup Notebooks

**Option A: Using Jupyter**

```bash
# Start Jupyter
jupyter notebook

# Run these notebooks in order:
# 1. 01_external_db_setup.ipynb
# 2. 02_core_db_setup.ipynb
```

**Option B: Using Python**

```bash
# Convert notebooks to Python and run
jupyter nbconvert --to python 01_external_db_setup.ipynb
jupyter nbconvert --to python 02_core_db_setup.ipynb

python 01_external_db_setup.py
python 02_core_db_setup.py
```

This creates:
- `data/external/cultpass.db` - CultPass customer database
- `data/core/udahub.db` - UdaHub core database with 14 knowledge articles

## Run the System (2 minutes)

### 4. Test the Workflow

```bash
python test_workflow.py
```

Expected output:
```
================================================================================
UDA-HUB MULTI-AGENT WORKFLOW TEST SUITE
================================================================================

================================================================================
TEST CASE 1: Login Issue
================================================================================
...
✅ Login Issue: PASSED
✅ Reservation Query: PASSED
✅ Subscription Info: PASSED
✅ Blocked Account: PASSED
✅ User Lookup: PASSED

Total: 5/5 tests passed
```

### 5. Interactive Chat

**Option A: Jupyter Notebook**

```bash
jupyter notebook 03_agentic_app.ipynb
```

**Option B: Python Script**

```python
from agentic.workflow import orchestrator
from langchain_core.messages import HumanMessage

# Create a ticket
config = {"configurable": {"thread_id": "my_ticket_1"}}

state = {
    "messages": [HumanMessage(content="How do I reserve an event?")],
    "ticket_id": "my_ticket_1",
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

## Example Queries to Try

1. **Knowledge-based queries:**
   - "How do I reserve an event?"
   - "What's included in my subscription?"
   - "How do I cancel my subscription?"
   - "I can't log in to my account"

2. **Database operations (include user ID):**
   - "Check my account status. User ID: f556c0"
   - "Show my reservations. User ID: f556c0"
   - "What's my subscription tier? User ID: f556c0"

3. **Escalation scenarios:**
   - "My account is blocked. User ID: a4ab87"
   - "I need a refund for my premium event"

## Troubleshooting

### "OpenAI API key not set"
- Check `.env` file exists in `starter/` directory
- Verify `OPENAI_API_KEY=sk-...` is set correctly
- Restart Python kernel/terminal after editing `.env`

### "Database not found"
- Run the setup notebooks (01 and 02)
- Check `data/external/cultpass.db` exists
- Check `data/core/udahub.db` exists

### "Module not found" errors
- Ensure you're in the `starter/` directory
- Install all requirements: `pip install -r ../requirements.txt`
- Check Python version: `python --version` (should be 3.13)

### Import errors
- Make sure `__init__.py` files exist in:
  - `agentic/`
  - `agentic/agents/`
  - `agentic/tools/`
  - `data/`
  - `data/models/`

## System Architecture Overview

```
User Query → Supervisor → Classifier → Supervisor → Resolver/Tool → Supervisor → Response/Escalation
```

**Agents:**
1. **Supervisor** - Routes to appropriate agent
2. **Classifier** - Categorizes ticket
3. **Resolver** - Provides knowledge-based answers (RAG)
4. **Tool** - Executes database operations
5. **Escalation** - Handles complex cases

## Next Steps

- Read `README.md` for detailed documentation
- Review `agentic/design/architecture.md` for architecture details
- Check `agentic/design/RAG_implementation.md` for RAG details
- Explore test cases in `test_workflow.py`
- Customize agents in `agentic/agents/`
- Add more tools in `agentic/tools/database_tools.py`
- Add more knowledge articles in `data/external/cultpass_articles.jsonl`

## Support

For detailed information, see:
- `README.md` - Complete user guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `agentic/design/` - Architecture documentation

## Performance Notes

- First query may take 10-15 seconds (loading embeddings)
- Subsequent queries: 2-5 seconds
- Knowledge retrieval uses semantic search (FAISS)
- Fallback to keyword search if embeddings fail

## Success Indicators

✅ All 5 test cases pass
✅ Knowledge-based queries return relevant answers
✅ Database tools execute successfully
✅ Escalation works for blocked accounts
✅ Conversation history maintained per thread_id

Enjoy using UDA-Hub! 🚀

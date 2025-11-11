# UDA-Hub Setup Guide

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/ciach/sturdy-spork.git
cd sturdy-spork
```

### 2. Set Up Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cd starter
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 4. Initialize Databases
```bash
# Run the setup notebooks in order
jupyter notebook 01_external_db_setup.ipynb  # Sets up CultPass database
jupyter notebook 02_core_db_setup.ipynb      # Sets up UDA-Hub database
```

### 5. Test the Agentic System
```bash
jupyter notebook 03_agentic_app.ipynb
```

## Performance Notes

- **First query**: ~10-15s (initializes embeddings and builds cache)
- **Subsequent queries**: ~10-20s (uses cached embeddings)
- **Cache location**: `starter/data/core/faiss_cache_cultpass/`

## Architecture

### Multi-Agent System
- **Supervisor**: Routes requests to appropriate agents
- **Classifier**: Categorizes tickets and extracts entities
- **Resolver**: Provides knowledge-based responses using RAG
- **Tool Agent**: Executes database operations
- **Escalation**: Handles complex cases requiring human intervention

### Key Features
- RAG-based knowledge retrieval with FAISS vector store
- Three-tier memory system (state, session, long-term)
- Persistent customer history and personalization
- Lazy loading and caching for performance
- Loop detection to prevent infinite routing

### Memory System
The system implements comprehensive memory management:

1. **State Memory**: AgentState maintains context during workflow execution
2. **Session Memory**: SqliteSaver checkpointing persists conversations per thread_id
3. **Long-Term Memory**: MemoryManager stores interactions across sessions

See `starter/MEMORY_SYSTEM.md` for detailed documentation.

## Project Structure

```
starter/
├── agentic/
│   ├── agents/          # Agent implementations
│   ├── tools/           # Knowledge retrieval and database tools
│   ├── design/          # Architecture documentation
│   └── workflow.py      # LangGraph workflow definition
├── data/
│   ├── core/            # UDA-Hub database and checkpoints
│   ├── external/        # CultPass database and sample data
│   └── models/          # SQLAlchemy models
├── 01_external_db_setup.ipynb
├── 02_core_db_setup.ipynb
├── 03_agentic_app.ipynb
└── utils.py
```

## Important Notes

- **Do not commit** `.env` files or large database files
- **Database files** (`.db`, `.db-wal`, `.db-shm`) are gitignored
- **Vector store caches** are gitignored and regenerated on first use
- **Checkpoint database** is created automatically on first run

## Troubleshooting

### Slow Performance
- Ensure FAISS cache exists in `starter/data/core/faiss_cache_cultpass/`
- First query will be slower as it builds the cache
- Restart Jupyter kernel if changes to code aren't reflected

### Module Import Errors
- Verify virtual environment is activated
- Run `pip install -r requirements.txt` again
- Clear Python cache: `find . -type d -name "__pycache__" -exec rm -rf {} +`

### Recursion Errors
- The workflow has loop detection built-in
- If you see recursion errors, check the supervisor routing logic
- Increase recursion limit in config if needed: `{"configurable": {"recursion_limit": 50}}`

## Development

### Adding New Knowledge Articles
Add articles to the UDA-Hub database using the `02_core_db_setup.ipynb` notebook or directly via SQLAlchemy.

### Testing
```bash
cd starter
python test_orchestrator.py      # Test basic functionality
python test_performance.py       # Test performance improvements
python test_memory_system.py     # Test all three memory types
```

### Memory System Demo
```bash
jupyter notebook 04_memory_demo.ipynb  # Interactive memory demonstration
```

## License

See LICENSE file for details.

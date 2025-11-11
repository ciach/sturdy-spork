#!/usr/bin/env python
"""
Quick test script to verify the orchestrator works correctly.
Run this before using the notebook to ensure everything is set up properly.
"""

from langchain_core.messages import HumanMessage
from agentic.workflow import orchestrator

def test_orchestrator():
    """Test that the orchestrator can process a simple message."""
    print("Testing orchestrator...")
    print(f"Orchestrator type: {type(orchestrator)}")
    print(f"Checkpointer type: {type(orchestrator.checkpointer)}")
    print(f"Checkpointer has required methods: {hasattr(orchestrator.checkpointer, 'get_next_version') and hasattr(orchestrator.checkpointer, 'list')}")
    
    # Test with a simple query
    test_state = {
        "messages": [HumanMessage(content="Hello, I need help with my account")],
    }
    
    config = {
        "configurable": {
            "thread_id": "test-thread-1",
        }
    }
    
    print("\nInvoking orchestrator with test message...")
    try:
        result = orchestrator.invoke(test_state, config)
        print("✅ Test successful!")
        print(f"   Number of messages in result: {len(result['messages'])}")
        print(f"   Last message preview: {result['messages'][-1].content[:100]}...")
        
        # Test state retrieval
        print("\nTesting state retrieval...")
        current_state = orchestrator.get_state(config)
        print(f"✅ Current state retrieved successfully")
        print(f"   State has {len(current_state.values.get('messages', []))} messages")
        
        # Test state history
        print("\nTesting state history...")
        history = list(orchestrator.get_state_history(config))
        print(f"✅ State history retrieved successfully")
        print(f"   History has {len(history)} checkpoints")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_orchestrator()
    exit(0 if success else 1)

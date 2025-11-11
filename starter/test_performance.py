#!/usr/bin/env python
"""
Test performance improvements with lazy loading and caching.
"""

import time

def test_import_speed():
    """Test how fast the module imports."""
    print("=" * 60)
    print("TEST 1: Import Speed")
    print("=" * 60)
    
    start = time.time()
    from agentic.workflow import orchestrator
    elapsed = time.time() - start
    
    print(f"✅ Import time: {elapsed:.2f}s")
    print(f"   Orchestrator type: {type(orchestrator).__name__}")
    return elapsed < 5  # Should be under 5 seconds

def test_knowledge_retrieval():
    """Test knowledge retrieval with caching."""
    print("\n" + "=" * 60)
    print("TEST 2: Knowledge Retrieval (First Time - Builds Cache)")
    print("=" * 60)
    
    from agentic.tools.knowledge_retrieval import search_knowledge_base
    
    start = time.time()
    result = search_knowledge_base("How do I log in?", top_k=3)
    elapsed = time.time() - start
    
    print(f"✅ First search time: {elapsed:.2f}s")
    print(f"   Found {result.get('count', 0)} articles")
    print(f"   Method: {result.get('method', 'unknown')}")
    
    # Second search should be much faster (uses cache)
    print("\n" + "=" * 60)
    print("TEST 3: Knowledge Retrieval (Second Time - Uses Cache)")
    print("=" * 60)
    
    start = time.time()
    result2 = search_knowledge_base("How do I cancel my subscription?", top_k=3)
    elapsed2 = time.time() - start
    
    print(f"✅ Second search time: {elapsed2:.2f}s")
    print(f"   Found {result2.get('count', 0)} articles")
    print(f"   Speedup: {elapsed/elapsed2:.1f}x faster")
    
    return elapsed2 < 2  # Second search should be under 2 seconds

def test_agent_initialization():
    """Test individual agent initialization."""
    print("\n" + "=" * 60)
    print("TEST 4: Agent Initialization")
    print("=" * 60)
    
    start = time.time()
    from agentic.agents.classifier import ClassifierAgent
    from agentic.agents.resolver import ResolverAgent
    from agentic.agents.tool_agent import ToolAgent
    elapsed = time.time() - start
    
    print(f"✅ Agent imports: {elapsed:.2f}s")
    
    # Test classifier
    start = time.time()
    classifier = ClassifierAgent()
    result = classifier.classify("I can't log in")
    elapsed = time.time() - start
    
    print(f"✅ Classifier test: {elapsed:.2f}s")
    print(f"   Category: {result.get('classification', {}).get('category', 'N/A')}")
    
    return True

if __name__ == "__main__":
    print("\n🚀 Performance Test Suite\n")
    
    results = []
    
    try:
        results.append(("Import Speed", test_import_speed()))
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        results.append(("Import Speed", False))
    
    try:
        results.append(("Knowledge Retrieval", test_knowledge_retrieval()))
    except Exception as e:
        print(f"❌ Knowledge retrieval test failed: {e}")
        results.append(("Knowledge Retrieval", False))
    
    try:
        results.append(("Agent Initialization", test_agent_initialization()))
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        results.append(("Agent Initialization", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    exit(0 if all_passed else 1)

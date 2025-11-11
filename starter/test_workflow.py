"""
Test cases for UDA-Hub multi-agent workflow.
"""

import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

from agentic.workflow import orchestrator


def test_login_issue():
    """Test Case 1: Login issue ticket"""
    print("\n" + "="*80)
    print("TEST CASE 1: Login Issue")
    print("="*80)
    
    ticket_text = "I can't log in to my Cultpass account. My user ID is a4ab87."
    
    config = {"configurable": {"thread_id": "test_login_1"}}
    
    initial_state = {
        "messages": [HumanMessage(content=ticket_text)],
        "ticket_id": "test_login_1",
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
    
    result = orchestrator.invoke(initial_state, config=config)
    
    print(f"\nTicket: {ticket_text}")
    print(f"\nClassification: {result.get('classification', {}).get('classification', {}).get('category')}")
    print(f"Confidence: {result.get('confidence_score', 0):.2f}")
    print(f"\nFinal Response:")
    
    # Get last AI message
    for msg in reversed(result["messages"]):
        if hasattr(msg, 'name') and msg.name in ['resolver', 'escalation_agent']:
            print(msg.content)
            break
    
    print(f"\nEscalated: {result.get('escalation_needed', False)}")
    
    return result


def test_reservation_query():
    """Test Case 2: Reservation query"""
    print("\n" + "="*80)
    print("TEST CASE 2: Reservation Query")
    print("="*80)
    
    ticket_text = "How do I reserve a spot for an event?"
    
    config = {"configurable": {"thread_id": "test_reservation_1"}}
    
    initial_state = {
        "messages": [HumanMessage(content=ticket_text)],
        "ticket_id": "test_reservation_1",
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
    
    result = orchestrator.invoke(initial_state, config=config)
    
    print(f"\nTicket: {ticket_text}")
    print(f"\nClassification: {result.get('classification', {}).get('classification', {}).get('category')}")
    print(f"Confidence: {result.get('confidence_score', 0):.2f}")
    print(f"\nFinal Response:")
    
    for msg in reversed(result["messages"]):
        if hasattr(msg, 'name') and msg.name in ['resolver', 'escalation_agent']:
            print(msg.content)
            break
    
    print(f"\nEscalated: {result.get('escalation_needed', False)}")
    
    return result


def test_subscription_info():
    """Test Case 3: Subscription information"""
    print("\n" + "="*80)
    print("TEST CASE 3: Subscription Information")
    print("="*80)
    
    ticket_text = "What's included in my CultPass subscription?"
    
    config = {"configurable": {"thread_id": "test_subscription_1"}}
    
    initial_state = {
        "messages": [HumanMessage(content=ticket_text)],
        "ticket_id": "test_subscription_1",
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
    
    result = orchestrator.invoke(initial_state, config=config)
    
    print(f"\nTicket: {ticket_text}")
    print(f"\nClassification: {result.get('classification', {}).get('classification', {}).get('category')}")
    print(f"Confidence: {result.get('confidence_score', 0):.2f}")
    print(f"\nFinal Response:")
    
    for msg in reversed(result["messages"]):
        if hasattr(msg, 'name') and msg.name in ['resolver', 'escalation_agent']:
            print(msg.content)
            break
    
    print(f"\nEscalated: {result.get('escalation_needed', False)}")
    
    return result


def test_account_blocked():
    """Test Case 4: Blocked account (should escalate)"""
    print("\n" + "="*80)
    print("TEST CASE 4: Blocked Account")
    print("="*80)
    
    ticket_text = "My account seems to be blocked. User ID: a4ab87"
    
    config = {"configurable": {"thread_id": "test_blocked_1"}}
    
    initial_state = {
        "messages": [HumanMessage(content=ticket_text)],
        "ticket_id": "test_blocked_1",
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
    
    result = orchestrator.invoke(initial_state, config=config)
    
    print(f"\nTicket: {ticket_text}")
    print(f"\nClassification: {result.get('classification', {}).get('classification', {}).get('category')}")
    print(f"Confidence: {result.get('confidence_score', 0):.2f}")
    print(f"\nFinal Response:")
    
    for msg in reversed(result["messages"]):
        if hasattr(msg, 'name') and msg.name in ['resolver', 'escalation_agent']:
            print(msg.content)
            break
    
    print(f"\nEscalated: {result.get('escalation_needed', False)}")
    
    return result


def test_user_lookup():
    """Test Case 5: User lookup with tools"""
    print("\n" + "="*80)
    print("TEST CASE 5: User Lookup with Tools")
    print("="*80)
    
    ticket_text = "Can you check my account status? My user ID is f556c0"
    
    config = {"configurable": {"thread_id": "test_lookup_1"}}
    
    initial_state = {
        "messages": [HumanMessage(content=ticket_text)],
        "ticket_id": "test_lookup_1",
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
    
    result = orchestrator.invoke(initial_state, config=config)
    
    print(f"\nTicket: {ticket_text}")
    print(f"\nClassification: {result.get('classification', {}).get('classification', {}).get('category')}")
    print(f"Tool Results: {len(result.get('tool_results', []))} tools executed")
    print(f"Confidence: {result.get('confidence_score', 0):.2f}")
    print(f"\nFinal Response:")
    
    for msg in reversed(result["messages"]):
        if hasattr(msg, 'name') and msg.name in ['resolver', 'escalation_agent']:
            print(msg.content)
            break
    
    print(f"\nEscalated: {result.get('escalation_needed', False)}")
    
    return result


def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*80)
    print("UDA-HUB MULTI-AGENT WORKFLOW TEST SUITE")
    print("="*80)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set in environment")
        print("Please set your OpenAI API key in .env file")
        return
    
    tests = [
        ("Login Issue", test_login_issue),
        ("Reservation Query", test_reservation_query),
        ("Subscription Info", test_subscription_info),
        ("Blocked Account", test_account_blocked),
        ("User Lookup", test_user_lookup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "PASSED", result))
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            results.append((test_name, "FAILED", str(e)))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, status, _ in results:
        icon = "✅" if status == "PASSED" else "❌"
        print(f"{icon} {test_name}: {status}")
    
    passed = sum(1 for _, status, _ in results if status == "PASSED")
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    run_all_tests()

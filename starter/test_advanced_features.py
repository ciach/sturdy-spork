"""
Test cases for advanced features:
1. Advanced Knowledge Retrieval with ChromaDB
2. Sentiment Analysis
3. FastMCP Tools
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))


def test_advanced_knowledge_retrieval():
    """Test Case 1: Advanced Knowledge Retrieval with ChromaDB"""
    print("\n" + "="*80)
    print("TEST CASE 1: Advanced Knowledge Retrieval (ChromaDB + Hybrid Search)")
    print("="*80)
    
    from agentic.tools.advanced_knowledge_retrieval import search_knowledge_advanced
    
    # Test semantic search
    print("\n--- Test 1.1: Semantic Search ---")
    query = "I'm having trouble logging into my account"
    result = search_knowledge_advanced(query, top_k=3, use_hybrid=True)
    
    print(f"Query: {query}")
    print(f"Method: {result.get('method')}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print(f"Articles found: {result.get('count', 0)}")
    
    if result.get("success") and result.get("articles"):
        for i, article in enumerate(result["articles"][:3], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Relevance: {article['relevance_score']:.2f}")
            if "keyword_boost" in article:
                print(f"   Keyword Boost: +{article['keyword_boost']:.2f}")
    
    # Test category filtering
    print("\n--- Test 1.2: Category-Filtered Search ---")
    query = "payment issues"
    result = search_knowledge_advanced(query, top_k=2, category="billing")
    
    print(f"Query: {query}")
    print(f"Category Filter: billing")
    print(f"Articles found: {result.get('count', 0)}")
    
    if result.get("success") and result.get("articles"):
        for article in result["articles"]:
            print(f"- {article['title']} (Category: {article.get('category', 'N/A')})")
    
    return result.get("success", False)


def test_sentiment_analysis():
    """Test Case 2: Sentiment Analysis"""
    print("\n" + "="*80)
    print("TEST CASE 2: Sentiment Analysis for Ticket Prioritization")
    print("="*80)
    
    from agentic.agents.sentiment_analyzer import SentimentAnalyzer
    
    analyzer = SentimentAnalyzer()
    
    # Test 1: Frustrated customer
    print("\n--- Test 2.1: Frustrated Customer ---")
    ticket = "This is RIDICULOUS! I've been trying to log in for 3 days and STILL can't access my account. This is the worst service ever!!!"
    
    result = analyzer.analyze(ticket)
    
    print(f"Ticket: {ticket[:100]}...")
    print(f"Sentiment: {result.get('sentiment')}")
    print(f"Emotion: {result.get('emotion')}")
    print(f"Urgency Score: {result.get('urgency_score', 0):.2f}")
    print(f"Frustration Level: {result.get('frustration_level', 0):.2f}")
    print(f"Priority Boost: {result.get('priority_boost', 0):.2f}")
    print(f"Escalation Recommended: {result.get('escalation_recommended', False)}")
    print(f"Key Indicators: {', '.join(result.get('key_indicators', [])[:5])}")
    
    # Test 2: Urgent but calm
    print("\n--- Test 2.2: Urgent but Calm ---")
    ticket = "I need to cancel my reservation urgently as I can't attend the event tomorrow. User ID: f556c0"
    
    result = analyzer.analyze(ticket)
    
    print(f"Ticket: {ticket}")
    print(f"Sentiment: {result.get('sentiment')}")
    print(f"Emotion: {result.get('emotion')}")
    print(f"Urgency Score: {result.get('urgency_score', 0):.2f}")
    print(f"Frustration Level: {result.get('frustration_level', 0):.2f}")
    
    # Test 3: Neutral inquiry
    print("\n--- Test 2.3: Neutral Inquiry ---")
    ticket = "What's included in the Premium subscription?"
    
    result = analyzer.analyze(ticket)
    
    print(f"Ticket: {ticket}")
    print(f"Sentiment: {result.get('sentiment')}")
    print(f"Emotion: {result.get('emotion')}")
    print(f"Urgency Score: {result.get('urgency_score', 0):.2f}")
    
    # Test urgency adjustment
    print("\n--- Test 2.4: Urgency Adjustment ---")
    base_urgency = "medium"
    frustrated_sentiment = {
        "urgency_score": 0.8,
        "frustration_level": 0.7,
        "emotion": "angry"
    }
    
    adjusted = analyzer.adjust_urgency(base_urgency, frustrated_sentiment)
    print(f"Base Urgency: {base_urgency}")
    print(f"Adjusted Urgency: {adjusted}")
    
    return True


def test_mcp_tools():
    """Test Case 3: FastMCP Tools"""
    print("\n" + "="*80)
    print("TEST CASE 3: FastMCP Support Tools")
    print("="*80)
    
    from agentic.tools.mcp_server import (
        lookup_user,
        check_user_eligibility,
        get_subscription_details,
        manage_reservation,
        diagnose_account_issue,
        generate_account_summary,
        list_mcp_tools
    )
    
    # List available tools
    print("\n--- Available MCP Tools ---")
    tools = list_mcp_tools()
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool}")
    
    # Test 1: Lookup user
    print("\n--- Test 3.1: Lookup User ---")
    user_id = "f556c0"
    result = lookup_user(user_id)
    
    print(f"User ID: {user_id}")
    if result.get("success"):
        print(f"Account Status: {result.get('account_status')}")
        print(f"Reservations: {result.get('reservations_count')}")
        if result.get("subscription"):
            print(f"Subscription Tier: {result['subscription'].get('tier')}")
    
    # Test 2: Check eligibility
    print("\n--- Test 3.2: Check User Eligibility ---")
    result = check_user_eligibility(user_id, "reserve_event")
    
    print(f"Action: reserve_event")
    print(f"Eligible: {result.get('eligible')}")
    print(f"Reason: {result.get('reason')}")
    if result.get("monthly_quota"):
        print(f"Monthly Quota: {result.get('monthly_quota')}")
    
    # Test 3: Subscription details
    print("\n--- Test 3.3: Get Subscription Details ---")
    result = get_subscription_details(user_id)
    
    if result.get("success"):
        print(f"Tier: {result.get('tier')}")
        print(f"Status: {result.get('status')}")
        print(f"Quota: {result.get('used_quota')}/{result.get('monthly_quota')}")
        print(f"Remaining: {result.get('remaining_quota')}")
        print(f"Usage: {result.get('usage_percentage', 0):.1f}%")
    
    # Test 4: Diagnose account
    print("\n--- Test 3.4: Diagnose Account Issues ---")
    result = diagnose_account_issue(user_id)
    
    print(f"Account Healthy: {result.get('account_healthy')}")
    print(f"Overall Status: {result.get('overall_status')}")
    print(f"Issues Found: {result.get('issues_found')}")
    
    if result.get("issues"):
        for issue in result["issues"]:
            print(f"  - {issue['type']}: {issue['description']} (Severity: {issue['severity']})")
    
    if result.get("recommendations"):
        print("Recommendations:")
        for rec in result["recommendations"]:
            print(f"  - {rec['action']}: {rec['description']}")
    
    # Test 5: Account summary
    print("\n--- Test 3.5: Generate Account Summary ---")
    result = generate_account_summary(user_id)
    
    if result.get("success"):
        print(f"Name: {result['account_overview']['name']}")
        print(f"Status: {result['account_overview']['status']}")
        print(f"Subscription: {result['subscription_overview']['tier']} ({result['subscription_overview']['status']})")
        print(f"Total Reservations: {result['activity_overview']['total_reservations']}")
        if result.get("quick_actions"):
            print(f"Quick Actions: {', '.join(result['quick_actions'])}")
    
    return True


def test_enhanced_classifier():
    """Test Case 4: Enhanced Classifier with Sentiment"""
    print("\n" + "="*80)
    print("TEST CASE 4: Enhanced Classifier (Classification + Sentiment)")
    print("="*80)
    
    from agentic.agents.enhanced_classifier import EnhancedClassifier
    
    classifier = EnhancedClassifier()
    
    # Test with frustrated ticket
    print("\n--- Test 4.1: Frustrated Login Issue ---")
    ticket = "I CAN'T LOG IN AGAIN!!! This is the third time this week. My user ID is a4ab87. PLEASE FIX THIS IMMEDIATELY!"
    
    result = classifier.classify_with_sentiment(ticket)
    
    if result.get("success"):
        classification = result["classification"]
        print(f"Ticket: {ticket[:80]}...")
        print(f"\nClassification:")
        print(f"  Category: {classification.get('category')}")
        print(f"  Original Urgency: {classification.get('original_urgency')}")
        print(f"  Adjusted Urgency: {classification.get('urgency')}")
        print(f"  Urgency Adjusted: {classification.get('urgency_adjusted')}")
        print(f"  Confidence: {classification.get('confidence', 0):.2f}")
        
        if classification.get("sentiment"):
            sentiment = classification["sentiment"]
            print(f"\nSentiment Analysis:")
            print(f"  Emotion: {sentiment.get('emotion')}")
            print(f"  Frustration: {sentiment.get('frustration_level', 0):.2f}")
            print(f"  Urgency Score: {sentiment.get('urgency_score', 0):.2f}")
        
        if classification.get("response_guidelines"):
            guidelines = classification["response_guidelines"]
            print(f"\nResponse Guidelines:")
            print(f"  Tone: {guidelines.get('tone')}")
            print(f"  Priority: {guidelines.get('priority')}")
            print(f"  Empathy Level: {guidelines.get('empathy_level')}")
    
    return result.get("success", False)


def run_all_advanced_tests():
    """Run all advanced feature tests"""
    print("\n" + "="*80)
    print("ADVANCED FEATURES TEST SUITE")
    print("="*80)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set in environment")
        print("Some tests may fail without the API key")
    
    tests = [
        ("Advanced Knowledge Retrieval", test_advanced_knowledge_retrieval),
        ("Sentiment Analysis", test_sentiment_analysis),
        ("FastMCP Tools", test_mcp_tools),
        ("Enhanced Classifier", test_enhanced_classifier)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            success = test_func()
            status = "PASSED" if success else "COMPLETED"
            results.append((test_name, status))
            print(f"\n✅ {test_name}: {status}")
        except Exception as e:
            print(f"\n❌ {test_name} failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "FAILED"))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, status in results:
        icon = "✅" if status in ["PASSED", "COMPLETED"] else "❌"
        print(f"{icon} {test_name}: {status}")
    
    passed = sum(1 for _, status in results if status in ["PASSED", "COMPLETED"])
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed/completed")


if __name__ == "__main__":
    run_all_advanced_tests()

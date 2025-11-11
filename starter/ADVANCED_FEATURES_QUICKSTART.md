# Advanced Features Quick Start

## Installation

```bash
# Install new dependencies
pip install chromadb>=0.4.22 langchain-community>=0.3.0
```

## 1. Advanced Knowledge Retrieval (ChromaDB)

### Basic Usage

```python
from agentic.tools.advanced_knowledge_retrieval import search_knowledge_advanced

# Simple semantic search
results = search_knowledge_advanced("How do I cancel my subscription?")

# Hybrid search (semantic + keyword)
results = search_knowledge_advanced(
    query="payment issues",
    top_k=3,
    use_hybrid=True
)

# Category-filtered search
results = search_knowledge_advanced(
    query="login problems",
    category="login",
    top_k=3
)
```

### Response Format

```json
{
  "success": true,
  "method": "chromadb_hybrid",
  "confidence": 0.89,
  "count": 3,
  "articles": [
    {
      "title": "Article Title",
      "content": "...",
      "relevance_score": 0.92,
      "keyword_boost": 0.15,
      "category": "login"
    }
  ]
}
```

## 2. Sentiment Analysis

### Basic Usage

```python
from agentic.agents.sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()

# Analyze ticket sentiment
result = analyzer.analyze("I CAN'T LOG IN!!! This is urgent!")

print(f"Emotion: {result['emotion']}")
print(f"Urgency: {result['urgency_score']:.2f}")
print(f"Frustration: {result['frustration_level']:.2f}")
```

### Enhanced Classifier (Recommended)

```python
from agentic.agents.enhanced_classifier import EnhancedClassifier

classifier = EnhancedClassifier()

# Get classification + sentiment in one call
result = classifier.classify_with_sentiment(ticket_text)

classification = result["classification"]
print(f"Category: {classification['category']}")
print(f"Urgency: {classification['urgency']}")
print(f"Emotion: {classification['sentiment']['emotion']}")
print(f"Tone: {classification['response_guidelines']['tone']}")
```

### Response Format

```json
{
  "sentiment": "very_negative",
  "emotion": "angry",
  "urgency_score": 0.85,
  "frustration_level": 0.90,
  "priority_boost": 0.45,
  "escalation_recommended": true,
  "recommended_tone": "empathetic and apologetic",
  "key_indicators": ["can't access", "multiple times", "urgent"]
}
```

## 3. FastMCP Tools

### Import Tools

```python
from agentic.tools.mcp_server import (
    lookup_user,
    check_user_eligibility,
    get_subscription_details,
    manage_reservation,
    diagnose_account_issue,
    generate_account_summary
)
```

### Common Operations

#### User Lookup

```python
# Get complete user info
user_info = lookup_user(user_id="f556c0")

print(f"Status: {user_info['account_status']}")
print(f"Reservations: {user_info['reservations_count']}")
```

#### Check Eligibility

```python
# Check if user can perform action
result = check_user_eligibility(
    user_id="f556c0",
    action="reserve_event"
)

if result["eligible"]:
    print(f"User can {action}")
else:
    print(f"Reason: {result['reason']}")
```

#### Subscription Details

```python
# Get usage statistics
details = get_subscription_details(user_id="f556c0")

print(f"Tier: {details['tier']}")
print(f"Used: {details['used_quota']}/{details['monthly_quota']}")
print(f"Remaining: {details['remaining_quota']}")
```

#### Diagnose Issues

```python
# Automated diagnostics
diagnosis = diagnose_account_issue(user_id="a4ab87")

print(f"Healthy: {diagnosis['account_healthy']}")
print(f"Status: {diagnosis['overall_status']}")

for issue in diagnosis['issues']:
    print(f"- {issue['type']}: {issue['description']}")

for rec in diagnosis['recommendations']:
    print(f"→ {rec['action']}: {rec['description']}")
```

#### Account Summary

```python
# Complete overview
summary = generate_account_summary(user_id="f556c0")

print(f"Name: {summary['account_overview']['name']}")
print(f"Tier: {summary['subscription_overview']['tier']}")
print(f"Reservations: {summary['activity_overview']['total_reservations']}")
```

## Testing

### Run All Advanced Feature Tests

```bash
python test_advanced_features.py
```

### Run Individual Tests

```python
# Test knowledge retrieval
from test_advanced_features import test_advanced_knowledge_retrieval
test_advanced_knowledge_retrieval()

# Test sentiment analysis
from test_advanced_features import test_sentiment_analysis
test_sentiment_analysis()

# Test MCP tools
from test_advanced_features import test_mcp_tools
test_mcp_tools()
```

## Integration Examples

### Example 1: Enhanced Ticket Processing

```python
from agentic.agents.enhanced_classifier import EnhancedClassifier
from agentic.tools.advanced_knowledge_retrieval import search_knowledge_advanced

# Classify with sentiment
classifier = EnhancedClassifier()
result = classifier.classify_with_sentiment(ticket_text)

classification = result["classification"]
category = classification["category"]
urgency = classification["urgency"]

# Search knowledge base
kb_results = search_knowledge_advanced(
    query=ticket_text,
    category=category,
    use_hybrid=True
)

# Use response guidelines
guidelines = classification["response_guidelines"]
tone = guidelines["tone"]
```

### Example 2: Account Issue Resolution

```python
from agentic.tools.mcp_server import (
    diagnose_account_issue,
    lookup_user,
    generate_account_summary
)

# Diagnose
diagnosis = diagnose_account_issue(user_id)

if not diagnosis["account_healthy"]:
    # Get full context
    summary = generate_account_summary(user_id)
    
    # Take action based on recommendations
    for rec in diagnosis["recommendations"]:
        if rec["priority"] == "high":
            # Execute high-priority action
            print(f"Action: {rec['action']}")
```

### Example 3: Sentiment-Based Routing

```python
from agentic.agents.sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
sentiment = analyzer.analyze(ticket_text)

# Route based on sentiment
if sentiment["frustration_level"] > 0.7:
    # Escalate frustrated customers
    escalate_to_human(ticket)
elif sentiment["urgency_score"] > 0.8:
    # Prioritize urgent tickets
    prioritize_ticket(ticket)
else:
    # Normal processing
    process_ticket(ticket)
```

## Performance Tips

### Knowledge Retrieval
- First query takes 2-3s (loads embeddings)
- Subsequent queries: 0.5-1s
- Use category filters to improve speed
- Hybrid search adds ~100ms but improves accuracy

### Sentiment Analysis
- Rule-based: <100ms (use for most tickets)
- LLM-based: 1-2s (only for complex cases)
- System automatically chooses best method

### MCP Tools
- Each tool: 50-200ms
- Can be chained for complex operations
- Use `diagnose_account_issue` for automated checks

## Troubleshooting

### ChromaDB Issues

```python
# Check if ChromaDB is working
from agentic.tools.advanced_knowledge_retrieval import get_advanced_retriever

retriever = get_advanced_retriever()
# Should print: "✅ Loaded existing ChromaDB collection"
```

### Sentiment Analysis Not Working

```python
# Test sentiment analyzer
from agentic.agents.sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
result = analyzer.analyze("test")

if result.get("success"):
    print("✅ Sentiment analyzer working")
else:
    print(f"❌ Error: {result.get('error')}")
```

### MCP Tools Not Available

```python
# Check MCP tools
from agentic.tools.mcp_server import list_mcp_tools

tools = list_mcp_tools()
print(f"Available tools: {len(tools)}")
# Should show 8 tools
```

## Next Steps

1. Read `ADVANCED_FEATURES.md` for detailed documentation
2. Run `test_advanced_features.py` to verify installation
3. Try examples above with your own data
4. Integrate into your workflow

## Quick Reference

| Feature | File | Key Function |
|---------|------|--------------|
| Advanced Search | `advanced_knowledge_retrieval.py` | `search_knowledge_advanced()` |
| Sentiment | `sentiment_analyzer.py` | `SentimentAnalyzer.analyze()` |
| Enhanced Classifier | `enhanced_classifier.py` | `EnhancedClassifier.classify_with_sentiment()` |
| MCP Tools | `mcp_server.py` | 8 specialized tools |

Happy coding! 🚀

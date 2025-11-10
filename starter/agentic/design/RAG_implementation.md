# RAG (Retrieval-Augmented Generation) Implementation

## Overview

The UDA-Hub system uses RAG to provide accurate, knowledge-based responses to customer support tickets. This document explains how the RAG system works.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│  Classifier Agent                   │
│  - Extracts intent and entities     │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Resolver Agent                     │
│  - Initiates knowledge search       │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Knowledge Retriever                │
│  1. Embed query                     │
│  2. Semantic search in vector store │
│  3. Return top-k articles           │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Response Generation                │
│  - LLM generates response using     │
│    retrieved articles as context    │
└─────────────┬───────────────────────┘
              │
              ▼
         Final Response
```

## Components

### 1. Embedding Model

**Model**: OpenAI `text-embedding-3-small`

**Purpose**: Convert text into dense vector representations for semantic search

**Configuration**:
```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
```

**Dimensions**: 1536 (default for text-embedding-3-small)

### 2. Vector Store

**Implementation**: FAISS (Facebook AI Similarity Search)

**Purpose**: Efficient similarity search over embedded documents

**Initialization**:
```python
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Create documents
documents = []
for article in knowledge_articles:
    text = f"Title: {article['title']}\n\nContent: {article['content']}\n\nTags: {article['tags']}"
    doc = Document(
        page_content=text,
        metadata={
            "article_id": article["article_id"],
            "title": article["title"],
            "tags": article["tags"]
        }
    )
    documents.append(doc)

# Create vector store
vector_store = FAISS.from_documents(documents, embeddings)
```

**Search Method**: L2 distance (Euclidean distance)

### 3. Document Preparation

Each knowledge article is formatted as:

```
Title: [Article Title]

Content: [Article Content]

Tags: [Comma-separated tags]
```

This format ensures:
- Title is weighted in semantic search
- Full content is available for context
- Tags provide additional keyword signals

### 4. Retrieval Process

**Step 1: Query Embedding**
```python
query = "How do I reserve an event?"
query_vector = embeddings.embed_query(query)
```

**Step 2: Similarity Search**
```python
results = vector_store.similarity_search_with_score(query, k=3)
```

**Parameters**:
- `k=3`: Return top 3 most relevant articles
- Returns: List of (Document, score) tuples

**Step 3: Score Conversion**
```python
# FAISS returns L2 distance (lower is better)
# Convert to similarity score (higher is better)
similarity = 1 / (1 + distance)
```

### 5. Response Generation

**Model**: GPT-4

**System Prompt**:
```
You are a helpful customer support agent for CultPass.

Your role is to provide accurate, friendly responses based on the knowledge base articles provided.

Guidelines:
1. Base your response ONLY on the provided knowledge articles
2. Be concise but complete
3. Use a friendly, professional tone
4. If the articles don't contain enough information, acknowledge this
5. Include specific steps when applicable
6. Reference relevant policies when needed
```

**Context Construction**:
```python
articles_text = "\n\n---\n\n".join([
    f"Article: {article['title']}\n{article['content']}"
    for article in retrieved_articles
])

user_message = f"""
Customer Question: {query}

Relevant Knowledge Articles:
{articles_text}

Provide a helpful response based on the articles above.
"""
```

**Generation**:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0.3)
response = llm.invoke([
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_message)
])
```

## Confidence Scoring

The system calculates confidence based on:

1. **Retrieval Confidence**: Average similarity score of retrieved articles
2. **Classification Confidence**: Confidence from the classifier agent
3. **Combined Confidence**: Average of both

```python
retrieval_confidence = sum(article['relevance_score'] for article in articles) / len(articles)
classification_confidence = classification.get('confidence', 0.5)
overall_confidence = (retrieval_confidence + classification_confidence) / 2
```

**Thresholds**:
- **High confidence (> 0.8)**: Provide resolution directly
- **Medium confidence (0.5-0.8)**: Provide resolution with disclaimer
- **Low confidence (< 0.5)**: Escalate to human agent

## Fallback Mechanism

If embeddings are not available (e.g., API issues), the system falls back to keyword-based search:

```python
def _keyword_search(query: str, top_k: int = 3):
    query_lower = query.lower()
    scored_articles = []
    
    for article in all_articles:
        score = 0
        text = f"{article.title} {article.content} {article.tags}".lower()
        
        # Count keyword matches
        for word in query_lower.split():
            if len(word) > 2:
                score += text.count(word)
        
        if score > 0:
            scored_articles.append({
                "article": article,
                "relevance_score": min(score / 10, 1.0)
            })
    
    # Sort by score and return top_k
    scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored_articles[:top_k]
```

## Performance Optimization

### 1. Vector Store Caching

The vector store is initialized once and reused:

```python
_retriever = None

def get_retriever(account_id: str = "cultpass"):
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever(account_id)
    return _retriever
```

### 2. Batch Processing

For multiple queries, embeddings can be batched:

```python
queries = ["query1", "query2", "query3"]
query_vectors = embeddings.embed_documents(queries)
```

### 3. Index Optimization

FAISS supports various index types for different use cases:
- **Flat**: Exact search (current implementation)
- **IVF**: Faster search with slight accuracy trade-off
- **HNSW**: Hierarchical navigable small world graphs

## Evaluation Metrics

### Retrieval Quality

1. **Precision@k**: Percentage of retrieved articles that are relevant
2. **Recall@k**: Percentage of relevant articles that are retrieved
3. **MRR (Mean Reciprocal Rank)**: Average of reciprocal ranks of first relevant result

### Response Quality

1. **Faithfulness**: Response is grounded in retrieved articles
2. **Relevance**: Response addresses the user's question
3. **Completeness**: Response provides sufficient information

## Example Workflow

**Input**: "How do I cancel my subscription?"

**Step 1 - Embedding**:
```
Query vector: [0.023, -0.145, 0.089, ..., 0.234] (1536 dimensions)
```

**Step 2 - Retrieval**:
```
Top 3 Articles:
1. "How to Cancel or Pause a Subscription" (similarity: 0.92)
2. "What's Included in a CultPass Subscription" (similarity: 0.67)
3. "Refund Policy and Process" (similarity: 0.58)
```

**Step 3 - Generation**:
```
Input to LLM:
- System: [Support agent instructions]
- User: Customer Question + 3 retrieved articles

Output:
"You can cancel or pause your subscription at any time via the 'My Account' 
section in the CultPass app. Cancellation takes effect at the end of your 
billing cycle. To cancel:
1. Open the CultPass app
2. Go to 'My Account' > 'Manage Plan'
3. Select 'Cancel Subscription'
4. Confirm your choice

Please note that subscription fees are non-refundable once charged."
```

**Step 4 - Confidence**:
```
Retrieval confidence: 0.72
Classification confidence: 0.85
Overall confidence: 0.79 (Medium-High)
Decision: Provide resolution
```

## Future Improvements

1. **Hybrid Search**: Combine semantic and keyword search
2. **Re-ranking**: Use cross-encoder for better relevance
3. **Query Expansion**: Expand queries with synonyms
4. **Feedback Loop**: Learn from user satisfaction
5. **Multi-lingual Support**: Support multiple languages
6. **Contextual Embeddings**: Fine-tune embeddings on domain data

## References

- [LangChain RAG Documentation](https://python.langchain.com/docs/use_cases/question_answering/)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

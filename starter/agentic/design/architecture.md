# UDA-Hub Multi-Agent Architecture Design

## Overview

UDA-Hub is a Universal Decision Agent system designed to intelligently process customer support tickets using a multi-agent architecture built with LangGraph. The system employs a **Supervisor Pattern** where a central supervisor agent coordinates specialized agents to handle different aspects of ticket resolution.

## Architecture Pattern

**Pattern Type:** Hierarchical Supervisor Pattern

The supervisor pattern was chosen because:
- Clear separation of concerns with specialized agents
- Centralized decision-making for routing
- Easy to extend with new specialized agents
- Maintains conversation context across agent transitions
- Supports escalation workflows naturally

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        TICKET INPUT                              │
│              (Text + Metadata + Thread ID)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SUPERVISOR AGENT                              │
│  - Analyzes ticket content and metadata                         │
│  - Routes to appropriate specialized agent                       │
│  - Monitors progress and decides next steps                      │
│  - Handles escalation decisions                                  │
└─────┬───────────────┬──────────────┬──────────────┬─────────────┘
      │               │              │              │
      ▼               ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│CLASSIFIER│   │ RESOLVER │   │   TOOL   │   │ESCALATION│
│  AGENT   │   │  AGENT   │   │  AGENT   │   │  AGENT   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
      │               │              │              │
      │               │              │              │
      ▼               ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         TOOLS LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Knowledge   │  │  User Lookup │  │ Subscription │          │
│  │  Retrieval   │  │     Tool     │  │  Management  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Reservation  │  │   Account    │  │   Refund     │          │
│  │  Management  │  │    Status    │  │   Request    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  UdaHub DB   │  │ CultPass DB  │                             │
│  │  (Core)      │  │ (External)   │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY SYSTEM                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Short-term Memory (Session/Thread-based)         │           │
│  │ - Conversation history                           │           │
│  │ - Agent state transitions                        │           │
│  │ - Tool invocations                               │           │
│  └──────────────────────────────────────────────────┘           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Long-term Memory (Persistent)                    │           │
│  │ - Resolved ticket history                        │           │
│  │ - User preferences                               │           │
│  │ - Common issue patterns                          │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Specifications

### 1. Supervisor Agent

**Role:** Central coordinator and decision maker

**Responsibilities:**
- Receive incoming tickets
- Analyze ticket content and metadata
- Route to appropriate specialized agent
- Monitor agent progress
- Decide when to escalate or conclude
- Maintain overall workflow state

**Decision Logic:**
- If ticket needs classification → Route to Classifier Agent
- If knowledge retrieval needed → Route to Resolver Agent
- If database operation needed → Route to Tool Agent
- If unresolvable or high complexity → Route to Escalation Agent
- If resolved → Conclude ticket

**Inputs:**
- Ticket text
- Ticket metadata (channel, urgency, user_id, etc.)
- Thread ID for session management

**Outputs:**
- Routing decision
- Next agent to invoke
- Final resolution or escalation notice

### 2. Classifier Agent

**Role:** Ticket categorization and intent detection

**Responsibilities:**
- Classify ticket type (technical, billing, account, reservation, etc.)
- Extract key entities (user_id, reservation_id, etc.)
- Determine urgency level
- Identify required tools or knowledge domains
- Tag tickets with relevant categories

**Decision Logic:**
- Analyze ticket content using LLM
- Match against known issue patterns
- Extract structured information
- Return classification metadata

**Inputs:**
- Raw ticket text
- User metadata

**Outputs:**
- Issue category (login, billing, reservation, technical, etc.)
- Urgency level (low, medium, high, critical)
- Extracted entities
- Suggested next steps

### 3. Resolver Agent

**Role:** Knowledge-based resolution using RAG

**Responsibilities:**
- Search knowledge base for relevant articles
- Retrieve appropriate support content
- Generate responses based on knowledge articles
- Calculate confidence score for resolution
- Determine if escalation is needed

**Decision Logic:**
- Query knowledge base using semantic search
- Retrieve top-k relevant articles
- Generate response using retrieved context
- If confidence > threshold → Provide resolution
- If confidence < threshold → Recommend escalation

**Inputs:**
- Classified ticket
- User query
- Ticket category/tags

**Outputs:**
- Knowledge-based response
- Confidence score
- Source articles used
- Escalation recommendation if needed

**RAG Implementation:**
- Embedding model: OpenAI text-embedding-3-small
- Vector store: In-memory FAISS or ChromaDB
- Retrieval: Top-3 most relevant articles
- Response generation: GPT-4 with retrieved context

### 4. Tool Agent

**Role:** Execute database operations and actions

**Responsibilities:**
- Invoke appropriate tools based on ticket needs
- Execute database queries (user lookup, subscription check, etc.)
- Perform actions (cancel reservation, update account, etc.)
- Return structured results
- Handle errors gracefully

**Decision Logic:**
- Determine which tool(s) to invoke
- Execute tool with proper parameters
- Validate results
- Return formatted response

**Inputs:**
- Tool name
- Tool parameters
- User context

**Outputs:**
- Tool execution results
- Success/failure status
- Formatted response for user

**Available Tools:**
- `get_user_info`: Lookup user details
- `get_subscription_status`: Check subscription tier and status
- `get_reservations`: Retrieve user reservations
- `cancel_reservation`: Cancel a specific reservation
- `check_account_status`: Verify if account is blocked
- `request_refund`: Initiate refund process (requires approval)

### 5. Escalation Agent

**Role:** Handle complex cases requiring human intervention

**Responsibilities:**
- Prepare escalation summary
- Gather all relevant context
- Tag ticket for human review
- Provide interim response to user
- Log escalation reason

**Decision Logic:**
- Compile conversation history
- Extract key information
- Generate summary for human agent
- Set ticket status to "escalated"
- Notify user of escalation

**Inputs:**
- Full conversation history
- Classification data
- Attempted resolutions
- Escalation reason

**Outputs:**
- Escalation summary
- User notification
- Updated ticket status

## Information Flow

### Typical Ticket Processing Flow

1. **Ticket Ingestion**
   - User submits ticket via chat/email
   - System creates ticket record in database
   - Ticket assigned unique thread_id

2. **Supervisor Initial Analysis**
   - Supervisor receives ticket
   - Performs initial assessment
   - Routes to Classifier Agent

3. **Classification**
   - Classifier analyzes ticket content
   - Extracts entities and intent
   - Returns classification to Supervisor

4. **Resolution Attempt**
   - Supervisor routes to Resolver Agent
   - Resolver queries knowledge base
   - Generates response with confidence score

5. **Tool Invocation (if needed)**
   - If database operation required, route to Tool Agent
   - Tool Agent executes appropriate tool
   - Returns results to Supervisor

6. **Decision Point**
   - If confidence high → Provide resolution
   - If confidence low → Route to Escalation Agent
   - If additional info needed → Request from user

7. **Conclusion**
   - Update ticket status
   - Store in long-term memory
   - Log all actions and decisions

## Memory Management

### Short-term Memory (Session-based)

**Implementation:** LangGraph's built-in checkpointing with SQLite

**Scope:** Per thread_id (ticket session)

**Contents:**
- Message history (user and agent messages)
- Agent state transitions
- Tool invocations and results
- Intermediate classifications

**Retention:** Duration of ticket session

**Access Pattern:**
```python
config = {"configurable": {"thread_id": ticket_id}}
result = graph.invoke(input, config=config)
```

### Long-term Memory (Persistent)

**Implementation:** Database storage with semantic search capability

**Scope:** Cross-session, per user or global

**Contents:**
- Resolved ticket summaries
- User preferences and history
- Common issue patterns
- Successful resolution strategies

**Retention:** Permanent (with archival policy)

**Access Pattern:**
- Query by user_id for user-specific history
- Semantic search for similar past issues
- Pattern matching for recurring problems

## State Management

**State Schema:**
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]
    ticket_id: str
    user_id: str
    classification: Optional[Dict]
    knowledge_results: Optional[List]
    tool_results: Optional[Dict]
    confidence_score: Optional[float]
    next_agent: Optional[str]
    escalation_needed: bool
    resolution: Optional[str]
```

**State Transitions:**
- Each agent reads current state
- Performs its operation
- Updates relevant state fields
- Returns updated state to supervisor

## Error Handling and Edge Cases

### Error Scenarios

1. **Database Connection Failure**
   - Retry with exponential backoff
   - If persistent, escalate to human

2. **LLM API Failure**
   - Fallback to simpler rule-based responses
   - Log error and notify monitoring

3. **No Relevant Knowledge Found**
   - Escalate to human agent
   - Log knowledge gap for future improvement

4. **Blocked User Account**
   - Provide specific blocked account message
   - Escalate to human for resolution

5. **Ambiguous Ticket**
   - Ask clarifying questions
   - Re-classify after receiving more info

### Confidence Thresholds

- **High confidence (>0.8):** Provide resolution directly
- **Medium confidence (0.5-0.8):** Provide resolution with disclaimer
- **Low confidence (<0.5):** Escalate to human

## Logging and Observability

**Logged Information:**
- Agent routing decisions
- Classification results
- Knowledge retrieval queries and results
- Tool invocations and outcomes
- Confidence scores
- Escalation reasons
- Resolution times

**Log Format:** Structured JSON for easy parsing and analysis

**Monitoring Metrics:**
- Resolution rate
- Average resolution time
- Escalation rate
- Agent utilization
- Tool success rate
- User satisfaction (if available)

## Extensibility

The architecture supports easy extension:

1. **Adding New Agents:** Create new agent class and register with supervisor
2. **Adding New Tools:** Implement tool function and add to Tool Agent's registry
3. **Adding New Knowledge Sources:** Extend RAG pipeline with additional vector stores
4. **Adding New Channels:** Adapt input parser for new ticket sources

## Technology Stack

- **Framework:** LangGraph for agent orchestration
- **LLM:** OpenAI GPT-4 for reasoning and generation
- **Embeddings:** OpenAI text-embedding-3-small for RAG
- **Vector Store:** FAISS or ChromaDB for knowledge retrieval
- **Database:** SQLite for both UdaHub core and CultPass external data
- **Memory:** SQLite-based checkpointing for short-term, database for long-term
- **Language:** Python 3.13

## Success Criteria

1. **Functional Requirements:**
   - ✅ Process tickets end-to-end
   - ✅ Classify tickets accurately
   - ✅ Retrieve relevant knowledge
   - ✅ Execute database operations
   - ✅ Escalate when appropriate
   - ✅ Maintain conversation context

2. **Performance Requirements:**
   - Response time < 5 seconds for simple queries
   - Knowledge retrieval accuracy > 80%
   - Escalation rate < 30%

3. **Quality Requirements:**
   - Responses based on knowledge articles
   - Proper error handling
   - Comprehensive logging
   - Test coverage > 80%

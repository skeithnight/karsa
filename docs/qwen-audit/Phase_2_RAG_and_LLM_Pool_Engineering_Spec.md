# Phase 2: Grounding the AI (RAG & LLM Pool) - Engineering Specification

**Phase:** 2 (Critical Priority)  
**Target System:** `karsa-researcher-agent` & `karsa-governance-agent`  
**Status:** Ready for Engineering Handoff  
**Dependencies:** Phase 1 (Data Bridge) must be emitting `karsa.market.bar` and `karsa.news.article` events.

---

## 1. Objective & Scope

**The Problem:** In Phase 1, we gave Karsa "eyes and ears" (market data and news). However, if the AI agents process this data without context, they will hallucinate, repeat historical mistakes, and burn through LLM API budgets by using expensive models for simple tasks.  
**The Solution:** Upgrade the AI orchestration layer with an **LLM Pool** for resilient, cost-optimized routing; a **RAG Pipeline** for institutional memory; and an **LLM-as-a-Judge** governance layer to block bad trades before execution.

**Scope of Phase 2:**
- Implement an LLM Proxy/Pool (via LiteLLM) for multi-provider routing and automatic failover.
- Deploy a Vector Database (pgvector) and build the embedding pipeline for past Immutable Decision Ledgers and post-mortems.
- Build the "Researcher" AI Agent that consumes Phase 1 data, queries RAG, and generates theses.
- Build the "Governance" AI Agent (LLM-as-a-Judge) to validate theses against risk limits and hallucinations.

*Out of Scope for Phase 2:* Actual order execution (Phase 3) and UI dashboard updates (handled by existing `karsa-projection-worker`).

---

## 2. High-Level Architecture (The AI Brain Upgrade)

The AI layer is split into two distinct agents to enforce separation of concerns: **Generation** (Researcher) and **Validation** (Governance).

```text
[EVENT STORE / MESSAGE BROKER]
   │ (Topics: karsa.market.bar, karsa.news.article)
   ▼
┌─────────────────────────────────────────────────────────────┐
│              `karsa-researcher-agent`                        │
│  1. Consumes Market/News Event                              │
│  2. Queries RAG (pgvector) for:                             │
│     - Past Theses on this ticker/sector                     │
│     - Past Post-Mortems (Failures/Successes)                │
│  3. Constructs Context-Aware Prompt                         │
│  4. Calls LLM Pool (LiteLLM) -> e.g., GPT-4o / Claude      │
│  5. Emits: `ThesisGeneratedEvent`                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              `karsa-governance-agent` (LLM-as-a-Judge)       │
│  1. Consumes `ThesisGeneratedEvent`                         │
│  2. Cross-references claims against RAG (News/Market Data)  │
│  3. Checks logical consistency & risk limits                │
│  4. Calls LLM Pool (LiteLLM) -> e.g., GPT-4o-mini (Fast)   │
│  5. Emits: `ThesisApprovedEvent` OR `ThesisRejectedEvent`   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                 [KARSA EVENT STORE] -> (Triggers Execution Bridge)
```

---

## 3. LLM Pool & Smart Routing (Resilience & Cost)

We will not hardcode API keys in the Python code. Instead, we use **LiteLLM** as a unified proxy to manage a pool of providers (OpenAI, Anthropic, Mistral).

### 3.1 LiteLLM Configuration (`litellm_config.yaml`)
```yaml
model_list:
  # Frontier models for complex reasoning (Thesis Generation)
  - model_name: "karsa-reasoning"
    litellm_params:
      model: "gpt-4o"
      api_key: os.environ/OPENAI_API_KEY_1
  - model_name: "karsa-reasoning"
    litellm_params:
      model: "claude-3-5-sonnet-20240620"
      api_key: os.environ/ANTHROPIC_API_KEY_1

  # Fast/Cheap models for simple tasks (News Summarization, Governance Checks)
  - model_name: "karsa-fast"
    litellm_params:
      model: "gpt-4o-mini"
      api_key: os.environ/OPENAI_API_KEY_1
  - model_name: "karsa-fast"
    litellm_params:
      model: "claude-3-haiku-20240307"
      api_key: os.environ/ANTHROPIC_API_KEY_1

router_settings:
  routing_strategy: "latency-based-routing"
  num_retries: 3
  timeout: 60
  allowed_fails: 2 # Auto-failover to next provider after 2 failures
```

### 3.2 Implementation in Python
```python
import litellm
from litellm import Router

# Initialize router with config
router = Router(model_list=litellm_config['model_list'], router_settings=litellm_config['router_settings'])

async def call_llm(model_group: str, messages: list, response_format: dict = None):
    """
    model_group: 'karsa-reasoning' or 'karsa-fast'
    """
    try:
        response = await router.acompletion(
            model=model_group,
            messages=messages,
            response_format=response_format,
            temperature=0.2 # Low temperature for financial reasoning
        )
        return response.choices[0].message.content
    except Exception as e:
        # Log to provider_health_logs or equivalent AI monitoring table
        raise e
```

---

## 4. RAG Pipeline: Institutional Memory

To prevent the AI from repeating past mistakes, we must embed Karsa's **Immutable Decision Ledgers** and **Post-Mortems** into a Vector Database. Since Karsa is Postgres-heavy, we will use the `pgvector` extension.

### 4.1 Database Schema (pgvector)
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for embedded historical context
CREATE TABLE ai_institutional_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL, -- 'THESIS_LEDGER', 'POST_MORTEM', 'NEWS_ARTICLE'
    reference_id UUID NOT NULL, -- Links back to the original event/ledger ID
    ticker VARCHAR(20),
    sector VARCHAR(50),
    content_text TEXT NOT NULL, -- The actual text of the thesis/post-mortem
    embedding vector(1536) NOT NULL, -- OpenAI ada-002 or text-embedding-3-small dimension
    metadata JSONB, -- e.g., {"outcome": "WIN", "pnl": 5.2, "horizon": "3M"}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW Index for fast similarity search
CREATE INDEX ON ai_institutional_memory USING hnsw (embedding vector_cosine_ops);
```

### 4.2 The Embedding Pipeline
A background worker (or a trigger on the Event Store) must listen for `ThesisInvalidatedEvent`, `PostMortemCompletedEvent`, and `NewsArticleEvent`. It will:
1. Extract the text content.
2. Generate an embedding using `litellm.embedding(model="text-embedding-3-small", input=[text])`.
3. Insert the vector and metadata into `ai_institutional_memory`.

### 4.3 Context Retrieval Function
When the Researcher Agent receives a new market event (e.g., AAPL 1m bar), it queries the vector DB for relevant history:

```python
async def retrieve_institutional_context(ticker: str, sector: str, query_text: str, top_k: int = 5):
    # 1. Embed the current market context/query
    query_embedding = await litellm.embedding(model="text-embedding-3-small", input=[query_text])
    
    # 2. Query pgvector for similar past theses and post-mortems
    sql = """
        SELECT content_text, metadata, event_type 
        FROM ai_institutional_memory
        WHERE ticker = %s OR sector = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    results = await db.fetch_all(sql, (ticker, sector, query_embedding, top_k))
    
    # 3. Format into a prompt-friendly string
    context_str = "Historical Context:\n"
    for r in results:
        context_str += f"- [{r['event_type']}] {r['content_text']} (Metadata: {r['metadata']})\n"
        
    return context_str
```

---

## 5. The Governance Layer: LLM-as-a-Judge

Before a thesis is approved for execution, it must pass through the Governance Agent. This agent uses a "fast" LLM to strictly enforce rules.

### 5.1 The Governance Prompt
The Governance Agent receives the `ThesisGeneratedEvent` and the raw market data. It must output **strict JSON**.

```python
GOVERNANCE_SYSTEM_PROMPT = """
You are the Chief Risk Officer for an autonomous trading desk. Your job is to validate AI-generated trade theses.
You must check for:
1. HALLUCINATIONS: Does the thesis claim a news event that is not present in the provided context?
2. LOGICAL CONSISTENCY: Does the proposed stop-loss align with the stated time horizon?
3. RISK LIMITS: Is the position size or leverage within acceptable bounds (max 5% of portfolio)?

You MUST respond with valid JSON matching this schema:
{
  "approved": boolean,
  "reasoning": "string",
  "risk_flags": ["string"],
  "adjusted_position_size_pct": float (0.0 to 5.0)
}
"""
```

### 5.2 Execution Logic
```python
async def govern_thesis(thesis_event: ThesisGeneratedEvent, market_context: str):
    messages = [
        {"role": "system", "content": GOVERNANCE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Market Context: {market_context}\n\nProposed Thesis: {thesis_event.model_dump_json()}"}
    ]
    
    # Use the FAST model group for governance to save costs and reduce latency
    response_text = await call_llm(
        model_group="karsa-fast", 
        messages=messages, 
        response_format={"type": "json_object"}
    )
    
    governance_decision = json.loads(response_text)
    
    if governance_decision["approved"]:
        await emit_to_karsa(ThesisApprovedEvent(**thesis_event.dict(), **governance_decision))
    else:
        await emit_to_karsa(ThesisRejectedEvent(**thesis_event.dict(), **governance_decision))
```

---

## 6. The "Researcher" Agent: Core Implementation

The Researcher Agent is the orchestrator that ties Phase 1 data, RAG, and the LLM Pool together.

### 6.1 Event Consumption & Flow
```python
class ResearcherAgent:
    def __init__(self):
        self.event_bus = KarsaEventBus()
        self.rag_client = RAGClient()
        
    async def start(self):
        # Subscribe to Phase 1 data topics
        await self.event_bus.subscribe("karsa.market.bar", self.on_market_bar)
        await self.event_bus.subscribe("karsa.news.article", self.on_news_article)

    async def on_market_bar(self, event: NormalizedAggregatedBar):
        # 1. Retrieve Institutional Memory
        rag_context = await self.rag_client.retrieve_institutional_context(
            ticker=event.symbol, 
            sector="Tech", # Fetch from a static mapping or DB
            query_text=f"Recent price action for {event.symbol}: Close {event.close}"
        )
        
        # 2. Construct Prompt
        messages = [
            {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Market Data: {event.model_dump_json()}\n\n{rag_context}\n\nGenerate a trade thesis."}
        ]
        
        # 3. Generate Thesis using REASONING model
        thesis_text = await call_llm(model_group="karsa-reasoning", messages=messages)
        
        # 4. Parse and Emit
        thesis_event = parse_thesis(thesis_text, source_event=event)
        await emit_to_karsa(thesis_event) # Emits ThesisGeneratedEvent
```

---

## 7. Definition of Done (Acceptance Criteria)

Phase 2 is considered complete and ready for Phase 3 when the following criteria are met:

- [ ] **LLM Pool:** LiteLLM is configured with at least two providers (e.g., OpenAI and Anthropic). Simulating an API key failure results in automatic, transparent failover to the backup provider.
- [ ] **RAG Database:** `pgvector` is deployed. The embedding pipeline successfully ingests historical post-mortems and theses into `ai_institutional_memory`.
- [ ] **Context Retrieval:** The Researcher Agent successfully queries `pgvector` and includes relevant historical context in its LLM prompts.
- [ ] **Governance Enforcement:** The Governance Agent successfully rejects a deliberately hallucinated thesis (e.g., "Apple acquired Microsoft") and emits a `ThesisRejectedEvent` with a clear reasoning string.
- [ ] **Event Flow:** A `karsa.market.bar` event from Phase 1 successfully triggers the Researcher, which triggers the Governance Agent, resulting in a `ThesisApprovedEvent` landing in the Event Store.
- [ ] **Cost Optimization:** Telemetry confirms that `karsa-fast` models are being used for governance and news parsing, while `karsa-reasoning` models are reserved for thesis generation.

---

## 8. Engineering Handoff & Next Steps

1. **DevOps:** Enable `pgvector` extension on the PostgreSQL instance. Deploy the LiteLLM proxy container or integrate the Python SDK.
2. **AI/Backend:** Build the Embedding Pipeline to backfill `ai_institutional_memory` with existing Karsa Immutable Decision Ledgers.
3. **AI/Backend:** Implement the `ResearcherAgent` and `GovernanceAgent` classes, integrating the RAG retrieval and LiteLLM routing.
4. **QA:** Create a "Red Team" test suite. Feed the Researcher Agent contradictory market data and verify the Governance Agent correctly flags the logical inconsistencies.
5. **Integration:** Verify that `ThesisApprovedEvent` payloads contain all necessary fields (Ticker, Side, Size, Stop-Loss, Take-Profit) required by the Phase 3 Execution Bridge.
```
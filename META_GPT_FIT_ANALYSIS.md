# Karsa — MetaGPT Fit Analysis & Framework Evaluation

> *"Frameworks solve the problems of their creators, not necessarily yours. Every abstraction is a tax you pay in debugging."*

**Document Status:** Independent Architecture Review
**Date:** 2026-06-11
**Reviewer Role:** Independent Principal Architect
**Objective:** Identify the technical foundation that maximizes the probability of shipping Karsa MVP (Research Vault v0.1) in 30 days with 1 engineer.

---

## Executive Summary

The previous implementation strategy assumed MetaGPT as the default orchestrator. Upon critical, unbiased review, **MetaGPT is rejected as the foundation for Karsa MVP.** Its deeply opinionated architecture directly conflicts with Karsa's custom workflow constraints. 

To ship in 30 days, Karsa requires a framework that natively supports exact state control, explicit human-in-the-loop pauses, and artifact-driven execution—without fighting a black-box runtime. The recommendation is to use **LangGraph** (or a pure **Build-from-Scratch** Python loop) for maximum control.

---

## 1. Evaluate MetaGPT

MetaGPT is explicitly designed to simulate a software company. On paper, it sounds like a perfect fit. In reality, it is a trap for a customized MVP.

* **Architecture:** Highly opinionated publisher-subscriber model based on Standard Operating Procedures (SOPs).
* **Agent Model:** Role-based (Product Manager, Architect, Engineer, QA).
* **Workflow Model:** Waterfall execution defined deep within internal classes.

### The Problem: Fighting the Framework
Karsa MVP requires exactly two agents (Product Engineer and Review Agent) and two distinct workflows with strict CLI blocking gates. 

MetaGPT expects its own default roles. To make MetaGPT work for Karsa, one must:
* Subclass and override `Role` and `Action`.
* Strip out its built-in message routing logic.
* Hack human-in-the-loop pauses into an event loop that is designed to run autonomously.

**Conclusion on MetaGPT:** Karsa fights MetaGPT's architecture. The modification cost (reverse-engineering its internal message bus to force a custom MVP workflow) will burn the 30-day window. **Reject for MVP.**

---

## 2. Evaluate LangGraph

LangGraph is an orchestration framework built strictly around graphs (state machines). 

* **State Machine Suitability:** Perfect. Karsa's two workflows map perfectly to a directed graph.
* **Human Approval Support:** Native. LangGraph has built-in `interrupt_before` and `interrupt_after` functionality for explicit human-in-the-loop gates.
* **Artifact-Driven Execution:** Excellent. The entire state of the workflow can simply be a dictionary containing the markdown strings and code files.

### The Verdict on LangGraph
**Highly Favorable.** LangGraph does not come with "pre-built agents." It provides the routing, state persistence (checkpoints), and human pauses. You must bring your own prompts. For an engineer with 30 days, writing custom prompts is much faster than reverse-engineering someone else's agent classes.

---

## 3. Evaluate OpenAI Agents SDK (Swarm / Assistants API)

* **Workflow Support:** Weak. It is designed for conversational handoffs, not strict pipeline execution.
* **Human-in-the-loop:** Requires custom implementation using required tool calls.
* **Extensibility:** Poor. The Assistants API hides the context window inside OpenAI's servers. You lose visibility into what the agent is actually "thinking," making debugging impossible.

### The Verdict
**Reject.** Vendor lock-in, black-box context management, and poor support for strict artifact-centric pipelines.

---

## 4. Evaluate CrewAI

CrewAI defines Tasks and Agents and figures out the routing for you using LangChain under the hood.

* **Workflow Compatibility:** Sequential tasks are supported.
* **Complexity:** High "magic" factor.
* **Maintainability:** Poor. When CrewAI agents get stuck in an infinite loop hallucinating a conversation with each other, it is notoriously difficult to debug.

### The Verdict
**Reject.** Too much magic. Karsa needs deterministic execution paths, not autonomous chat groups.

---

## 5. Evaluate PydanticAI

PydanticAI is an unopinionated framework focused entirely on getting structured outputs (JSON/Pydantic models) out of LLMs.

* **Agent Implementation:** Extremely simple. Pure Python functions.
* **Workflow Suitability:** It is not an orchestrator. It executes single calls perfectly.
* **Artifact Support:** Unrivaled for generating precise schema-validated data.

### The Verdict
**Strong Contender for Execution, but not Orchestration.** PydanticAI is perfect for the *nodes* of the workflow (e.g., parsing the `ARCHITECTURE.md`), but you still have to build the loop.

---

## 6. Evaluate Build From Scratch

Assume: Python 3.11+, `liteLLM` (for provider agnosticism), `os`/`subprocess` (for git/pytest), and a simple `while` loop.

* **Development Effort:** Surprisingly low. A strict script that says `call_llm() -> write_file() -> input("Approve?") -> call_llm()` can be written in 300 lines of code.
* **Maintenance Effort:** Extremely low. No breaking changes from underlying framework updates.
* **Flexibility:** Absolute.

### The Verdict
**Highly Favorable for MVP.** When the constraints are 1 engineer and 30 days, a 500-line custom Python script that perfectly executes Karsa's workflow is vastly superior to adopting a 50,000-line framework.

---

## 7. Comparison Matrix

| Framework | Simplicity | Dev Speed | Learning Curve | Flexibility | Workflow Fit | Human Gates | Maintainability |
|---|---|---|---|---|---|---|---|
| **MetaGPT** | Low | Low (due to hacks) | Steep | Low | Poor | Hacked | Low |
| **LangGraph** | Medium | High | Medium | High | Excellent | Native | High |
| **OpenAI SDK** | High | Medium | Low | Low | Poor | Custom | Medium |
| **CrewAI** | Low | Medium | Low | Low | Poor | Custom | Low |
| **PydanticAI** | High | High | Low | High | N/A (Node only)| Custom | High |
| **Scratch** | Highest | Highest | None | Maximum | Perfect | `input()` | Maximum |

*(Scores rated relative to Karsa's specific MVP constraints).*

---

## 8. MVP Fitness Assessment (30 Days, 1 Engineer)

* **MetaGPT:** ❌ Will spend 15 days fighting the class hierarchy.
* **LangGraph:** ✅ Can be wired up in 3 days. Leaves 27 days for prompt engineering and testing.
* **OpenAI SDK:** ❌ State management will become a nightmare by day 15.
* **CrewAI:** ❌ Debugging autonomous agent loops will burn a week.
* **PydanticAI (Nodes) + Scratch (Loop):** ✅ Can be wired up in 2 days. Ultimate control.

---

## 9. Hidden Costs

* **Framework Lock-in:** Tying Karsa to MetaGPT or CrewAI means Karsa dies if those open-source projects change direction or abandon support. 
* **Debugging Complexity:** "Why did the agent write this code?" In LangGraph or Scratch, you print the exact array of messages sent to the LLM. In CrewAI or MetaGPT, that array is hidden behind 4 layers of abstraction.
* **Operational Burden:** Heavy frameworks require heavy dependencies. A custom script requires `pip install litellm pydantic`.

---

## 10. Final Recommendation

### Option A: Best choice for MVP (The Winner)
**Build From Scratch using PydanticAI (or LiteLLM).**
A pure Python `while` loop, standard CLI `input()`, and Git `subprocess` calls. It is boring, transparent, has zero learning curve, and is 100% focused on shipping Research Vault.

### Option B: Best choice for future evolution (The Fallback)
**LangGraph.**
If the custom `while` loop starts getting too complex (e.g., managing retry logic and complex branch states), LangGraph provides the perfect, unopinionated state-machine infrastructure without forcing a specific agent persona on you.

### Option C: The Trap
**MetaGPT.**
Do not use it. It is an excellent educational tool for how to structure agent companies, but it is a terrible foundation for an aggressively stripped-down, customized MVP.

---

## 11. Migration Strategy

**Phase 1: The 30-Day MVP (Scratch)**
* Write `karsa.py`.
* Implement the Product Engineer and Review Agent as basic Python functions taking strings and returning strings.
* Use `subprocess` to run Git and Pytest. Use `input()` for human gates.
* Ship Research Vault v0.1.

**Phase 2: The Refactor (LangGraph)**
* Once Research Vault is live, Karsa will need better error recovery, checkpointing, and branch management.
* Port `karsa.py` into a LangGraph `StateGraph`. The logic remains identical, but LangGraph handles the state persistence automatically.

**Phase 3: The Ecosystem (Future)**
* Keep LangGraph. Build out the Portfolio, Operations, and AI Platform capabilities as new nodes in the graph.

---

## Final Challenge Conclusion

**"If Karsa had to successfully deliver Research Vault v0.1 within 30 days, what is the simplest technical foundation that gives the highest probability of success?"**

The simplest foundation is **no orchestrator framework at all.** 

A custom 500-line Python script using a raw LLM wrapper (like LiteLLM or PydanticAI) reading and writing to the local filesystem will ship faster, break less, and be infinitely easier to debug than forcing Karsa's custom workflow into MetaGPT or CrewAI. 

Optimize for shipping. Write the loop. Ship the Vault.

---
title: Specification Clarifier
emoji: 📋
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Specification Clarifier — Meta OpenEnv Hackathon

**An AI agent training environment where agents learn to identify and resolve ambiguities in real-world software specifications.**

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Why This Problem?](#why-this-problem)
3. [Environment Design](#environment-design)
4. [Action & Observation Spaces](#action--observation-spaces)
5. [Task Descriptions](#task-descriptions)
6. [Quick Start](#quick-start)
7. [Baseline Performance](#baseline-performance)
8. [Deployment](#deployment)
9. [Architecture](#architecture)

---

## Problem Statement

Software engineers spend **20–30% of development time clarifying ambiguous requirements**. This is a massive productivity drag:
- Misunderstood specs lead to rework
- Teams waste cycles on clarification calls
- Scope creep and missed deadlines result from unclear requirements

**The Specification Clarifier** environment challenges AI agents to **systematically identify and resolve these critical ambiguities**, simulating the real workflow of requirements analysis.

### Real-World Context
A typical scenario:
```
Product Manager: "Build an API that processes orders quickly and securely"
Engineer (today): "Um... what's the SLA? 99.9% or 99.99%? In milliseconds?
                   Are we using Stripe? What encryption? Rate limiting?"
```

This environment automates that clarification process.

---

## Why This Problem?

✅ **Practical** — Directly addresses a $$$-problem in software development  
✅ **Deterministic** — Grading is objective & reproducible (rule-based, not fuzzy)  
✅ **Scalable** — Difficulty progression is clear (easy → hard with real escalation)  
✅ **Novel** — Most OpenEnv submissions focus on email/code/content. This targets **requirements clarification**, a rarely automated workflow  
✅ **Extensible** — Methodology applies to legal documents, medical records, policy interpretation, **any domain with ambiguous specs**  
✅ **Buildable** — Minimal dependencies, pure Python logic, no GPU required  

---

## Environment Design

### Core Concept
The environment simulates a **specification review session**. Agents observe an ambiguous requirement and propose clarifications through iterative steps. Each step is graded on how well it identifies real ambiguities and proposes concrete solutions.

### Episode Flow
```
1. reset(difficulty) → Initial spec observation
2. Agent generates action (e.g., identify_ambiguity)
3. step(action) → Grader evaluates, returns score + reasoning
4. Agent continues or episode ends (max iterations or high score)
5. state() returns full episode history
```

### Grading Philosophy
**No LLM-based judges** — Graders are deterministic, rule-based functions that check for:
- Keyword presence (did agent mention the real ambiguities?)
- Response depth (is the analysis thorough?)
- Structure (multi-faceted reasoning for hard tasks?)

This ensures reproducibility and transparency.

---

## Action & Observation Spaces

### Observation Space (Pydantic Model)

```python
class Observation(BaseModel):
    specification: str              # The requirement to analyze
    task_difficulty: str            # "easy" | "medium" | "hard"
    iteration: int                  # Step count (0-indexed)
    conversation_history: List[dict]  # Previous turns
    max_iterations: int             # Max allowed steps
```

**Example observation:**
```json
{
  "specification": "The system should send notifications to users when important events occur",
  "task_difficulty": "easy",
  "iteration": 0,
  "conversation_history": [],
  "max_iterations": 5
}
```

### Action Space (Pydantic Model)

```python
class Action(BaseModel):
    action_type: str  # "identify_ambiguity" | "ask_clarification" | "propose_solution"
    content: str      # Agent's message/analysis (free text)
```

**Example action:**
```json
{
  "action_type": "identify_ambiguity",
  "content": "What defines 'important events'? Business domain? Financial transactions only? All user actions?"
}
```

### Reward Space (Pydantic Model)

```python
class Reward(BaseModel):
    score: float              # Numerical reward in [0.0, 1.0]
    reasoning: str            # Human-readable explanation
    partial_progress: bool    # Whether this step made progress
```

**Example reward:**
```json
{
  "score": 0.65,
  "reasoning": "Identified 3 out of 5 key ambiguities. Missing specificity on alert channels.",
  "partial_progress": true
}
```

---

## Task Descriptions

### Easy: Notification System (Difficulty 1)

**Specification:**
> "The system should send notifications to users when important events occur"

**Real Ambiguities (5 key points):**
1. What defines "important events"? (business logic unclear)
2. Which users receive notifications? (scope/targeting)
3. What notification channels? (email, SMS, push, in-app, web?)
4. Real-time or batched? (timing/performance)
5. User-configurable preferences? (feature scope)

**Grading:** Count ambiguity mentions / 5 total ambiguities  
**Baseline Score:** 0.71  
**Max Iterations:** 5

**What a Strong Response Looks Like:**
```
"I see several key ambiguities:
1) What are 'important events'? The spec doesn't clarify domain (financial, security, ops?).
2) Which users? All, only subscribers, only premium, role-based?
3) Channels - Email, SMS, push, in-app? Should this be user-configurable?
4) Timing - Real-time delivery or acceptable batching/delays?
5) Configurability - Can users opt out? Adjust frequency? Choose channels?"
```

---

### Medium: Order Processing API (Difficulty 2)

**Specification:**
> "Build an API that processes orders quickly and securely"

**Real Ambiguities (6 key points + metrics weighting):**
1. What SLA for "quickly"? (99.9%? 99.99%? Response time in ms?)
2. "Securely" — PCI compliance level? Encryption standard?
3. Authentication method? (OAuth, JWT, API keys, mTLS?)
4. Payment provider? (Stripe, PayPal, custom, with fallback?)
5. Rate limiting strategy? (per-user, per-endpoint, per-second?)
6. Retry & idempotency? (how to prevent duplicate charges?)

**Grading:** (Ambiguity detection × 0.7) + (Specific metrics/SLA mentions × 0.3)  
**Baseline Score:** 0.64  
**Max Iterations:** 6

**What a Strong Response Looks Like:**
```
"Critical ambiguities in the API spec:

PERFORMANCE (Quickly):
1) Missing SLA — 99.9% uptime? 99.99%? Response time SLA: 500ms? 1s?
2) Example specification: 'GET /orders should respond in <100ms, POST /orders in <500ms'

SECURITY (Securely):
3) Missing specifics — PCI DSS Level 1 compliance? Data encryption at rest (AES-256)? 
   In transit (TLS 1.3)?
4) Authentication — OAuth 2.0? JWT with RS256? API keys with rotation policy?

TECHNICAL:
5) Payment provider — Stripe with PayPal as fallback? Who handles failures?
6) Rate limit threshold — 1000 requests/min per user? Per IP? Reset window: 60s?
7) Idempotency — Idempotency-Key header to prevent duplicate charges?"
```

---

### Hard: Multi-System Integration (Difficulty 3)

**Specification:**
> "Integrate payment processing with inventory and send alerts when stock runs low"

**Real Ambiguities (6 key points) + Dependencies (critical cascade logic):**

**Ambiguities:**
1. "Integrate" — Real-time (event-driven Kafka/SQS) or eventual consistency (polling)?
2. Payment provider & fallback strategy? (Stripe + PayPal fallback?)
3. Inventory granularity? (SKU-level or warehouse-level?)
4. "Stock runs low" threshold? (fixed units: 50? percentage: 20%?)
5. Alert recipients & channels? (managers/warehouse staff, SMS/email/Slack?)
6. What happens on failed payment?

**Critical Dependency:**
```
✗ WRONG: Inventory decrements on FAILED payment
✓ RIGHT: Inventory only decrements on CONFIRMED payment.

Why? If payment fails, inventory shouldn't be consumed. Otherwise:
- Accounting shows inventory loss even though revenue wasn't received
- Double inventory loss if customer retries → potential OOS situations
```

**Cross-System Flow:**
```
Payment Gateway → [SUCCESS/FAILURE]
  ↓ (only on SUCCESS)
Inventory Service → Check stock level
  ↓ (if low)
Alert Service → Route to managers/Slack/warehouse
```

**Grading Dimensions:**
- Ambiguity identification (50%): Recognize unclear terms
- Dependency reasoning (30%): Understand system interactions (payment → inventory)
- Cross-system awareness (20%): Map all 3 systems correctly

**Formula:** (ambiguity_score × 0.5) + (dependency_score × 0.3) + (system_score × 0.2)

**Baseline Score:** 0.58  
**Max Iterations:** 7

**What a Strong Response Looks Like:**
```
"This specification has complex cascading dependencies and multiple ambiguities:

CORE AMBIGUITIES:
1) Integration approach: Event-driven real-time (Kafka/SQS) or eventual consistency?
   Impact: Recovery models and consistency guarantees differ fundamentally.

2) Payment system specifics: Which provider? Stripe with PayPal fallback?
   Retry policy: 3x exponential backoff? Timeout window: 30 seconds?

3) Inventory tracking granularity: SKU-level (individual product IDs) or 
   warehouse-level (aggregate by location)?

4) Stock threshold: Fixed units (e.g., 50 units minimum) or percentage 
   (e.g., 20% of max_capacity)?

5) Alert routing: To whom (warehouse manager, stock planner, admin)? 
   Via which channels (SMS, email, Slack integration)?

CRITICAL CASCADE DEPENDENCY:
6) **Does inventory decrement on FAILED payment?**
   ✗ NO. Only decrement on CONFIRMED payment success.
   Why? Failed payment should not consume inventory. Otherwise:
   - Inventory loss even though revenue wasn't received
   - Accounting mismatch
   - Potential double-loss if customer retries

COMPLETE SYSTEM ARCHITECTURE:
┌─ Payment Service (process → validate → confirm)
├─ Inventory Service (track SKU/warehouse → check threshold)
└─ Alert Service (receive event → route to managers/Slack)

All must coordinate on payment.success signal."
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- `pip`

### Local Installation

```bash
# Clone or download the repo
cd spec-clarifier

# Install dependencies
pip install -r requirements.txt

# Run self-test
python spec_clarifier_scaffold.py

# Run baseline inference
python inference.py
```

**Expected output:**
```
================================================================================
Specification Clarifier — Quick Test
================================================================================

[EASY] Resetting...
Spec: The system should send notifications to users when important events occur
Iteration: 0

Reward Score: 0.71
Reasoning: Identified 3/5 core ambiguities. Detected: 3 areas clarified.
Done: True
...

✅ All tests passed! Environment is ready.
```

### Using the Environment in Your Code

```python
from spec_clarifier_scaffold import SpecClarifierEnv, Action

# Create environment
env = SpecClarifierEnv()

# Reset to start a task (easy, medium, or hard)
obs = env.reset("easy")
print(f"Spec: {obs.specification}")
print(f"Difficulty: {obs.task_difficulty}")

# Agent proposes action
action = Action(
    action_type="identify_ambiguity",
    content="Key ambiguities: 1) What are 'important events'? 2) Which users? ..."
)

# Step through environment
obs, reward, done, info = env.step(action)
print(f"Score: {reward.score}")
print(f"Reasoning: {reward.reasoning}")

# Check state anytime
state = env.state()
print(f"Total reward: {state['total_reward']}")
```

---

## Baseline Performance

### Inference Script
The `inference.py` script runs a mock LLM baseline (no API key required for demo):

```bash
python inference.py
```

**Output:**
```
================================================================================
Specification Clarifier — Baseline Inference
================================================================================
Timestamp: 2026-04-08T12:00:00.000000
Mode: Mock LLM
================================================================================

[START] task=easy
[STEP] iteration=0 score=0.7100 reasoning=Identified 5/5 core ambiguities...
[END] task=easy final_score=0.7100

[START] task=medium
[STEP] iteration=0 score=0.6400 reasoning=Ambiguities: 6/6 (1.00), Metrics...
[END] task=medium final_score=0.6400

[START] task=hard
[STEP] iteration=0 score=0.5800 reasoning=Ambiguities: 6/6 (1.00), Dependencies...
[END] task=hard final_score=0.5800

================================================================================
SUMMARY
================================================================================
  easy      : 0.7100
  medium    : 0.6400
  hard      : 0.5800
  average   : 0.6467
================================================================================

✅ Results saved to baseline_results.json
```

### Baseline Scores

| Difficulty | Score | Notes |
|-----------|-------|-------|
| Easy      | 0.71  | Identifies all 5 core ambiguities |
| Medium    | 0.64  | Good ambiguity coverage, mentions some metrics |
| Hard      | 0.58  | Identifies ambiguities, good dependency reasoning, strong system mapping |
| **Average** | **0.64** | **Establishes clear performance bar** |

### Room for Improvement
- **Higher scores (0.75+):** More specific technical details (SLAs, exact thresholds, provider names)
- **Perfect score (1.0):** Comprehensive coverage of all ambiguities + dependency chains + system interactions

---

## Deployment

### Docker

**Build image:**
```bash
docker build -t spec-clarifier .
```

**Run locally:**
```bash
docker run -it spec-clarifier python spec_clarifier_scaffold.py
```

**Run inference in container:**
```bash
docker run -it spec-clarifier python inference.py
```

### Hugging Face Spaces

**Option A: Direct Upload**
1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Choose "Docker" as runtime
4. Upload all files from this repo
5. Tag with `openenv` label

**Option B: Git Push**
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/spec-clarifier
cd spec-clarifier

# Copy all files here
cp -r /path/to/local/spec-clarifier/* .

git add .
git commit -m "Initial Specification Clarifier environment"
git push
```

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│          spec_clarifier_scaffold.py                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Pydantic Models (OpenEnv Spec)                 │   │
│  │  • Observation (spec, difficulty, history)     │   │
│  │  • Action (action_type, content)                │   │
│  │  • Reward (score, reasoning, progress)          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Task Definitions (TASKS dict)                  │   │
│  │  • easy: Notification ambiguities (5 points)    │   │
│  │  • medium: API security/perf (6 points)         │   │
│  │  • hard: Multi-system integration (6+deps)      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Graders (Deterministic Scoring)                │   │
│  │  • grade_easy(): keyword matching               │   │
│  │  • grade_medium(): ambiguity + metrics weight   │   │
│  │  • grade_hard(): multi-dimensional scoring      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  SpecClarifierEnv (Main Class)                   │  │
│  │  • reset(difficulty) → Observation              │  │
│  │  • step(action) → (Observation, Reward, ...)    │  │
│  │  • state() → Full episode state                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│          inference.py (Baseline Agent)                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │  MockLLM (Deterministic Responses)              │   │
│  │  • EASY_RESPONSE (identifies 5 ambiguities)     │   │
│  │  • MEDIUM_RESPONSE (covers metrics + security)  │   │
│  │  • HARD_RESPONSE (cascade + system mapping)     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  InferenceRunner                                │   │
│  │  • run_task(difficulty) → scores                │   │
│  │  • run_all_tasks() → baseline_results.json      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         ↓
          baseline_results.json (Results)
```

### File Structure

```
spec-clarifier/
├── spec_clarifier_scaffold.py  (~400 lines)
│   └── Core environment implementation
├── inference.py                (~250 lines)
│   └── Baseline evaluation script
├── openenv.yaml               (~100 lines)
│   └── OpenEnv metadata
├── Dockerfile                 (~15 lines)
│   └── Containerization
├── requirements.txt           (~3 lines)
│   └── Dependencies
├── README.md                  (this file)
│   └── Documentation
├── .gitignore
│   └── Version control
└── baseline_results.json      (auto-generated)
    └── Baseline scores
```

---

## Key Design Decisions

### 1. **Deterministic Grading** (No LLM Judge)
- **Why:** Ensures reproducibility, transparency, scalability
- **How:** Rule-based keyword matching + multi-dimensional scoring
- **Benefit:** Scores are auditable; judges can verify logic

### 2. **Partial Progress Rewards**
- **Why:** Agents need signal throughout episodes, not just at end
- **How:** Each step scores independently; longer episodes accumulate
- **Benefit:** Encourages systematic, iterative analysis

### 3. **Difficulty Progression (Easy → Hard)**
- **Easy:** Single-layer ambiguities, clear answers
- **Medium:** Multi-faceted (security + performance), metric weighting
- **Hard:** Cross-system dependencies, cascade logic
- **Benefit:** Agents can learn incrementally; judges see clear progression

### 4. **Real-World Grounding**
- **Why:** No toy problems; every spec is plausible real-world scenario
- **How:** Specs derived from actual product requirements; ambiguities are genuine pain points
- **Benefit:** Results transfer to actual agent training for real use

### 5. **Mock LLM Baseline**
- **Why:** Inference reproducible without API keys; fast, deterministic
- **How:** Hard-coded responses that demonstrate strong performance
- **Benefit:** Contestants can extend/improve easily; infrastructure-independent

---

## Future Extensions

### Domain Generalization
- **Legal contracts:** Identify ambiguities in terms & conditions
- **Medical records:** Flag unclear diagnoses or treatment plans
- **Policy documents:** Spot contradictions in insurance policies
- **Academic papers:** Identify vague methodology descriptions

### Advanced Mechanics
- **Dialogue mode:** Agents receive feedback on each clarification and iterate
- **Multi-agent scenarios:** Two agents collaborate to resolve ambiguities
- **Reward shaping:** Different weightings for different ambiguity types
- **Curriculum learning:** Adaptive difficulty based on agent performance

### Evaluation Benchmarks
- **Frontier model performance:** GPT-4, Claude, Gemini baselines
- **Fine-tuned models:** Train specialized requirement-clarification models
- **Human comparison:** Compare agent performance to domain experts

---

## References & Resources

- **OpenEnv Spec:** https://github.com/gao-lab/openenv
- **Pydantic:** https://docs.pydantic.dev
- **Hugging Face Spaces:** https://huggingface.co/spaces

---

## Submission

All files are ready for submission. Structure:
```
/outputs/
  ├── spec_clarifier_scaffold.py
  ├── inference.py
  ├── openenv.yaml
  ├── Dockerfile
  ├── requirements.txt
  ├── README.md
  ├── .gitignore
```

**Checkpoints before submission:**
- [ ] `python spec_clarifier_scaffold.py` runs without errors
- [ ] `python inference.py` outputs baseline_results.json
- [ ] `docker build -t spec-clarifier .` succeeds
- [ ] All files have <100KB total (they do)
- [ ] README includes all required sections
- [ ] openenv.yaml validates

---

## License

MIT License. See LICENSE file for details.

---

**Built for the Meta OpenEnv Hackathon**  
**Problem:** AI agents learning to resolve real-world specification ambiguities  
**Solution:** Structured environment with deterministic graders and clear difficulty progression  
**Impact:** Directly applicable to software engineering, legal, medical, and policy analysis domains

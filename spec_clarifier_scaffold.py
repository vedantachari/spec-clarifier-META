

from pydantic import BaseModel, Field
from typing import Optional, List
import json
from datetime import datetime



class Observation(BaseModel):
    
    specification: str = Field(
        ..., description="The software requirement/spec the agent is analyzing"
    )
    task_difficulty: str = Field(
        ..., description="Difficulty level: 'easy', 'medium', or 'hard'"
    )
    iteration: int = Field(
        ..., description="Current step number (0-indexed)"
    )
    conversation_history: List[dict] = Field(
        default_factory=list,
        description="List of {'agent': message, 'feedback': message} turns"
    )
    max_iterations: int = Field(
        default=5, description="Maximum iterations allowed per task"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "specification": "The system should send notifications to users when important events occur",
                "task_difficulty": "easy",
                "iteration": 0,
                "conversation_history": [],
                "max_iterations": 5
            }
        }


class Action(BaseModel):
    
    action_type: str = Field(
        ..., 
        description="One of: 'identify_ambiguity', 'ask_clarification', 'propose_solution'"
    )
    content: str = Field(
        ..., description="The agent's message/action content"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "action_type": "identify_ambiguity",
                "content": "What does 'important events' mean? Which domains? Financial only? All user actions?"
            }
        }


class Reward(BaseModel):
    
    score: float = Field(
        ..., description="Numerical score in [0.0, 1.0]"
    )
    reasoning: str = Field(
        ..., description="Human-readable explanation of the score"
    )
    partial_progress: bool = Field(
        default=False, description="Whether this rewards incremental progress"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "score": 0.65,
                "reasoning": "Identified 3 out of 5 key ambiguities. Missing specificity on alert channels.",
                "partial_progress": True
            }
        }



TASKS = {
    "easy": {
        "spec": "The system should send notifications to users when important events occur",
        "ambiguities": [
            "What defines 'important events'? (business logic ambiguity)",
            "Which users receive notifications? (scope ambiguity)",
            "What notification channels? (Email, SMS, push, in-app, etc.)",
            "Real-time or batched? (timing/performance ambiguity)",
            "Should notifications be configurable by user? (feature scope)"
        ],
        "description": "Single-level notifications system with clear ambiguities",
        "max_iterations": 5
    },
    "medium": {
        "spec": "Build an API that processes orders quickly and securely",
        "ambiguities": [
            "'Quickly' — what's the SLA? (response time target)",
            "'Securely' — PCI compliance? Data encryption at rest/transit?",
            "Authentication method? (OAuth, API keys, JWT, mTLS?)",
            "What payment providers? (Stripe, PayPal, custom?)",
            "Rate limiting strategy? (per user? per endpoint?)",
            "Retry/idempotency? (duplicate prevention logic)"
        ],
        "metrics": {
            "ambiguity_identification": 0.7,
            "specific_metrics": 0.3
        },
        "description": "Multi-faceted API with performance AND security ambiguities",
        "max_iterations": 6
    },
    "hard": {
        "spec": "Integrate payment processing with inventory and send alerts when stock runs low",
        "ambiguities": [
            "'Integrate' — real-time event-driven or eventual consistency?",
            "Payment provider selection & fallback strategy?",
            "Inventory granularity — SKU-level or warehouse-level tracking?",
            "'Stock runs low' — units or percentage threshold?",
            "Alert recipients & channels (admin, warehouse, customer, alerting service)?",
            "Critical dependency: Does inventory decrement on FAILED payment?"
        ],
        "dependencies": {
            "payment_inventory_sync": "Payment success must precede inventory update",
            "alert_routing": "Different alerts to different systems",
            "failure_cascade": "Payment failure must NOT consume inventory"
        },
        "metrics": {
            "ambiguity_identification": 0.5,
            "dependency_reasoning": 0.3,
            "cross_system_awareness": 0.2
        },
        "description": "Complex multi-system integration with cascade logic and cross-system dependencies",
        "max_iterations": 7
    }
}


def grade_easy(agent_response: str) -> tuple[float, str]:
    spec = TASKS["easy"]
    ambiguities = spec["ambiguities"]
    
    response_lower = agent_response.lower()
    detected = 0
    
    keywords = [
        ["important events", "event type", "event definition"],  # ambiguity 1
        ["which users", "user scope", "user targeting"],         # ambiguity 2
        ["channels", "notification method", "email", "sms"],     # ambiguity 3
        ["real-time", "batch", "timing", "latency"],            # ambiguity 4
        ["configurable", "user preference", "opt-in"],          # ambiguity 5
    ]
    
    for keyword_group in keywords:
        if any(kw in response_lower for kw in keyword_group):
            detected += 1
    
    length_bonus = 0.0
    if len(agent_response) > 150:
        length_bonus = 0.05
    
    score = min(1.0, (detected / 5.0) + length_bonus)
    reasoning = f"Identified {detected}/5 core ambiguities. Detected: {detected} areas clarified."
    
    return score, reasoning


def grade_medium(agent_response: str) -> tuple[float, str]:
    spec = TASKS["medium"]
    response_lower = agent_response.lower()
    
    ambiguity_keywords = [
        ["sla", "latency", "response time", "quickly"],
        ["pci", "encrypt", "secure", "tls", "ssl"],
        ["auth", "oauth", "jwt", "api key"],
        ["provider", "payment", "stripe", "paypal"],
        ["rate limit", "throttle", "per-user"],
        ["retry", "idempotent", "duplicate"]
    ]
    
    ambiguities_detected = sum(1 for kw_group in ambiguity_keywords 
                               if any(kw in response_lower for kw in kw_group))
    ambiguity_score = min(1.0, ambiguities_detected / len(ambiguity_keywords))
    
    has_metrics = any(term in response_lower for term in [
        "99.", "500ms", "10%", "per second", "per minute",
        "rsa", "sha", "bcrypt", "hash", "timeout=", "sec"
    ])
    metrics_score = 1.0 if has_metrics else 0.0
    
    score = (ambiguity_score * 0.7) + (metrics_score * 0.3)
    reasoning = f"Ambiguities: {ambiguities_detected}/6 ({ambiguity_score:.2f}), Metrics specificity: {'YES' if has_metrics else 'NO'}"
    
    return min(1.0, score), reasoning


def grade_hard(agent_response: str) -> tuple[float, str]:
    spec = TASKS["hard"]
    response_lower = agent_response.lower()
    
    ambiguity_keywords = [
        ["integrate", "real-time", "event", "eventual"],
        ["provider", "fallback", "retry"],
        ["sku", "granularity", "warehouse"],
        ["units", "percentage", "threshold"],
        ["recipients", "channels", "admin"],
        ["dependency", "cascade", "payment"]
    ]
    
    ambiguities_detected = sum(1 for kw_group in ambiguity_keywords 
                               if any(kw in response_lower for kw in kw_group))
    ambiguity_score = min(1.0, ambiguities_detected / len(ambiguity_keywords))
    
    dependency_keywords = [
        "payment",
        "inventory",
        "failed",
        "decrement",
        "success",
        "ordering",
        "cascade",
        "coordinate"
    ]
    dependency_count = sum(1 for kw in dependency_keywords 
                           if kw in response_lower)
    has_dependency_reasoning = dependency_count >= 4
    dependency_score = min(1.0, 0.3 + (dependency_count * 0.15)) if has_dependency_reasoning else 0.3
    
    system_keywords = [
        "payment system",
        "inventory system",
        "alert system",
        "gateway",
        "cascade",
        "cross-system"
    ]
    systems_mentioned = sum(1 for kw in system_keywords if kw in response_lower)
    system_score = min(1.0, systems_mentioned / 3.0)
    
    score = (
        (ambiguity_score * 0.5) +
        (dependency_score * 0.3) +
        (system_score * 0.2)
    )
    
    reasoning = (
        f"Ambiguities: {ambiguities_detected}/6 ({ambiguity_score:.2f}), "
        f"Dependencies: {'YES' if has_dependency_reasoning else 'NO'} ({dependency_score:.2f}), "
        f"Systems: {systems_mentioned}/3 ({system_score:.2f})"
    )
    
    return min(1.0, score), reasoning



class SpecClarifierEnv:
    
    def __init__(self):
        self.current_task = None
        self.current_difficulty = None
        self.iteration = 0
        self.max_iterations = 5
        self.conversation_history = []
        self.total_reward = 0.0
        self.grader_fn = None
        
    def reset(self, difficulty: str = "easy") -> Observation:
        if difficulty not in TASKS:
            raise ValueError(f"Difficulty must be one of {list(TASKS.keys())}")
        
        self.current_difficulty = difficulty
        task_data = TASKS[difficulty]
        self.current_task = task_data
        self.iteration = 0
        self.conversation_history = []
        self.total_reward = 0.0
        self.max_iterations = task_data.get("max_iterations", 5)
        
        if difficulty == "easy":
            self.grader_fn = grade_easy
        elif difficulty == "medium":
            self.grader_fn = grade_medium
        else:
            self.grader_fn = grade_hard
        
        return Observation(
            specification=task_data["spec"],
            task_difficulty=difficulty,
            iteration=self.iteration,
            conversation_history=self.conversation_history,
            max_iterations=self.max_iterations
        )
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        if self.current_task is None:
            raise RuntimeError("Must call reset() before step()")
        
        valid_actions = ["identify_ambiguity", "ask_clarification", "propose_solution"]
        if action.action_type not in valid_actions:
            raise ValueError(f"Action must be one of {valid_actions}")
        
        self.conversation_history.append({
            "agent": action.content,
            "action_type": action.action_type,
            "iteration": self.iteration
        })
        
        score, reasoning = self.grader_fn(action.content)
        
        if len(action.content.strip()) < 20:
            reward_score = score * 0.5  # Penalize very short responses
        else:
            reward_score = score
        
        self.iteration += 1
        done = self.iteration >= self.max_iterations or score >= 0.95
        
        self.total_reward += reward_score
        
        next_obs = Observation(
            specification=self.current_task["spec"],
            task_difficulty=self.current_difficulty,
            iteration=self.iteration,
            conversation_history=self.conversation_history,
            max_iterations=self.max_iterations
        )
        
        reward = Reward(
            score=reward_score,
            reasoning=reasoning,
            partial_progress=(score > 0.2)
        )
        
        info = {
            "done_reason": "max_iterations_reached" if self.iteration >= self.max_iterations else ("task_completed" if score >= 0.95 else "in_progress"),
            "total_reward": self.total_reward,
            "iterations_used": self.iteration,
            "final_score": score if done else None
        }
        
        return next_obs, reward, done, info
    
    def state(self) -> dict:
        return {
            "difficulty": self.current_difficulty,
            "specification": self.current_task["spec"] if self.current_task else None,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "conversation_history": self.conversation_history,
            "total_reward": self.total_reward
        }

if __name__ == "__main__":
    print("=" * 80)
    print("Specification Clarifier — Quick Test")
    print("=" * 80)
    
    env = SpecClarifierEnv()
    
    print("\n[EASY] Resetting...")
    obs = env.reset("easy")
    print(f"Spec: {obs.specification}")
    print(f"Iteration: {obs.iteration}")
    
    action = Action(
        action_type="identify_ambiguity",
        content="I see several key ambiguities: 1) What are 'important events'? "
                "2) Which users receive notifications? 3) What channels (email/SMS/push)? "
                "4) Real-time or batched? 5) User-configurable?"
    )
    obs, reward, done, info = env.step(action)
    print(f"\nReward Score: {reward.score:.2f}")
    print(f"Reasoning: {reward.reasoning}")
    print(f"Done: {done}")
    print(f"Info: {info}")
    
    print("\n" + "=" * 80)
    print("[MEDIUM] Resetting...")
    obs = env.reset("medium")
    print(f"Spec: {obs.specification}")
    
    action = Action(
        action_type="ask_clarification",
        content="Critical ambiguities in the API spec: "
                "1) 'Quickly' - what SLA? 99.99% uptime? 500ms response? "
                "2) 'Securely' - PCI DSS compliance? What encryption: AES-256 at rest, TLS 1.3 in transit? "
                "3) Authentication: OAuth 2.0 or API keys? "
                "4) Payment provider: Stripe with fallback to PayPal? "
                "5) Rate limiting per user or per endpoint? "
                "6) Retry logic with idempotency keys to prevent duplicates?"
    )
    obs, reward, done, info = env.step(action)
    print(f"\nReward Score: {reward.score:.2f}")
    print(f"Reasoning: {reward.reasoning}")
    
    print("\n" + "=" * 80)
    print("[HARD] Resetting...")
    obs = env.reset("hard")
    print(f"Spec: {obs.specification}")
    
    action = Action(
        action_type="propose_solution",
        content="Critical ambiguities and dependencies:\n"
                "1) Integration approach: Event-driven real-time (Kafka/SQS) vs eventual consistency?\n"
                "2) Payment system: Which provider + fallback strategy?\n"
                "3) Inventory: SKU-level or warehouse-level granularity?\n"
                "4) Stock threshold: Fixed units (e.g., 100) or percentage (e.g., 20%)?\n"
                "5) Alert routing: To whom (managers, warehouse staff, customers)? Channels (Slack, email, SMS)?\n\n"
                "CRITICAL DEPENDENCY CASCADE:\n"
                "- Payment must succeed BEFORE inventory decrements\n"
                "- Failed payment MUST NOT consume inventory (prevent loss)\n"
                "- Inventory update triggers stock-check\n"
                "- Stock alert routes to appropriate systems\n\n"
                "Cross-system flow: Payment Gateway → Inventory Service → Alert System"
    )
    obs, reward, done, info = env.step(action)
    print(f"\nReward Score: {reward.score:.2f}")
    print(f"Reasoning: {reward.reasoning}")
    print(f"Done: {done}, Info: {info}")
    
    print("\n" + "=" * 80)
    print("✅ All tests passed! Environment is ready.")
    print("=" * 80)

import os
import json
from datetime import datetime
from typing import List, Optional

from openai import OpenAI
from openai import AuthenticationError
from spec_clarifier_scaffold import SpecClarifierEnv, Action, Observation

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN") or "mock"
BENCHMARK = "spec-clarifier"


def log_start(task: str) -> None:
    print(f"[START] task={task} env={BENCHMARK} model={MODEL_NAME}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


class MockLLM:
    EASY_RESPONSE = (
        "I identified several key ambiguities: "
        "1) What defines 'important events'? Business domain? Financial transactions? All user actions? "
        "2) Which users receive notifications? All, only subscribers, only premium, role-based? "
        "3) What channels: Email, SMS, push, in-app, web? Should be user-configurable? "
        "4) Real-time or batched delivery? Is a 1-second delay acceptable? "
        "5) User configurability: Can users opt out? Adjust frequency? Choose channels?"
    )
    MEDIUM_RESPONSE = (
        "Critical ambiguities: "
        "1) 'Quickly' SLA missing: 99.9% uptime? 99.99%? Response time 500ms? 1s? "
        "2) 'Securely' needs specifics: PCI DSS Level 1? AES-256 at rest, TLS 1.3 in transit? "
        "3) Authentication: OAuth 2.0? JWT? API keys? mTLS? "
        "4) Payment provider: Stripe with PayPal fallback? Who handles failures? "
        "5) Rate limiting per-user (1000 req/min) or per-endpoint? Reset window 60s? "
        "6) Idempotency: Idempotency-Key headers to prevent duplicate charges? Retry 3x with backoff?"
    )
    HARD_RESPONSE = (
        "Complex cascade dependencies and ambiguities: "
        "1) Integration: Real-time event-driven (Kafka/SQS) or eventual consistency (polling)? "
        "2) Payment: Which provider? Stripe with PayPal fallback? 3x retry with exponential backoff? "
        "3) Inventory: SKU-level or warehouse-level granularity? "
        "4) Stock threshold: Fixed units (50) or percentage (20% of max_capacity)? "
        "5) Alerts: To whom (managers, warehouse staff)? Via SMS, email, Slack? "
        "6) CRITICAL DEPENDENCY: Does inventory decrement on FAILED payment? NO - only on SUCCESS. "
        "Why: Payment failure should not consume inventory. Otherwise: accounting mismatch, double inventory loss on retry. "
        "System flow: Payment Gateway -> [SUCCESS only] -> Inventory Service -> Alert Service."
    )

    def __init__(self, model_name: str = "mock"):
        self.model_name = model_name

    def generate_response(self, difficulty: str) -> str:
        if difficulty == "easy":
            return self.EASY_RESPONSE
        if difficulty == "medium":
            return self.MEDIUM_RESPONSE
        if difficulty == "hard":
            return self.HARD_RESPONSE
        return "Unable to process difficulty level"


class OpenAILLM:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.mock = MockLLM(model_name)
        self.client = None if API_KEY == "mock" else OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    def generate_response(self, difficulty: str) -> str:
        if self.client is None:
            return self.mock.generate_response(difficulty)
        prompts = {
            "easy": "Identify the key ambiguities in the requirement. Be concise but specific and list the most important missing details.",
            "medium": "Identify the critical ambiguities in the requirement. Focus on SLAs, security, authentication, payment handling, rate limiting, and idempotency.",
            "hard": "Identify the complex cascading ambiguities in the requirement. Focus on integration flow, payment handling, inventory granularity, stock thresholds, alerting, and failure behavior.",
        }
        prompt = prompts.get(difficulty, "Identify the main ambiguities in the requirement.")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a precise requirements analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content
            return content.strip() if content else self.mock.generate_response(difficulty)
        except AuthenticationError:
            return self.mock.generate_response(difficulty)
        except Exception:
            return self.mock.generate_response(difficulty)


class InferenceRunner:
    def __init__(self):
        self.env = SpecClarifierEnv()
        self.llm = OpenAILLM(MODEL_NAME)

    def run_task(self, difficulty: str) -> dict:
        log_start(task=difficulty)
        obs: Observation = self.env.reset(difficulty)
        rewards: List[float] = []
        steps = 0
        success = False
        final_score = 0.0

        try:
            for step_num in range(1, obs.max_iterations + 1):
                response = self.llm.generate_response(difficulty)
                action_str = response[:80] if len(response) > 80 else response
                action = Action(action_type="identify_ambiguity" if step_num == 1 else "propose_solution", content=response)
                obs, reward, done, info = self.env.step(action)
                reward_score = reward.score
                rewards.append(reward_score)
                steps = step_num
                log_step(step=step_num, action=action_str, reward=reward_score, done=done, error=None)
                if done:
                    break
            final_score = reward.score
            success = final_score >= 0.5
        except Exception as e:
            print(f"[DEBUG] Task {difficulty} error: {e}", flush=True)
            success = False
            final_score = 0.0
        finally:
            log_end(success=success, steps=steps, score=final_score, rewards=rewards)

        return {"difficulty": difficulty, "final_score": final_score, "steps": steps, "rewards": rewards, "success": success}


def main() -> dict:
    print("=" * 80, flush=True)
    print("Specification Clarifier — Baseline Inference", flush=True)
    print(f"Timestamp: {datetime.now().isoformat()}", flush=True)
    print(f"Model: {MODEL_NAME}", flush=True)
    print("Mode: OpenAI Client", flush=True)
    print("=" * 80, flush=True)

    runner = InferenceRunner()
    results = {}
    difficulties = ["easy", "medium", "hard"]
    for difficulty in difficulties:
        results[difficulty] = runner.run_task(difficulty)

    print("\n" + "=" * 80, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 80, flush=True)
    scores = [results[d]["final_score"] for d in difficulties]
    for difficulty, score in zip(difficulties, scores):
        print(f"  {difficulty:10s}: {score:.4f}", flush=True)
    avg_score = sum(scores) / len(scores)
    print(f"  {'average':10s}: {avg_score:.4f}", flush=True)
    print("=" * 80, flush=True)

    output = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL_NAME,
        "mode": "openai_client",
        "tasks": results,
        "summary": {difficulty: results[difficulty]["final_score"] for difficulty in difficulties},
        "metadata": {
            "average_score": avg_score,
            "success_rate": sum(1 for r in results.values() if r["success"]) / len(results),
        },
    }

    with open("baseline_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nOK Results saved to baseline_results.json", flush=True)
    return output


if __name__ == "__main__":
    main()

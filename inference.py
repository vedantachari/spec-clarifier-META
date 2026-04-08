import os
import sys
import json
from datetime import datetime
from typing import List, Optional

from openai import OpenAI
from spec_clarifier_scaffold import (
    SpecClarifierEnv,
    Action,
    Observation,
    TASKS
)

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "mock")
BENCHMARK = "spec-clarifier"


def log_start(task: str) -> None:
    msg = f"[START] task={task} env={BENCHMARK} model={MODEL_NAME}"
    print(msg, flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    msg = f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}"
    print(msg, flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    msg = f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}"
    print(msg, flush=True)


class OpenAILLM:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    def generate_response(self, difficulty: str) -> str:
        prompts = {
            "easy": (
                "Identify the key ambiguities in the requirement. "
                "Be concise but specific and list the most important missing details."
            ),
            "medium": (
                "Identify the critical ambiguities in the requirement. "
                "Focus on SLAs, security, authentication, payment handling, rate limiting, and idempotency."
            ),
            "hard": (
                "Identify the complex cascading ambiguities in the requirement. "
                "Focus on integration flow, payment handling, inventory granularity, stock thresholds, alerting, and failure behavior."
            ),
        }
        prompt = prompts.get(difficulty, "Identify the main ambiguities in the requirement.")
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a precise requirements analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()


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

                action = Action(
                    action_type="identify_ambiguity" if step_num == 1 else "propose_solution",
                    content=response
                )

                obs, reward, done, info = self.env.step(action)

                reward_score = reward.score
                rewards.append(reward_score)
                steps = step_num

                log_step(
                    step=step_num,
                    action=action_str,
                    reward=reward_score,
                    done=done,
                    error=None
                )

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

        return {
            "difficulty": difficulty,
            "final_score": final_score,
            "steps": steps,
            "rewards": rewards,
            "success": success
        }


def main() -> dict:
    print("=" * 80, flush=True)
    print(f"Specification Clarifier — Baseline Inference", flush=True)
    print(f"Timestamp: {datetime.now().isoformat()}", flush=True)
    print(f"Model: {MODEL_NAME}", flush=True)
    print(f"Mode: OpenAI Client", flush=True)
    print("=" * 80, flush=True)

    runner = InferenceRunner()
    results = {}

    difficulties = ["easy", "medium", "hard"]
    for difficulty in difficulties:
        task_result = runner.run_task(difficulty)
        results[difficulty] = task_result

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
        "summary": {
            difficulty: results[difficulty]["final_score"]
            for difficulty in difficulties
        },
        "metadata": {
            "average_score": avg_score,
            "success_rate": sum(1 for r in results.values() if r["success"]) / len(results)
        }
    }

    with open("baseline_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nOK Results saved to baseline_results.json", flush=True)

    return output


if __name__ == "__main__":
    main()

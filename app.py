import json
import os

import gradio as gr

from inference import MODEL_NAME, MockLLM, OpenAILLM
from spec_clarifier_scaffold import Action, SpecClarifierEnv, TASKS


def get_llm(use_openai: bool):
    if use_openai:
        return OpenAILLM(MODEL_NAME)
    return MockLLM(MODEL_NAME)


def evaluate_task(difficulty: str, response: str, action_type: str):
    env = SpecClarifierEnv()
    obs = env.reset(difficulty)
    action = Action(action_type=action_type, content=response)
    next_obs, reward, done, info = env.step(action)
    return (
        obs.specification,
        json.dumps(obs.model_dump(), indent=2),
        json.dumps(next_obs.model_dump(), indent=2),
        f"{reward.score:.2f}",
        reward.reasoning,
        str(done).lower(),
        json.dumps(info, indent=2),
    )


def run_with_text(difficulty: str, response: str, action_type: str):
    return evaluate_task(difficulty, response, action_type)


def generate_and_evaluate(difficulty: str, use_openai: bool):
    llm = get_llm(use_openai)
    response = llm.generate_response(difficulty)
    action_type = "identify_ambiguity" if difficulty != "hard" else "propose_solution"
    return evaluate_task(difficulty, response, action_type) + (response,)


def run_baseline(use_openai: bool):
    llm = get_llm(use_openai)
    lines = []
    results = {}
    for difficulty in ["easy", "medium", "hard"]:
        env = SpecClarifierEnv()
        env.reset(difficulty)
        response = llm.generate_response(difficulty)
        action = Action(action_type="identify_ambiguity", content=response)
        _, reward, done, info = env.step(action)
        results[difficulty] = reward.score
        lines.append(f"{difficulty}: score={reward.score:.2f}, done={str(done).lower()}, reasoning={reward.reasoning}")
    avg = sum(results.values()) / len(results)
    lines.append(f"average: {avg:.3f}")
    return "\n".join(lines), json.dumps(results, indent=2)


def build_demo():
    with gr.Blocks() as demo:
        gr.Markdown("# Specification Clarifier")
        gr.Markdown("Inspect ambiguous requirements and score a clarification response.")

        with gr.Row():
            difficulty = gr.Dropdown(choices=["easy", "medium", "hard"], value="easy", label="Task")
            use_openai = gr.Checkbox(value=True, label="Use OpenAI client when configured")

        response = gr.Textbox(lines=8, label="Agent response", placeholder="Type a clarification response here")
        action_type = gr.Dropdown(
            choices=["identify_ambiguity", "ask_clarification", "propose_solution"],
            value="identify_ambiguity",
            label="Action type",
        )

        with gr.Row():
            evaluate_btn = gr.Button("Evaluate response")
            generate_btn = gr.Button("Generate and evaluate")
            baseline_btn = gr.Button("Run baseline")

        spec = gr.Textbox(label="Specification")
        observation_before = gr.Textbox(lines=10, label="Initial observation")
        observation_after = gr.Textbox(lines=10, label="Observation after step")
        score = gr.Textbox(label="Score")
        reasoning = gr.Textbox(label="Reasoning")
        done = gr.Textbox(label="Done")
        info = gr.Textbox(lines=8, label="Info")
        baseline_summary = gr.Textbox(lines=6, label="Baseline summary")
        baseline_json = gr.Textbox(lines=8, label="Baseline JSON")

        evaluate_btn.click(
            fn=run_with_text,
            inputs=[difficulty, response, action_type],
            outputs=[spec, observation_before, observation_after, score, reasoning, done, info],
        )

        def generate_and_fill(difficulty_value, use_openai_value):
            result = generate_and_evaluate(difficulty_value, use_openai_value)
            return result[:-1], result[-1]

        generate_btn.click(
            fn=generate_and_fill,
            inputs=[difficulty, use_openai],
            outputs=[
                spec,
                observation_before,
                observation_after,
                score,
                reasoning,
                done,
                info,
                response,
            ],
        )

        baseline_btn.click(
            fn=run_baseline,
            inputs=[use_openai],
            outputs=[baseline_summary, baseline_json],
        )

    return demo


app = build_demo()


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))

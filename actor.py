from groq import Groq
import time
import copy
from flaml import oai
import openai

class ActorAgent:
    def __init__(self, model, temperature=0.5):
        # self.client = client
        self.model = model
        # self.temperature = temperature
        self.system_prompt = str(
            """
            You are an innovative math problem solver tasked with creating a detailed plan to solve the provided math problem.
            Your plan must:
            1. Break down the problem into clear, logical, step-by-step actions.
            2. Explain every assumption and justify any use of hardcoded values.
            3. Include Python code snippets only if they are essential for demonstrating the solution.
            4. Explicitly note any uncertainties or alternative approaches.
            5. Be structured and easy to follow, ensuring that no steps are vague or skipped.
            """
        )

    def generate_plan(self, problem_statement, conversation_history):
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Append conversation history if available
        if conversation_history:
            messages.extend(conversation_history)

        # Append the new problem statement
        messages.append({"role": "user", "content": problem_statement})

        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            # temperature=self.temperature,
        )
        return response.choices[0].message.content
from groq import Groq
import time
from flaml import oai
import openai

class CritiqueAgent:
    def __init__(self, model, temperature=0.5):
        # self.client = client
        self.model = model
        # self.temperature = temperature
        self.system_prompt = str(
            """
                You are a math expert tasked with reviewing and refining the problem-solving plan created by another AI assistant.
                Your responsibilities are to:
                1. Verify that the plan is structured, logical, and complete.
                2. Identify and question any vague steps, unexplained assumptions, or hardcoded values.
                3. Check that any Python code is necessary, correct, and properly integrated.
                4. Ask clarifying questions where any step is ambiguous or could lead to errors.
                5. Provide clear, constructive feedback. If the plan is solid, respond with:
                "Plan Approved. You may start solving the problem."
                Otherwise, explain the issues and suggest improvements.
                Keep your feedback concise, direct, and focused on enhancing the solution.
            """
        )
    
    def critique_plan(self, problem_statement, proposed_plan):
        critique_prompt = f"""
            Given the following math problem:

            {problem_statement}

            The assistant has proposed the following plan:

            {proposed_plan}

            Please review the plan according to your guidelines and provide your feedback. If the plan is acceptable, confirm with "Plan Approved. You may start solving the problem." Otherwise, highlight the issues and suggest specific improvements.
        """
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": critique_prompt}
            ],
            # temperature=self.temperature,
        )
        return response.choices[0].message.content

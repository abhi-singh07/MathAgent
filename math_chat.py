from user_proxy_agent import UserProxyAgent
from flaml.autogen.math_utils import eval_math_responses, get_answer
from flaml import oai
import os
import json
import re
import copy
from utils import write_json, remove_asy_sections, math_type_mapping, mylogger
from prompts import PROMPTS
from groq import Groq
import groq_utils
from critique import CritiqueAgent
from actor import ActorAgent

class MathChat:
    def __init__(
        self,
        # client,
        model,
        prompt_type="select",
        prompt_location="user",
        sys_type="s0",
        max_round=10,
        max_invalid_q_per_step=3,
        n=1,
        # temperature=1,
        logger=None,
        use_cache=True,
        refine=False,
        config_list=None,
    ):
        # self.groq_client = client
        self.max_round = max_round
        if prompt_type not in PROMPTS:
            raise ValueError(f"Tool {prompt_type} not supported, choose from {PROMPTS.keys()}")

        self.prompt_type = prompt_type
        self.prompt_location = prompt_location
        self.prompt = PROMPTS[prompt_type]
        self.refine = refine

        # if the prompt_location is set to system, then the prompt is put in the system message
        self.sys_type = sys_type
        sys_choices = {
            "s0": "You are a helpful assistant.",
        }
        messages = (
            [{"role": "system", "content": self.prompt}]
            if prompt_location == "system"
            else [
                {
                    "role": "system",
                    "content": sys_choices[sys_type],
                }
            ]
        )
        self.deafult_config = {
            "model": model,
            "messages": messages,
            # "n": n,  # n should be 1 for now
            # "temperature": temperature,
        }

        self.max_invalid_q_per_step = max_invalid_q_per_step
        self.use_cache = use_cache
        self.logger = logger
        self.config_list = config_list
        self.model = model
        # self.temperature = temperature

        self.actor = ActorAgent(self.model)

        # Critique uses the same model as math agent (Can change in future)
        self.critique = CritiqueAgent(self.model)

    def make_conversation(self, problem, n=1, file_to_be_saved=None):
        # initialize the query handler
        proxy_agent = UserProxyAgent()

        conversation_history = []

        if self.prompt_location == "system":
            conversation_history.append({"role": "system", "content": self.prompt})
        
        # Append problem statement as a user message if required
        if self.prompt_location != "system":
            conversation_history.append({"role": "user", "content": self.prompt + "\nProblem: " + remove_asy_sections(problem["problem"])})
        else:
            conversation_history.append({"role": "user", "content": remove_asy_sections(problem["problem"])})
        
        # # initialize the conversation
        # config = copy.deepcopy(self.deafult_config)
        # problem_prompt = {
        #     "role": "user",
        #     "content": self.prompt + "\nProblem: " + remove_asy_sections(problem["problem"]),
        # }  # put prompt in user message

        # # if the prompt_location is set to system, then the prompt is already put in the system message in __init__,
        # # then we only need to put the problem in the user message
        # if self.prompt_location == "system":
        #     problem_prompt = {"role": "user", "content": remove_asy_sections(problem["problem"])}
        # config["messages"].append(problem_prompt)

        # save a readable conversation in txt file
        def save_message_to_file(message):
            if file_to_be_saved is not None:
                with open(file_to_be_saved, "a") as f:
                    f.write(message)
                    f.flush()

        separate_line = "\n" + "-" * 40 + "\n"
        # save the conversation history to the file
        save_message_to_file(f'Problem: {self.str_splitter(remove_asy_sections(problem["problem"]))}\n {separate_line}')

        # for additional refine process
        is_refine_process = False
        response_with_new_ans = ""  # save the corrected answer

        # init parameters
        is_valid_reply = False  # only valid when detect \box
        invalid_q = 0  # for query
        response_with_ans = ""  # save the response with \box to get the answer
        rr = 0  # round
        total_completion_tokens = 0

        is_approved_by_critique = False
        while rr < self.max_round:
            # 1. get the response from the assistant, handle exceptions
            actor_response = self.actor.generate_plan(remove_asy_sections(problem["problem"]), conversation_history)
            save_message_to_file(f"assistant: {self.str_splitter(actor_response)}{separate_line}")
            
            # raw_responses = self.groq_client.chat.completions.create(
            #     messages=config["messages"],
            #     model=self.model,
            #     temperature=self.temperature,
            # )
            # # print(raw_responses)
            # total_completion_tokens += raw_responses.usage.completion_tokens
        
            # if raw_responses.usage.completion_tokens >= 8000:
            #     error_str = "Use more than 8000 many tokens, breaking."
            #     print(error_str)
            #     save_message_to_file(error_str)
            #     break

            # responses = groq_utils.extract_text(raw_responses)

            # save_message_to_file(f"assistant: {self.str_splitter(responses[0])}{seperate_line}")

            # 2. Check if critique has given approval
            if not is_approved_by_critique:
                critique_response = self.critique.critique_plan(remove_asy_sections(problem["problem"]), actor_response)
                save_message_to_file(f"critique: {self.str_splitter(critique_response)}{separate_line}")
                if "plan approved" in critique_response.lower():
                    print("PLAN APPROVED!")
                    is_approved_by_critique = True
                conversation_history.append({"role": "assistant", "content": actor_response})
                conversation_history.append({"role": "user", "content": critique_response})
                rr += 1
                continue
                
            # 3. process response
            conversation_history.append({"role": "assistant", "content": actor_response})
            answer = get_answer(actor_response)

            if answer and answer != "":
                proxy_agent = UserProxyAgent()
                tmp_msg, is_query_exist = proxy_agent.check_queries(actor_response)
                if not is_query_exist:
                    # if the assistant gives a valid reply and no more queries, stop the conversation
                    is_valid_reply = True
                    if not self.refine:  # if not refine, stop the conversation
                        response_with_ans = actor_response
                        response_with_new_ans = actor_response
                        break
                    elif not is_refine_process:  # if refine, start the refine process
                        response_with_ans = actor_response
                        is_refine_process = True
                        refine_message = ("Please check your answer to ensure it meets the problem conditions and correct any mistakes. "
                                          "If no mistakes are found, put the previous answer in the box.")
                        conversation_history.append({"role": "user", "content": refine_message})
                        save_message_to_file(f"user: {self.str_splitter(refine_message)}{separate_line}")
                        continue
                    else:  # if already in the refine process, then stop the conversation
                        response_with_new_ans = actor_response
                        break

            # 4. handle the response and get the query
            proxy_agent = UserProxyAgent()
            query_response, is_query_success = proxy_agent.handle_query(actor_response)
            if len(query_response) > 2000:
                save_message_to_file("****: Replacing long query response****\n")
                query_response = ("Your requested query response is too long. Please revise your reasoning "
                                  "and simplify your query.")
                is_query_success = False

            if is_query_success:
                conversation_history.append({"role": "user", "content": query_response})
            else:
                invalid_q += 1
                if invalid_q >= self.max_invalid_q_per_step:
                    skip_query_str = ("Please revisit the problem statement and your reasoning. "
                                      "If you think this step is correct, solve it yourself and continue to the next step. "
                                      "Otherwise, correct this step.")
                    conversation_history.append({"role": "user", "content": skip_query_str})
                    invalid_q = 0
            save_message_to_file(f"user: {self.str_splitter(query_response)}{separate_line}")

            if "Continue" in query_response:
                rr -= 0.5
            rr += 1
        save_message_to_file("Solution: " + problem["solution"])

        # print("SOLVED ONE PROBLEM")
        return {
            "total_completion_tokens": total_completion_tokens,
            "valid_q_count": proxy_agent.valid_q_count if proxy_agent else 0,
            "total_q_count": proxy_agent.total_q_count if proxy_agent else 0,
            "is_valid_reply": is_valid_reply,
            "response_with_ans": response_with_ans,
            "response_with_new_ans": response_with_new_ans,
            "messages": conversation_history,
            "round": min(rr + 1, self.max_round),
        }

    def str_splitter(self, string, length=300):
        """
        Add '\n' every 'length' characters to make the output more readable.
        If at 'length' there is a word, add '\n' before the word.

        Args:
            string (str): The input string to be processed.
            length (int): The maximum number of characters in a line before adding a newline.

        Returns:
            str: The processed string with newlines added.
        """

        words = string.split(" ")
        current_line = []
        current_length = 0
        result = []

        for word in words:
            if current_length + len(word) + len(current_line) > length:
                result.append(" ".join(current_line))
                current_line = []
                current_length = 0

            current_line.append(word)
            current_length += len(word)

        if current_line:
            result.append(" ".join(current_line))

        return "\n".join(result)

    def solve_one_category(self, problem_set, saving_folder):
        """
        Solve all problems in a category.
        Assumption 1: all problems are of the same type
        Assumption 2: if resume from a previous run, the sequence of problems are the same as the previous run, using same shuffling seed

        Args:
            problem_set (list): a list of problems
            saving_folder (str): the result folder to save the solved problems, the category folder will be created inside

        Returns:
            None
        """
        if not self.logger:
            self.logger = mylogger(os.path.join(saving_folder, "log.txt"))

        # assume all problems are of the same type: TODO: ensure this assumption
        saving_folder = os.path.join(saving_folder, math_type_mapping[problem_set[0]["type"]])
        # mkdir if not exist
        os.makedirs(saving_folder, exist_ok=True)

        # from the saving folder load solved problems
        done_problems = set([int(f.split(".")[0]) for f in os.listdir(saving_folder) if "json" in f])

        correct_counts = 0
        self.logger.log("id : is_correct $ ans $ correct_ans | corrected_ans $ round")
        for count, problem in enumerate(problem_set):
            problem_path = os.path.join(saving_folder, problem["problem_id"] + ".json")

            # 1. if problem already solved, continue
            if int(problem["problem_id"]) in done_problems:
                problem = json.load(open(problem_path, "r"))
                correct_counts += problem["is_correct"]
                new_ans = problem["new_ans"] if "new_ans" in problem else ""
                if problem["new_ans"] == problem["voted_answer"]:
                    problem["new_ans"] = "same"
                self.logger.log(
                    f'{problem["problem_id"]} : {bool(problem["is_correct"])} $ {problem["voted_answer"]} $ '
                    f'{problem["correct_ans"]} | {new_ans} $ {problem["round"]} $ (from previous run)'
                )
                continue

            # 2. solve the problem
            result = self.make_conversation(
                problem, file_to_be_saved=os.path.join(saving_folder, problem["problem_id"] + ".txt")
            )
            metrics = eval_math_responses([result["response_with_ans"]], problem["solution"])

            # 3. save the result
            correct_ans = get_answer(problem["solution"])
            problem.update(
                {
                    "is_valid_reply": result["is_valid_reply"],
                    "is_correct": bool(metrics["success_vote"]),
                    "correct_ans": correct_ans,
                    "voted_answer": get_answer(metrics["voted_answer"]),
                    "new_ans": get_answer(result["response_with_new_ans"]),
                    "round": result["round"],
                    "valid_q_count": result["valid_q_count"],  # total number of valid queries
                    "total_q_count": result["total_q_count"],  # total number of queries
                    "messages": result["messages"],  # the conversation
                    "total_completion_tokens": result["total_completion_tokens"],
                }
            )
            write_json(problem, problem_path)
            if problem["new_ans"] == problem["voted_answer"]:
                problem["new_ans"] = "same"

            # 4. continue to next problem
            correct_counts += problem["is_correct"]
            self.logger.log(
                f'{problem["problem_id"]} : {bool(problem["is_correct"])} $ {problem["voted_answer"]} $ '
                f'{problem["correct_ans"]} | {problem["new_ans"]} $ {problem["round"]} $'
            )

        tp = problem_set[0]["type"]
        self.logger.log(f"{tp} Accuracy: {correct_counts}/{len(problem_set)} = {correct_counts/len(problem_set)}")
        self.logger.log("------------------------------------------------------------\n", verbose=True)
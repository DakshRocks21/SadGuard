import os
import dotenv
import google.generativeai as genai
from typing import List, Dict, Optional, Callable

dotenv.load_dotenv()
API_KEY = os.environ['GOOGLE_AI_STUDIO_KEY']

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def get_review(title: str, body: str, filename: str, diff: str) -> str:
    """Passes the code diff through an LLM and returns the LLM's response

    Args:
        title (str): The title of the pull request.
        body (str): The body of the pull request.
        filename (str): The name of the changed file
        diff (str): The diff in the pull request.

    Returns:
        str: The LLM's response as a string.
    """

    prompt = f"""===== PROMPT =====
You are a VULNERABILITY and MALWARE DETECTION expert. Analyze the code snippet and its associated GitHub commit description to ensure it:
Performs as described: Verify the code matches the commit message.
Detects issues: Identify vulnerabilities, unintended behavior, or malicious actions, highlighting severity and providing recommendations.
Summarizes in markdown: Provide a markdown-formatted summary of the code functionality.
Highlights problems: Clearly explain any unintended or malicious actions and suggest fixes.

BOLD some words for emphasis key points. (e.g., **vulnerability**)
Keep it concise without sacrificing brevity to make things easier for the reviewer to understand.
Do not output a title as it will be manually added in later.

If vulnerabilities are found: provide a report of the code functionality, the detected vulnerabilities. 

You are also given the pull request title and body, which usually contains context about the changes made.
If you need more context, DO NOT ASK.

DO NOT talk about the commit message or the author of the commit.

===== PULL REQUEST INFORMATION =====
PR Title: {title}
PR Body: {body}

===== CODE DIFF FOR {filename} =====
{diff}"""

    response = model.generate_content(prompt)
    return response.text

def get_network_analysis_output(output:str) -> str:
    """Analyzes the output of a network analysis script in a Docker container
    
    Returns:
        str: The output of the network analysis script.
    """
    print("analyzing network output")
    print("output:",output)
    prompt = f"""===== PROMPT =====
You are a NETWORK ANALYSIS expert. Analyze the output of the network analysis script to ensure it:
- Performs as described: Verify the script matches the expected output.
- Detects issues: Identify vulnerabilities, unintended behavior, or malicious actions, highlighting severity and providing recommendations.
- Summarizes in markdown: Provide a markdown-formatted summary of the script functionality.
- Highlights problems: Clearly explain any unintended or malicious actions and suggest fixes.

If anything is missing or unclear, DO NOT ASK for more information. Instead, just say not enough information to analyze.

===== NETWORK ANALYSIS OUTPUT =====
{output}"""

    response = model.generate_content(prompt)
    return response.text


def orchestrate_review_loop(
    pr_title: str,
    pr_body: str,
    diffs: List[Dict[str, str]],
    run_results: Optional[str] = None,
    analysis_results: Optional[str] = None,
    questions: Optional[List[str]] = None,
    max_iterations: int = 3,
    store_callback: Optional[Callable[[int, str], None]] = None,
) -> List[Dict[str, str]]:
    """
    Run an iterative LLM-driven review loop.

    - diffs: list of {"filename": str, "diff": str}
    - store_callback: optional function(iteration:int, content:str) to persist each LLM response

    Returns a list of review dicts: [{"iteration": i, "content": str, "action_requested": bool}]
    """
    results = []
    previous_reviews = []

    for i in range(1, max_iterations + 1):
        snippets = []
        for d in diffs:
            snippets.append(f"===== FILE: {d.get('filename')} =====\n{d.get('diff')}\n")

        prompt_parts = [
            "You are a VULNERABILITY and MALWARE DETECTION expert. Continue the iterative review based on the context provided.",
            f"PR Title: {pr_title}",
            f"PR Body: {pr_body}",
        ]

        if previous_reviews:
            prompt_parts.append("Previous reviews:\n" + "\n---\n".join(previous_reviews))

        prompt_parts.append("Code diffs:\n" + "\n".join(snippets))

        if run_results:
            prompt_parts.append("Sandbox run results:\n" + run_results)
        if analysis_results:
            prompt_parts.append("Analysis results:\n" + analysis_results)

        # Add explicit agentic questions for the LLM to answer in each iteration
        if questions:
            qblock = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(questions)])
            prompt_parts.append("Answer the following questions concisely and with recommended actions:\n" + qblock)

        prompt_parts.append(
            "Provide a concise markdown review. For each question above, include a short answer. At the END of your reply include a single line that starts with 'ACTION:' followed by one of the following tokens (lowercase): 're-run', 're-run-sandbox', 're-run-code', 'none', or 'escalate'. Example: ACTION: none\n\nIf you want another iteration, use 're-run' or the more specific 're-run-sandbox'/'re-run-code'. If no further iterations are needed, use 'ACTION: none'."
        )

        prompt = "\n\n".join(prompt_parts)
        resp = model.generate_content(prompt)
        text = resp.text

        # store via callback if provided
        if store_callback:
            try:
                store_callback(i, text)
            except Exception:
                pass

        previous_reviews.append(text)

        # Parse explicit ACTION: line for deterministic control
        import re
        action = 'none'
        m = re.search(r'(?m)^ACTION:\s*(.+)$', text)
        if m:
            action = m.group(1).strip().lower()
        else:
            # fallback: try to infer, but default to 'none' for safety
            action = 'none'

        results.append({"iteration": i, "content": text, "action": action})
        print(f"Iteration {i} complete. ACTION: {action}")

        # Continue only if ACTION indicates re-run
        if action == 'none' or action == 'escalate':
            print("No further automated iterations requested (ACTION: none or escalate). Ending review loop.")
            break

    return results

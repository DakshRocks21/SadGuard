import os
import dotenv
import google.generativeai as genai

dotenv.load_dotenv()
API_KEY = os.environ['GOOGLE_AI_STUDIO_KEY']

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

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

===== PULL REQUEST INFORMATION =====
PR Title: {title}
PR Body: {body}

===== CODE DIFF FOR {filename} =====
{diff}"""

    response = model.generate_content(prompt)
    return response.text

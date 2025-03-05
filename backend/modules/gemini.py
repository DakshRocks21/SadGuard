import google.generativeai as genai
import os
import dotenv
dotenv.load_dotenv("../.env")

MAKERSUITE_API_KEY = os.environ['GOOGLE_AI_STUDIO_KEY']


genai.configure(api_key=MAKERSUITE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def prompt_gemini(prompt):
    response = model.generate_content(prompt, request_options={"timeout": 600})
    return response.text


if __name__ == "__main__":
    response = model.generate_content("Explain how AI works")
    print(response.text)

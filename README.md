# SadGuard

Very self hosted

## Installation

Create a `.env` file as well as a `private.pem` file in the root directory of the project.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Set up the webhook

```bash
sudo apt update
sudo apt install cloudflared

cloudflared tunnel --url http://localhost:3000
```

After setup, provide this URL to the github bot settings page.

## Set up the LLM

1. Head to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) to obtain a Google AI Studio API key
2. In the `.env` file, add an entry named `GOOGLE_AI_STUDIO_KEY` with the newly created API key

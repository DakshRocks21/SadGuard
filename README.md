# SadGuard

> Part 2 of our other project [VulnGuard](https://github.com/DakshRocks21/VulnGuard), 

An AI-powered, self-hosted GitHub bot designed to detect and mitigate supply chain attacks in pull requests.
SadGuard combines intelligent code analysis with executable behavior monitoring to secure your software pipeline.

SadGuard was inspired by the growing threat of supply chain attacks, such as the recent high-profile
incident involving xz-utils. These attacks exploit trust in open-source contributions, embedding
vulnerabilities that can have widespread consequences.

## Features

1. Code Diff Analysis with AI
   - Leverages state-of-the-art LLMs to analyze pull request code diffs for vulnerabilities and suspicious patterns.  
   - Automatically adds insightful comments to PR threads, aiding reviewers in identifying potential threats.

2. Sandboxed Executable Analysis
   - Isolates executable files for runtime behavior analysis.  
   - Logs spawned processes to look for suspicious activity.

3. Entropy Analysis
   - Scans binary files for high-entropy data, which may indicate obfuscation or embedded secrets.

4. Self-Hosted Solution
   - Complete control of your security infrastructure. SadGuard runs locally, keeping sensitive data within your environment.

## Why SadGuard?

1. Proactive Defense: Detects vulnerabilities and malicious patterns in pull requests before they reach production.
2. AI-Powered Insights: Makes code reviews faster and more effective with intelligent comments.
3. Self-Hosted Security: Ensures your sensitive data stays within your infrastructure.

## Future Plans

1. Expand analysis capabilities to detect deeper, more complex supply chain attacks.
2. Introduce a scoring system for threats based on severity and potential impact.
3. Build support for additional LLMs and alternative AI providers for broader compatibility.

---

## 1. Installation

1. Clone the repository

    ```bash
    git clone https://github.com/DakshRocks21/SadGuard.git
    cd SadGuard
    ```

2. Set up the environment

    Create a `.env` file in the root directory with the following variables:

    ```bash
    GITHUB_APP_ID=<Obtained from creating a GitHub bot>
    GITHUB_PRIVATE_KEY_PATH=<File path to the .pem file from the Github bot>
    GITHUB_WEBHOOK_SECRET=<User-defined secret at the bots configuration page>
    GOOGLE_AI_STUDIO_KEY=<Refer to the LLM configuration section>
    ```

3. Install dependencies and run SadGuard

    database
    ```bash
    docker-compose up --build
    ```
    
    frontend

    ```bash
    cd frontend
    npm i
    npm run dev
    ```

    backend

    ```bash
    python -m venv venv
    source venv/bin/activate
    cd backend
    pip install -r requirements.txt
    pip install pymysql
    python main.py
    ```

## 2. Webhook Configuration

1. Install Cloudflare Tunnel:

    ```bash
    # Apt
    sudo apt update
    sudo apt install cloudflared

    # Homebrew
    brew upgrade
    brew install cloudflared
    ```

2. Set up the tunnel:

    ```bash
    cloudflared tunnel --url http://localhost:3000
    ```

3. Provide the generated URL to the GitHub bot settings page under "Webhook URL"

## 3. LLM Configuration

1. Obtain an API Key from Google AI Studio at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
2. Add the key to your `.env` file

## Contributing

We welcome contributions to SadGuard! Follow these steps to get started:

1. Fork the repository and create a new branch for your changes.
2. Write tests for any new features or updates.
3. Submit a pull request to the develop branch for review.

For major changes, please open an issue to discuss your proposal first.

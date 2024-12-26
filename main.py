from flask import Flask
from webhook.webhook import PRUtils
import threading
import os

from flask import Flask
from webhook.webhook import webhook_app  # Import the Blueprint

app = Flask(__name__)

app.register_blueprint(webhook_app, url_prefix='/webhook')


@app.route('/', methods=['GET'])
def status():
    return "Main Boss App is running!", 200

def run_webhook():
    app.run(host='0.0.0.0', port=3000)

if __name__ == '__main__':
    webhook_thread = threading.Thread(target=run_webhook, daemon=True)
    webhook_thread.start()

    # THIS IS TEMPORARY CODE TO DEMONSTRATE THE FUNCTIONALITY OF THE WEBHOOK
    # @notbowen: Please replace this other code needed to run the app
    while True:
        print("\n=== Main Boss App ===")
        print("1. List open pull requests")
        print("2. Comment on a pull request")
        print("3. Merge a pull request")
        print("4. Close a pull request")
        print("0. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            repo_name = input("Enter repository name (owner/repo): ")
            open_prs = PRUtils.list_open_prs(repo_name=repo_name)
            if open_prs:
                for pr in open_prs:
                    print(f"PR #{pr['number']}: {pr['title']} by {pr['author']}")
            else:
                print("No open pull requests.")

        elif choice == "2":
            repo_name = input("Enter repository name (owner/repo): ")
            pr_number = int(input("Enter pull request number: "))
            comment = input("Enter your comment: ")
            PRUtils.comment(repo_name=repo_name, pr_number=pr_number, comment=comment)
            print(f"Commented on PR #{pr_number}.")

        elif choice == "3":
            repo_name = input("Enter repository name (owner/repo): ")
            pr_number = int(input("Enter pull request number: "))
            commit_message = input("Enter commit message (optional): ")
            commit_message = commit_message or "Merged via Main Boss App"
            PRUtils.merge(repo_name=repo_name, pr_number=pr_number, commit_message=commit_message)
            print(f"PR #{pr_number} merged.")

        elif choice == "4":
            repo_name = input("Enter repository name (owner/repo): ")
            pr_number = int(input("Enter pull request number: "))
            PRUtils.close_pr(repo_name=repo_name, pr_number=pr_number)
            print(f"PR #{pr_number} closed.")

        elif choice == "0":
            print("Exiting Main Boss App...")
            break

        else:
            print("Invalid choice. Please try again.")

from flask import Flask
from utils.webhook import webhook_app
import threading

app = Flask(__name__)

app.register_blueprint(webhook_app, url_prefix='/webhook')

@app.route('/', methods=['GET'])
def status():
    return "Main Boss App is running!", 200

def run_webhook():
    app.run(host='0.0.0.0', port=3001)

run_webhook()

if __name__ == '__main__':
    print("Starting Main Boss App...")
    webhook_thread = threading.Thread(target=run_webhook, daemon=True)
    webhook_thread.start()
    print("Main Boss App started!")

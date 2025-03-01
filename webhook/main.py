
from flask import Flask
from utils.analysis import analysis_bp
from utils.webhook import webhook_app

app = Flask(__name__)
app.register_blueprint(webhook_app, url_prefix='/webhook')
app.register_blueprint(analysis_bp, url_prefix='/api')

@app.route('/', methods=['GET'])
def status():
    return "Main Boss App is running!", 200

def run_webhook():
    app.run(host='0.0.0.0', port=3001)

run_webhook()

# import threading
# if __name__ == '__main__':
#     print("Starting Main Boss App...")
#     webhook_thread = threading.Thread(target=run_webhook, daemon=True)
#     webhook_thread.start()
#     print("Main Boss App started!")

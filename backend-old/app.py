import os
import dotenv
dotenv.load_dotenv("../.env")

from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.sandboxes import sandboxes_bp
from routes.repositories import repos_bp 
from routes.analysis_proxy import analysis_proxy_bp

app = Flask(__name__)
app.secret_key = 'supersecretkey' 


CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(sandboxes_bp, url_prefix='/api')
app.register_blueprint(repos_bp, url_prefix='/api')
app.register_blueprint(analysis_proxy_bp, url_prefix='/api')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

import string
import random

DB_HOST="localhost:3313"
DB_USERNAME="sad"
DB_PASSWORD="password"
DB_NAME="sad"

# random 64 character hex
SECRET_KEY = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

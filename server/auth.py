# auth.py
import inspect
from functools import wraps
from quart import g, request, jsonify
import jwt
import os
from server_conf import JWT_ALGORITHM
from messages import USER_MESSAGES
from db import get_db_instance

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = JWT_ALGORITHM 

def get_user_collection():
    client = get_db_instance()
    mongo_db = client[os.getenv('MONGO_DB')]
    users_collection = mongo_db['users']
    return users_collection

def require_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify(USER_MESSAGES["TOKEN_MISSING"]), 401

        token = auth_header.split(" ")[1]
        try:
            # Decode JWT
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if not payload:
                return jsonify(USER_MESSAGES["INVALID_TOKEN"]), 401
            user_id = payload.get("user_id")
            username = payload.get("username")
            role = payload.get('role')
            
            if not user_id or not username or not role:
                return jsonify(USER_MESSAGES["INVALID_CLAIMS"]), 403

            # Check if user exists
            user_collection = get_user_collection()
            user = await user_collection.find_one({"username": username})

            if not user:
                return jsonify(USER_MESSAGES["USER_NOT_FOUND"]), 401
            
            if user['role'] != role:
                return jsonify(USER_MESSAGES["TOKEN_CREDENTIALS_MISMATCH"]), 403

            # Store user info in Flask's context
            g.user_id = user_id
            g.role = user["role"]
            g.username = username
            g.user = user
            g.token_payload = payload

        except jwt.ExpiredSignatureError:
            return jsonify(USER_MESSAGES["EXPIRED_TOKEN"]), 401
        except jwt.InvalidTokenError as e:
            return jsonify(USER_MESSAGES["INVALID_TOKEN"]), 401
        
        if inspect.iscoroutinefunction(f):
            return await f(*args, **kwargs)
        else:
            return f(*args, **kwargs)
    return decorated

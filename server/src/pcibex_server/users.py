from functools import wraps
from .auth import require_auth
from quart import Quart, Blueprint, request, jsonify, current_app, g
from .db import get_db_instance
from .utils import validate_password, hash_password, check_password, validate_email, validate_full_name # Assuming you have a utility function for hashing passwords
from .messages import USER_MESSAGES
from . import server_conf
import uuid
import jwt
from datetime import datetime, timedelta, timezone
import os
users_routes = Blueprint('users', __name__)

def get_user_collection_instance():
    """
        A simple helper function that returns the MongoDB instance 
        for user collection.
    """
    client = get_db_instance()
    mongo_db = client[os.getenv('MONGO_DB')]
    return mongo_db['users']

async def get_user_by_username(username):
    """
        Fetch a user by username from the database.
    """
    # Fetch user from the database
    users_collection = get_user_collection_instance() 
    user = await users_collection.find_one({"username": username})  # Exclude the MongoDB ObjectId field
    if user:
        user['_id'] = str(user['_id'])
    return user

async def get_user_by_id(user_id):
    """
        Fetch a user by user ID from the database.
    """
    # Fetch user from the database
    users_collection = get_user_collection_instance() 
    user = await users_collection.find_one({"_id": user_id}) 
    if user:
        user['_id'] = str(user['_id'])
        if 'password' in user:
            del user['password']
    return user

async def get_user_by_query_params(query):
    """ 
        Fetch users based on the requested query params. 
        The search is applied to the user full name and is case-insenstive
    """
    users_collection = get_user_collection_instance() 
    users = await users_collection.find({
            "full_name": {"$regex": query, "$options": "i"}
        }).to_list(None)
    
    for user in users:
        user['_id'] = str(user['_id'])
        if 'password' in user:
            del user['password']
    return users

async def update_user(username, user_data):
    """
        Update a user in the database.
    """
    # Access the MongoDB database from the Flask app context
    users_collection = get_user_collection_instance()
    result = await users_collection.update_one({"username": username}, {"$set": user_data})
    return result.modified_count > 0

async def get_all_users():
    """
        Fetch all users from the database.
    """
    # Access the MongoDB database from the Flask app context
    users_collection = get_user_collection_instance()
    users = await users_collection.find({}).to_list()  # Exclude the MongoDB ObjectId field
    # Remove password field from each user
    for user in users:
        user['_id'] = str(user['_id'])
        if 'password' in user:
            del user['password']
    
    return users

def generate_token(user): 
    """ 
        Helper function to generate a JWT token for the authenticated user. 
        The token includes user ID, username, role and token issue and expiration information. 
        The token duration is determined by the app config (see server_conf.py)
    """
    expiration = datetime.now(timezone.utc) + timedelta(hours=server_conf.JWT_EXPIRATION)
    issued_at = datetime.now(timezone.utc)
    token_payload = {
        'user_id': str(user.get('_id')),  # Convert to string to ensure serializable
        'username': user.get('username'),
        'exp': int(expiration.timestamp()),
        'iat': int(issued_at.timestamp()),
        'role': user.get('role')
    }
    
    try:
        # Create the token
        token = jwt.encode(
            token_payload,
            os.getenv('JWT_SECRET_KEY'),  # Secret key from environment variables
            algorithm=server_conf.JWT_ALGORITHM 
        )
        
        # Return user data with token
        return {
            'token': token,
            'user': user,
            'expires_at': expiration.isoformat()
        }
        
    except Exception as e:
        print(f"Error generating token: {e}")
        return USER_MESSAGES["AUTH_ERROR"]

@users_routes.route('/', methods=['GET'])
@require_auth
async def get_users():
    """
        Get a list of users from the database.
    """
    if g.role != server_conf.APP_ROLES[0]:
        return jsonify(USER_MESSAGES["AUTHORIZATION_ERROR"]), 403
    users = await get_all_users()
    if not users:
        return jsonify(USER_MESSAGES["NO_USERS_FOUND"]), 404

    return jsonify(users),200

@users_routes.route('/', methods=['POST'])
@require_auth
async def create_user():
    """ 
        Creates a new user in the database. Only ADMIN can create new users.
    """
    if g.role != server_conf.APP_ROLES[0]:
        return jsonify(USER_MESSAGES["AUTHORIZATION_ERROR"]), 403
    
    # Access the MongoDB database
    users_collection = get_user_collection_instance()
    
    # Get the user data from the request
    user_data = await request.get_json()

    if not user_data:
        return jsonify(USER_MESSAGES["NO_USER_DATA"]), 400
    if 'username' not in user_data:
        return jsonify(USER_MESSAGES["USERNAME_REQUIRED"]), 400
    if 'role' not in user_data:
        return jsonify(USER_MESSAGES["ROLE_REQUIRED"]), 400
    if 'full_name' not in user_data:    
        return jsonify(USER_MESSAGES["FULL_NAME_REQUIRED"]), 400
    
    valid, payload = validate_full_name(user_data['full_name'])
    if not valid:
        return jsonify(payload), 400
    
    if not validate_email(user_data['username']):
        return jsonify(USER_MESSAGES["INVALID_USERNAME"]), 400
    
    if user_data['role'] not in server_conf.APP_ROLES:
        return jsonify(USER_MESSAGES['INVALID_ROLE']), 400
    
    user_check = await get_user_by_username(user_data['username'])
    if user_check:
        return jsonify(USER_MESSAGES["USERNAME_TAKEN"]), 400
    
    # Create the password from the username as default
    now_utc = datetime.now(timezone.utc)
    user_data['createdOn'] = int(now_utc.timestamp() * 1000)   
    user_data['_id'] = str(uuid.uuid4())   
    user_data['password'] = hash_password(user_data['username'])
    
    created = await users_collection.insert_one(user_data)
    response = USER_MESSAGES["USER_CREATED"].copy()
    response["user_id"] = str(created.inserted_id)
    return jsonify(response), 201


@users_routes.route('/<username>', methods=['GET'])
def get_user(username): 
    """ 
        Fetch a user by username
    """
    user = get_user_by_username(username)
    if not user:
        return jsonify(USER_MESSAGES["USER_NOT_FOUND"]), 404
    del user['password']  # Remove password from the response
    return jsonify(user), 200

@users_routes.route('/password', methods=['PUT'])
async def update_password():
    """ 
        Update a user's password.
    """
    # Get the user data from the request
    data = await request.get_json()
    if not data:
        return jsonify(USER_MESSAGES["NO_DATA_PROVIDED"]), 400
    
    username = data.get('username')
    new_password = data.get('password')

    if not username or not new_password:
        return jsonify(USER_MESSAGES["USERNAME_PASSWORD_REQUIRED"]), 400
    
    # Valid the password
    user = await get_user_by_username(username)

    if not user:
        return jsonify(USER_MESSAGES["USER_NOT_FOUND"]), 404
    
    feedback = validate_password(new_password)
    if feedback != USER_MESSAGES["PASSWORD_VALID"]:
        return jsonify(feedback), 400
    
    # Update the user's password in the database
    # Ensure the password is hashed before storing it
    hashed_password = hash_password(new_password) 
    if hashed_password == user['password']:
        return jsonify(USER_MESSAGES["SAME_PASSWORD"]), 400
    
    result = await update_user(username, {"password": hashed_password})
    if not result:
        return jsonify(USER_MESSAGES["USER_NOT_FOUND_OR_PASSWORD_NOT_UPDATED"]), 404
    
    return jsonify(USER_MESSAGES["PASSWORD_UPDATED"]), 200

@users_routes.route('/login', methods=['POST'])
async def login(): 
    """ 
        Authenticate a user and return a JWT token if the authentication is successful. 
        JWT token validity depends on the app config
    """
    # Get the user data from the request
    data = await request.get_json()
    if not data:
        return jsonify(USER_MESSAGES["NO_DATA_PROVIDED"]), 400
    
    password = data.get('password')
    username = data.get('username') 
    
    if not username:
        return jsonify(USER_MESSAGES["USERNAME_REQUIRED"]), 400
    if not password:
        return jsonify(USER_MESSAGES["PASSWORD_REQUIRED"]), 400
    
    # Check if the password is correct
    user = await get_user_by_username(data['username'])
    if not user:
        return jsonify(USER_MESSAGES["USER_NOT_FOUND"]), 404
    if not check_password(user['password'], password):
        return jsonify(USER_MESSAGES["INVALID_PASSWORD"]), 401
    
    del user['password']
    
    token_data = generate_token(user)
    if "error" in token_data:
        response = {
            'data': None, 'error': token_data['error']
        }
        return jsonify(response), 500
    
    if password == username:
        return jsonify({"data": token_data, "message": USER_MESSAGES["UPDATE_PASSWORD"]}), 200
    return jsonify({"data": token_data, "message":""}), 200



def require_auth(f):
    """ 
        Decorator to validate the JWT token sent along with the API request. 
        The token contains user information as well as roles necessary to deduce if the 
        user is authenticated as well as authorized to perform the given action.
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithm=server_conf.JWT_ALGORITHM)
            # Validate presence of required claims
            if not payload.get("user_id") or not payload.get("username"):
                return jsonify({"error": "Invalid token claims"}), 403

            # Attach user info to request context (Flask's `g`)
            # Check if user exists first
            user = await get_user_by_username(payload["username"])
            if not user:
                return jsonify(USER_MESSAGES["USER_NOT_FOUND"]), 404
            g.user_id = user["_id"]
            g.username = payload["username"]
            g.role = user["role"]

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        return f(*args, **kwargs)

    return decorated
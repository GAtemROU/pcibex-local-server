from pymongo import AsyncMongoClient
from urllib.parse import quote_plus
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from utils import hash_password
import uuid
load_dotenv()
mongo_username = quote_plus(os.getenv('MONGO_USERNAME'))
mongo_password = quote_plus(os.getenv('MONGO_PASSWORD'))
mosaic_admin_username = os.getenv('MOSAIC_ADMIN')
mosaic_admin_password = os.getenv('MOSAIC_ADMIN_PASSWORD')
mongo_host = os.getenv('MONGO_HOST')
mongo_db = os.getenv('MONGO_DB')
mongo_port = os.getenv('MONGO_PORT')

def get_db_instance():
    MONGO_URI = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource={mongo_db}"
    client = AsyncMongoClient(MONGO_URI)
    return client
    
async def ping_db():
    try:
        client = get_db_instance()
        await client.admin.command('ping')
        await create_admin_if_not_exists(client)
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print("❌ Could not connect to MongoDB:", e)
        
def get_user_collection_instance(client):
    mongo_db = client[os.getenv('MONGO_DB')]
    return mongo_db['users']
        
async def create_admin_if_not_exists(client):
    users_collection = get_user_collection_instance(client)
    admin = await users_collection.find_one({"username": mosaic_admin_username})
    if admin:
        print("Admin exists")
    else:   
        now_utc = datetime.now(timezone.utc)
        admin_data = {
            "username": mosaic_admin_username,
            "role": 'ADMIN',
            "full_name": "Mosaic Admin",
            "createdOn": int(now_utc.timestamp() * 1000),
            "_id": str(uuid.uuid4()),
            'password': hash_password(mosaic_admin_password)   
        }
        created = await users_collection.insert_one(admin_data)
        if created:
            print("Admin Onboarded")
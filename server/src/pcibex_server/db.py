import os
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus

from pymongo import AsyncMongoClient

from .utils import hash_password

_mongo_client = None


def _required_setting(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required setting {name} is not configured")
    return value

def get_db_instance():
    global _mongo_client
    if _mongo_client is None:
        mongo_username = quote_plus(_required_setting("MONGO_USERNAME"))
        mongo_password = quote_plus(_required_setting("MONGO_PASSWORD"))
        mongo_host = _required_setting("MONGO_HOST")
        mongo_port = _required_setting("MONGO_PORT")
        mongo_db = _required_setting("MONGO_DB")
        mongo_uri = (
            f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:"
            f"{mongo_port}/{mongo_db}?authSource={mongo_db}"
        )
        _mongo_client = AsyncMongoClient(mongo_uri)
    return _mongo_client

async def ping_db():
    await get_db_instance().admin.command("ping")


async def close_db_instance():
    global _mongo_client
    if _mongo_client is not None:
        await _mongo_client.close()
        _mongo_client = None

def get_user_collection_instance(client):
    return client[_required_setting("MONGO_DB")]["users"]

async def create_admin_if_not_exists(client):
    mosaic_admin_username = _required_setting("MOSAIC_ADMIN")
    mosaic_admin_password = _required_setting("MOSAIC_ADMIN_PASSWORD")
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
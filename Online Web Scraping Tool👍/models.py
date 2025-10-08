"""
MongoDB models / helpers

We use pymongo directly for simplicity. Each function is small and focused.
"""
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import pymongo
import os

_db_client: Optional[MongoClient] = None
_db = None

def init_db(mongo_uri: str):
    global _db_client, _db
    _db_client = MongoClient(mongo_uri)

    # Explicitly check if a default database exists
    default_db = _db_client.get_default_database()
    dbname = default_db.name if default_db is not None else 'scraper_db'

    _db = _db_client[dbname]

    # Ensure indexes
    _db.users.create_index([('email', pymongo.ASCENDING)], unique=True)
    _db.users.create_index([('username', pymongo.ASCENDING)], unique=True)
    _db.scrapes.create_index([('user_id', pymongo.ASCENDING), ('created_at', pymongo.DESCENDING)])

    print(f"Connected to MongoDB database: {dbname}")

def create_user(username: str, email: str, password_hash: str) -> str:
    doc = {
        'username': username,
        'email': email,
        'password': password_hash,
        'created_at': datetime.utcnow()
    }
    res = _db.users.insert_one(doc)
    return str(res.inserted_id)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return _db.users.find_one({'email': email})

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None
    return _db.users.find_one({'_id': oid})

def save_scrape(job_doc: Dict[str, Any]) -> str:
    """
    job_doc expected keys: user_id (ObjectId), url, data (dict), summary (dict), created_at (datetime)
    """
    # ensure user_id is ObjectId
    if not isinstance(job_doc.get('user_id'), ObjectId):
        job_doc['user_id'] = ObjectId(job_doc['user_id'])
    res = _db.scrapes.insert_one(job_doc)
    return str(res.inserted_id)

def get_scrape_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(job_id)
    except Exception:
        return None
    doc = _db.scrapes.find_one({'_id': oid})
    if not doc:
        return None
    # convert ObjectId to str for templates
    doc['id'] = str(doc['_id'])
    doc['user_id'] = str(doc['user_id'])
    return doc

def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return []
    cursor = _db.scrapes.find({'user_id': oid}).sort('created_at', -1)
    history = []
    for doc in cursor:
        history.append({
            'id': str(doc['_id']),
            'url': doc.get('url'),
            'summary': doc.get('summary', {}),
            'created_at': doc.get('created_at')
        })
    return history

def delete_scrape(job_id):
    from pymongo import MongoClient
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['scraper_db']
    db.scrapes.delete_one({'_id': ObjectId(job_id)})

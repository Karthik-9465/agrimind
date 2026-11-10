import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("agrimind.mongodb")

_mongo_client = None
_mongo_db = None

def get_mongodb():
    """
    Returns MongoDB database instance if MONGODB_URI is configured.
    Returns None if MONGODB_URI is unconfigured or connection fails.
    """
    global _mongo_client, _mongo_db
    
    if _mongo_db is not None:
        return _mongo_db

    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    if not mongo_uri or mongo_uri.startswith("your_"):
        logger.info("MONGODB_URI not configured. Operating with primary SQLAlchemy relational database.")
        return None

    try:
        from pymongo import MongoClient
        db_name = os.getenv("MONGODB_DB_NAME", "agrimind")
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=4000)
        # Ping server
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client[db_name]
        logger.info(f"Connected successfully to MongoDB Atlas database: {db_name}")
        return _mongo_db
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB Atlas ({e}). Operating with local SQLAlchemy storage.")
        return None

def sync_report_to_mongodb(report_dict: Dict[str, Any]):
    """Optionally syncs disease diagnosis report into MongoDB collection."""
    db = get_mongodb()
    if db is not None:
        try:
            db["disease_reports"].insert_one(report_dict)
            logger.info(f"Report {report_dict.get('id')} synced to MongoDB Atlas.")
        except Exception as e:
            logger.error(f"Failed to sync report to MongoDB: {e}")


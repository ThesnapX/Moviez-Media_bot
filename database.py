import pymongo
from pymongo import MongoClient
from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME
import datetime

class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.collection = self.db[COLLECTION_NAME]
        
        # Create indexes
        self.collection.create_index("media_id", unique=True)
        self.collection.create_index("created_at")
    
    def save_files(self, media_id, files, user_id):
        """Save file metadata to MongoDB"""
        document = {
            "media_id": media_id,
            "files": files,
            "created_at": datetime.datetime.now(),
            "created_by": user_id,
            "total_files": len(files),
            "access_count": 0
        }
        
        self.collection.update_one(
            {"media_id": media_id},
            {"$set": document},
            upsert=True
        )
        return True
    
    def get_files(self, media_id):
        """Retrieve files by media_id"""
        result = self.collection.find_one({"media_id": media_id})
        return result.get("files") if result else None
    
    def increment_access(self, media_id):
        """Track how many times a link is accessed"""
        self.collection.update_one(
            {"media_id": media_id},
            {"$inc": {"access_count": 1}}
        )
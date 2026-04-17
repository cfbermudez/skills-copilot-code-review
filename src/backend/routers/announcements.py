"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import DESCENDING

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("")
def get_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements that haven't expired and have already started"""
    now = datetime.utcnow().isoformat()
    
    # Find active announcements where expiration_date is in the future
    # and start_date is not in the future (or is unset)
    announcements = list(announcements_collection.find(
        {
            "status": "active",
            "expiration_date": {"$gt": now},
            "$or": [
                {"start_date": {"$lte": now}},
                {"start_date": None},
                {"start_date": {"$exists": False}}
            ]
        },
        {"_id": 1, "title": 1, "message": 1, "start_date": 1, "expiration_date": 1, "created_at": 1}
    ).sort("created_at", DESCENDING))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    
    return announcements


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (including expired) - only for authenticated users"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    announcements = list(announcements_collection.find(
        {},
        {"_id": 1, "title": 1, "message": 1, "start_date": 1, "expiration_date": 1, "created_at": 1, "status": 1}
    ).sort("created_at", DESCENDING))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    
    return announcements


@router.post("")
def create_announcement(
    username: str,
    title: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement - only for authenticated users"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        exp_dt = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_dt >= exp_dt:
                raise ValueError("Start date must be before expiration date")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    
    announcement = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_at": datetime.utcnow().isoformat(),
        "status": "active"
    }
    
    result = announcements_collection.insert_one(announcement)
    
    return {
        "id": str(result.inserted_id),
        "title": announcement["title"],
        "message": announcement["message"],
        "start_date": announcement["start_date"],
        "expiration_date": announcement["expiration_date"],
        "created_at": announcement["created_at"],
        "status": announcement["status"]
    }


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    username: str,
    title: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an announcement - only for authenticated users"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate dates
    try:
        exp_dt = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_dt >= exp_dt:
                raise ValueError("Start date must be before expiration date")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    updated_announcement = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "status": announcement.get("status", "active")
    }
    
    announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": updated_announcement}
    )
    
    return {
        "id": str(obj_id),
        **updated_announcement,
        "created_at": announcement.get("created_at")
    }


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement - only for authenticated users"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}

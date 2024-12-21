from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyrebase
import os
from datetime import datetime, timezone
from typing import Optional
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load Firebase configuration from environment variable (or JSON file)
firebase_config = json.loads(os.getenv("FIREBASE_CONFIG"))

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Initialize FastAPI app
app = FastAPI()


# Pydantic models for Event with more detailed validation
class Event(BaseModel):
    user_id: str
    action: str
    timestamp: str
    client_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "Breinss",
                "action": "widget",
                "timestamp": "2024-12-21T07:09:13",
                "client_id": "example_client_id",
            }
        }


@app.post("/log-event")
async def log_event(event: Event):
    try:
        logger.info(f"Received event: {event.dict()}")

        # Check if the event already exists for the user and action combination
        existing_events = db.child("events").get()
        event_exists = False
        existing_key = None

        if existing_events.each():
            for e in existing_events.each():
                event_data = e.val()
                if (
                    event_data.get("user_id") == event.user_id
                    and event_data.get("action") == event.action
                ):
                    event_exists = True
                    existing_key = e.key()
                    logger.debug(f"Found existing event with key: {existing_key}")
                    break

        if event_exists and existing_key:
            # Update existing event
            event_data = {
                "user_id": event.user_id,
                "action": event.action,
                "timestamp": event.timestamp,
                "client_id": event.client_id,
                "usage_count": event_data.get("usage_count", 0) + 1,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"Updating existing event: {event_data}")
            db.child("events").child(existing_key).update(event_data)
        else:
            # Create new event
            event_data = {
                **event.dict(),
                "usage_count": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"Creating new event: {event_data}")
            db.child("events").push(event_data)

        return {
            "status": "success",
            "message": "Event logged successfully",
            "event": event_data,
        }

    except Exception as e:
        logger.error(f"Error logging event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error logging event: {str(e)}")


@app.get("/get_event_logs")
async def get_event_logs(event: Optional[str] = None):
    try:
        logger.info(f"Fetching logs for event: {event if event else 'all'}")

        if event:
            # Fetch specific event logs
            event_logs = (
                db.child("events").order_by_child("action").equal_to(event).get()
            )
        else:
            # Fetch all logs
            event_logs = db.child("events").get()

        if event_logs.each():
            logs = [log.val() for log in event_logs.each()]
            logger.debug(f"Found {len(logs)} logs")
            return {"logs": logs}
        else:
            logger.warning(f"No logs found for event: {event if event else 'any'}")
            return {"logs": []}

    except Exception as e:
        logger.error(f"Error fetching event logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

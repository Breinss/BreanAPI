from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyrebase
import os
from datetime import datetime
from typing import Optional

import json

# Load Firebase configuration from environment variable (or JSON file)
firebase_config = json.loads(os.getenv("FIREBASE_CONFIG"))

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Initialize FastAPI app
app = FastAPI()


# Pydantic models for User and Event
class Event(BaseModel):
    user_id: str
    action: str
    timestamp: str
    client_id: str


# Routes
@app.post("/log-event")
async def log_event(event: Event):
    try:
        # Check if the event already exists for the user and action
        existing_event = (
            db.child("events").order_by_child("user_id").equal_to(event.user_id).get()
        )

        event_exists = False
        if existing_event.each():
            for e in existing_event.each():
                event_data = e.val()
                # If the action matches, it's the same command for the same user
                if event_data["action"] == event.action:
                    # Update the existing event's usage count, timestamp, and client_id
                    event_data["usage_count"] = event_data.get("usage_count", 0) + 1
                    event_data["timestamp"] = (
                        datetime.now().isoformat()
                    )  # Update the timestamp to now
                    event_data["client_id"] = event.client_id  # Update client_id
                    db.child("events").child(e.key()).set(
                        event_data
                    )  # Update the existing event
                    event_exists = True
                    break

        if not event_exists:
            # If no existing event, create a new entry for the user and action
            event_data = event.dict()
            event_data["usage_count"] = 1
            event_data["timestamp"] = (
                datetime.now().isoformat()
            )  # Store timestamp for the first time
            db.child("events").push(event_data)  # Push new event

        return {"message": "Event logged successfully", "event": event}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging event: {str(e)}")


@app.get("/get_event_logs")
async def get_event_logs(event: Optional[str] = None):
    if not event:
        raise HTTPException(status_code=400, detail="Missing 'event' query parameter")

    try:
        # Query Firebase Realtime Database for events
        event_logs = db.child("events").order_by_child("action").equal_to(event).get()

        if event_logs.each():
            logs = [log.val() for log in event_logs.each()]
            return {"logs": logs}
        else:
            raise HTTPException(
                status_code=404, detail=f"No logs found for event: {event}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

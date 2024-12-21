from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyrebase
import os
from datetime import datetime
from typing import Optional

# Load Firebase configuration from environment variable (or JSON file)
import json

firebase_config = json.loads(os.getenv("FIREBASE_CONFIG"))

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Initialize FastAPI app
app = FastAPI()


# Pydantic models for User and Event
class User(BaseModel):
    id: str
    name: str
    email: str


class Event(BaseModel):
    user_id: str
    action: str
    timestamp: str
    client_id: str


# Route to log user information (for example, a new user)
@app.post("/log-user")
async def log_user(user: User):
    try:
        # Push user to Firebase Realtime Database
        db.child("users").child(user.id).set(user.dict())
        return {"message": "User logged successfully", "user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging user: {str(e)}")


# Route to log an event (and update usage if exists)
@app.post("/log-event")
async def log_event(event: Event):
    try:
        # Try to find existing event for the same action and user
        event_ref = db.child("events").child(event.user_id).child(event.action)

        existing_event = event_ref.get()

        if existing_event.val():
            # If the event already exists, update the timestamp and increment usage count
            existing_data = existing_event.val()
            existing_data["usage_count"] += 1
            existing_data["timestamp"] = (
                datetime.now().isoformat()
            )  # Update the timestamp to the current time
            event_ref.set(existing_data)  # Update the event data
        else:
            # If no event exists, create a new event with usage_count set to 1 and store timestamp
            event_data = event.dict()
            event_data["usage_count"] = 1
            event_data["timestamp"] = (
                datetime.now().isoformat()
            )  # Store timestamp for the first time
            event_ref.set(event_data)

        return {"message": "Event logged successfully", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging event: {str(e)}")


# Route to get event logs
@app.get("/get_event_logs")
async def get_event_logs(event: Optional[str] = None):
    if not event:
        raise HTTPException(status_code=400, detail="Missing 'event' query parameter")

    try:
        # Query Firebase Realtime Database for events matching the action
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

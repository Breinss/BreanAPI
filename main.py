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


# Routes
@app.post("/log-user")
async def log_user(user: User):
    try:
        # Push user to Firebase Realtime Database
        db.child("users").child(user.id).set(user.dict())
        return {"message": "User logged successfully", "user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging user: {str(e)}")


@app.post("/log-event")
async def log_event(event: Event):
    try:
        # Push event to Firebase Realtime Database
        db.child("events").push(event.dict())
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

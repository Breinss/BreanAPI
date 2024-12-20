from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyrebase
from datetime import datetime
import os

# Load Firebase configuration from a JSON file
import json

with open("/etc/secrets/firebase_config.json") as f:
    firebase_config = json.load(f)

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# Initialize FastAPI
app = FastAPI()


# Pydantic models
class User(BaseModel):
    id: str
    name: str
    email: str


class Event(BaseModel):
    user_id: str
    action: str
    timestamp: datetime = datetime.now()


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

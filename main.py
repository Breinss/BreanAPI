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


class CommandUsage(BaseModel):
    timestamp: str
    usage_count: int


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
    username = event.user_id
    command = event.action
    timestamp = datetime.now().isoformat()  # Get current timestamp

    # Define the unique key for this event
    command_key = f"{username}_{command}"

    # Reference to the command usage node in Firebase
    command_ref = db.child("command_usage").child(command_key)

    try:
        # Fetch existing command usage data
        existing_data = command_ref.get()

        if existing_data.val():
            # If the record exists, increment the usage count
            current_count = existing_data.val().get("usage_count", 0)
            new_data = CommandUsage(
                timestamp=timestamp,
                usage_count=current_count + 1,  # Increment the count
            )
            # Update the usage count in Firebase
            command_ref.update(new_data.dict())
            return {
                "message": f"Updated usage count for {username} using {command}. New count: {current_count + 1}"
            }
        else:
            # If no record exists, create a new one with usage count 1
            new_data = CommandUsage(timestamp=timestamp, usage_count=1)
            # Set the new record in Firebase
            command_ref.set(new_data.dict())
            return {"message": f"Created new record for {username} using {command}."}

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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyrebase
from datetime import datetime
import os

# Load Firebase configuration from a JSON file
import json

firebase_config = json.loads(os.getenv("FIREBASE_CONFIG"))

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
def get_event_logs():
    # Get 'event' parameter from query string
    event = request.args.get("event", None)
    if not event:
        return jsonify({"error": "Missing 'event' query parameter"}), 400

    try:
        # Query Firestore collection where events are stored
        logs_ref = db.collection("events").document(
            event
        )  # Replace 'events' with your Firestore collection name
        logs = logs_ref.get()

        # Check if the event exists
        if logs.exists:
            return jsonify(logs.to_dict()), 200
        else:
            return jsonify({"error": f"No logs found for event: {event}"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

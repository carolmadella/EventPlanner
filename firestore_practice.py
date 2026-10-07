"""
firestore_practice.py
Practice the four basic Firestore operations before building the real app:
insert, retrieve (query), modify, and delete.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Connect to Firestore using the service account key
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 1. INSERT - add() creates a new document with an automatic ID
_, event_ref = db.collection("events").add({
    "name": "Practice Party",
    "date": "2026-10-31",
    "location": "My house",
    "description": "Test event",
})
print("Created event with ID:", event_ref.id)

# Insert two guests that are linked to the event by its ID
for name, rsvp in [("Ana", "Yes"), ("Bruno", "Maybe")]:
    db.collection("guests").add({
        "event_id": event_ref.id,
        "name": name,
        "rsvp": rsvp,
    })
print("Added 2 guests.")

# 2. RETRIEVE - get one document by its ID
print("Event data:", event_ref.get().to_dict())

# QUERY - find only the guests whose event_id matches this event
guest_query = db.collection("guests").where(
    filter=FieldFilter("event_id", "==", event_ref.id))
for guest in guest_query.stream():
    print("  Guest:", guest.id, guest.to_dict())

input("\nOpen the Firebase console to see the data, then press Enter...")

# 3. MODIFY - update() changes only the fields you give it
event_ref.update({"location": "Community center"})
print("Updated location:", event_ref.get().to_dict()["location"])

# 4. DELETE - remove the guests first, then the event
for guest in guest_query.stream():
    guest.reference.delete()
event_ref.delete()
print("Deleted the practice event and its guests.")
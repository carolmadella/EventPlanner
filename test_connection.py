"""
test_connection.py
Quick check that Python can connect to the Firestore database.
It writes a test document, reads it back, then deletes it.
"""

import firebase_admin
from firebase_admin import credentials, firestore

# Service account key downloaded from the Firebase console.
# It is listed in .gitignore so it is never pushed to GitHub.
KEY_FILE = "serviceAccountKey.json"


def main():
    # Connect to Firebase using the service account key
    cred = credentials.Certificate(KEY_FILE)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # Insert a test document into a temporary collection
    test_ref = db.collection("connection_test").document("hello")
    test_ref.set({"message": "Hello, Firestore!"})
    print("Wrote test document.")

    # Read the document back
    doc = test_ref.get()
    print("Read back:", doc.to_dict())

    # Delete the test document so the database stays clean
    test_ref.delete()
    print("Deleted test document. Connection works!")


if __name__ == "__main__":
    main()
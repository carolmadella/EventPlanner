# Overview

As a software engineer, I wanted to learn how to build a program that stores its data in the cloud instead of on a local computer. Cloud databases remove the need to run and maintain your own database server, and they let the same data be reached from anywhere. To practice this, I built an Event Planner that keeps its events and their guest lists in Google Cloud Firestore.

The Event Planner is a Python command-line program. When it starts, it connects to a Firestore database using a Firebase service account and shows a menu. From the menu, the user can:

1. **Add an event** - enter a name, date, location, and optional description. The event is saved as a new document in the cloud.
2. **List all events** - retrieve every event from the database, sorted by date.
3. **List upcoming events** - run a filtered query that returns only events from today forward.
4. **View event details** - choose an event by number to see all of its information.
5. **Search events by name** - find events whose name contains a word (not case sensitive).
6. **Edit an event** - change any field of an event; pressing Enter keeps the current value.
7. **Delete an event** - remove an event after confirming. The event's guests are deleted too.
8. **Manage guests for an event** - choose an event, then:
   - view its guest list with a headcount by RSVP (Yes / Maybe / No)
   - add a guest with a name, optional email, and RSVP
   - update a guest's RSVP
   - remove a guest

To run the program:

1. Create a Firebase project with a Firestore database and download a service account key.
2. Save the key in the project folder as `serviceAccountKey.json` (this file is listed in `.gitignore` and is never uploaded).
3. Install the required library: `pip install -r requirements.txt`
4. Run the program: `python event_planner.py`

My purpose for writing this software was to learn how a NoSQL cloud database works and how to insert, retrieve, query, modify, and delete data in it from a program. I also wanted to learn how to relate two collections to each other in a NoSQL database and how to handle a secret credential safely.

[Software Demo Video](http://youtube.link.goes.here)

# Cloud Database

This program uses **Google Cloud Firestore**, a NoSQL document database that is part of Google Firebase. Instead of tables and rows, Firestore stores data as **documents** grouped into **collections**. Each document holds fields as key/value pairs and has a unique ID that Firestore generates automatically.

The database has two related collections:

**`events`** - one document per event

| Field | Type | Example |
|---|---|---|
| *(document ID)* | auto-generated | `dYCqP5bKJbLUTtVdMbhn` |
| `name` | string | "Birthday Party" |
| `date` | string (`YYYY-MM-DD`) | "2026-11-15" |
| `location` | string | "City Park" |
| `description` | string (optional) | "Bring snacks" |

**`guests`** - one document per guest

| Field | Type | Example |
|---|---|---|
| *(document ID)* | auto-generated | `Lm83qRt2Xa91PqZ0wKdc` |
| `event_id` | string (ID of the event) | `dYCqP5bKJbLUTtVdMbhn` |
| `name` | string | "Ana" |
| `email` | string (optional) | "ana@email.com" |
| `rsvp` | string: Yes, No, or Maybe | "Yes" |

**How the collections are related:** each guest stores the ID of its event in the `event_id` field. To show an event's guest list, the program queries the `guests` collection for documents where `event_id` equals that event's ID. Because Firestore does not delete related documents automatically, the program deletes an event's guests before deleting the event itself, so no guest is left pointing to an event that no longer exists.

Dates are stored as text in `YYYY-MM-DD` format so that alphabetical order matches date order. This lets Firestore sort events by date and filter them with a simple `>=` comparison.

# Development Environment

* **Visual Studio Code** - code editor
* **Firebase Console** - to create the project and the Firestore database, and to view the data
* **Git and GitHub** - version control
* **uv** - to create a Python virtual environment and install packages

The program is written in **Python 3.13** and uses these libraries:

* **firebase-admin** - the official Firebase Admin SDK, used to connect to Firestore
* **google-cloud-firestore** - provides `FieldFilter` for building filtered queries (installed with firebase-admin)
* **datetime** - from the Python standard library, used to check that dates are valid and to get today's date

# Useful Websites

- [Cloud Firestore Data Model](https://firebase.google.com/docs/firestore/data-model)
- [Add Data to Cloud Firestore](https://firebase.google.com/docs/firestore/manage-data/add-data)
- [Get Data with Cloud Firestore](https://firebase.google.com/docs/firestore/query-data/get-data)
- [Perform Simple and Compound Queries](https://firebase.google.com/docs/firestore/query-data/queries)
- [Delete Data from Cloud Firestore](https://firebase.google.com/docs/firestore/manage-data/delete-data)
- [Firebase Console](https://console.firebase.google.com/)

# Future Work

- Add user authentication so each person only sees their own events
- Receive live notifications when an event or guest list changes in the cloud
- Use a batched write so an event and its guests are deleted in a single operation
- Build a graphical or web interface instead of the command-line menu
- Support searching by location and filtering events by a date range
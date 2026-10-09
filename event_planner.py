"""
event_planner.py
Event Planner - a command-line program that stores events in a
Google Firestore cloud database.

CSE 310 - Cloud Databases module
Author: Carolina Madella
"""

from datetime import date, datetime

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Service account key (kept out of GitHub by .gitignore)
KEY_FILE = "serviceAccountKey.json"

# Dates are stored as text in this format so they sort correctly
DATE_FORMAT = "%Y-%m-%d"


# ---------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------

def connect_to_database():
    """Connect to Firestore with the service account key and return the client."""
    cred = credentials.Certificate(KEY_FILE)
    firebase_admin.initialize_app(cred)
    return firestore.client()


# ---------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------

def ask_text(prompt, required=True):
    """Ask for text. If the field is required, keep asking until it is not empty."""
    while True:
        answer = input(prompt).strip()
        if answer or not required:
            return answer
        print("  This field is required. Please try again.")


def ask_date(prompt, allow_blank=False):
    """Ask for a date in YYYY-MM-DD format and check that it is a real date.
    If allow_blank is True, pressing Enter returns an empty string."""
    while True:
        answer = input(prompt).strip()
        if answer == "" and allow_blank:
            return ""
        try:
            datetime.strptime(answer, DATE_FORMAT)
            return answer
        except ValueError:
            print("  Please use the format YYYY-MM-DD (example: 2026-11-15).")


# ---------------------------------------------------------------
# Event features
# ---------------------------------------------------------------

def add_event(db):
    """INSERT: ask for the event details and save a new document in 'events'."""
    print("\n--- Add a New Event ---")
    event = {
        "name": ask_text("Event name: "),
        "date": ask_date("Date (YYYY-MM-DD): "),
        "location": ask_text("Location: "),
        "description": ask_text("Description (optional): ", required=False),
    }
    # add() creates the document and Firestore generates its ID
    _, event_ref = db.collection("events").add(event)
    print(f"Event '{event['name']}' was saved (ID: {event_ref.id}).")


def get_all_events(db):
    """RETRIEVE: return every event document, sorted by date."""
    return list(db.collection("events").order_by("date").stream())


def get_upcoming_events(db):
    """QUERY: return only events from today forward, sorted by date."""
    today = date.today().strftime(DATE_FORMAT)
    query = (db.collection("events")
             .where(filter=FieldFilter("date", ">=", today))
             .order_by("date"))
    return list(query.stream())


def display_events(events):
    """Print a numbered table of events. The numbers let the user pick one."""
    if not events:
        print("No events found.")
        return
    print(f"\n{'#':<4}{'Date':<12}{'Name':<25}Location")
    print("-" * 60)
    for number, doc in enumerate(events, start=1):
        event = doc.to_dict()
        print(f"{number:<4}{event['date']:<12}{event['name']:<25}{event['location']}")


def choose_event(db):
    """Show all events and let the user pick one by number.
    Returns the chosen document, or None if there is nothing to choose."""
    events = get_all_events(db)
    display_events(events)
    if not events:
        return None
    while True:
        choice = input("\nEnter the event number (or press Enter to cancel): ").strip()
        if choice == "":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(events):
            return events[int(choice) - 1]
        print(f"  Please enter a number from 1 to {len(events)}.")


def view_event_details(db):
    """RETRIEVE ONE: show every field of a single event."""
    print("\n--- Event Details ---")
    doc = choose_event(db)
    if doc is None:
        return
    event = doc.to_dict()
    print(f"\nName:        {event['name']}")
    print(f"Date:        {event['date']}")
    print(f"Location:    {event['location']}")
    print(f"Description: {event.get('description') or '(none)'}")
    print(f"ID:          {doc.id}")


def search_events_by_name(db):
    """SEARCH: find events whose name contains the text the user types.
    Firestore cannot search for words inside text, so we retrieve the
    events and check each name in Python (ignoring upper/lower case)."""
    print("\n--- Search Events by Name ---")
    text = ask_text("Search for: ").lower()
    matches = [doc for doc in get_all_events(db)
               if text in doc.to_dict()["name"].lower()]
    display_events(matches)


def edit_event(db):
    """MODIFY: change the fields of an existing event.
    Pressing Enter keeps the current value."""
    print("\n--- Edit an Event ---")
    doc = choose_event(db)
    if doc is None:
        return
    event = doc.to_dict()
    print("\nPress Enter to keep the current value shown in [brackets].")

    changes = {}
    for field in ("name", "location", "description"):
        current = event.get(field, "")
        new_value = input(f"{field.capitalize()} [{current}]: ").strip()
        if new_value:
            changes[field] = new_value
    new_date = ask_date(f"Date [{event['date']}]: ", allow_blank=True)
    if new_date:
        changes["date"] = new_date

    if not changes:
        print("No changes made.")
        return
    # update() only changes the fields we send; the others stay the same
    doc.reference.update(changes)
    print(f"Event updated: {', '.join(changes)} changed.")


def delete_event(db):
    """DELETE: remove an event after the user confirms."""
    print("\n--- Delete an Event ---")
    doc = choose_event(db)
    if doc is None:
        return
    name = doc.to_dict()["name"]
    confirm = input(f"Are you sure you want to delete '{name}'? (y/n): ").strip().lower()
    if confirm != "y":
        print("Delete cancelled.")
        return
    # Week 2: the event's guests will also be deleted here
    doc.reference.delete()
    print(f"Event '{name}' was deleted.")


# ---------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------

def show_menu():
    """Print the main menu options."""
    print("\n===== EVENT PLANNER =====")
    print("1. Add an event")
    print("2. List all events")
    print("3. List upcoming events")
    print("4. View event details")
    print("5. Search events by name")
    print("6. Edit an event")
    print("7. Delete an event")
    print("0. Exit")


def main():
    """Connect to the database and run the menu until the user exits."""
    db = connect_to_database()
    print("Connected to Firestore.")

    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_event(db)
        elif choice == "2":
            print("\n--- All Events ---")
            display_events(get_all_events(db))
        elif choice == "3":
            print("\n--- Upcoming Events ---")
            display_events(get_upcoming_events(db))
        elif choice == "4":
            view_event_details(db)
        elif choice == "5":
            search_events_by_name(db)
        elif choice == "6":
            edit_event(db)
        elif choice == "7":
            delete_event(db)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose a number from the menu.")


if __name__ == "__main__":
    main()
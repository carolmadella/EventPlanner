"""
event_planner.py
Event Planner - a command-line program that stores events and their
guest lists in a Google Firestore cloud database.

The database has two related collections:
  events - one document per event
  guests - one document per guest, linked to an event by its event_id

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

# The only RSVP answers a guest can have
RSVP_OPTIONS = ("Yes", "No", "Maybe")


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


def ask_rsvp(prompt, allow_blank=False):
    """Ask for an RSVP answer (Yes, No or Maybe), in any upper/lower case.
    If allow_blank is True, pressing Enter returns an empty string."""
    while True:
        answer = input(prompt).strip().capitalize()
        if answer == "" and allow_blank:
            return ""
        if answer in RSVP_OPTIONS:
            return answer
        print("  Please type Yes, No or Maybe.")


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
    print(f"Guests:      {len(get_guests(db, doc.id))}")
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
    guests = get_guests(db, doc.id)
    confirm = input(f"Delete '{name}' and its {len(guests)} guest(s)? (y/n): ").strip().lower()
    if confirm != "y":
        print("Delete cancelled.")
        return
    # Firestore does not delete related documents automatically,
    # so we delete the event's guests first, then the event itself
    for guest in guests:
        guest.reference.delete()
    doc.reference.delete()
    print(f"Event '{name}' and {len(guests)} guest(s) were deleted.")


# ---------------------------------------------------------------
# Guest features (related collection)
# ---------------------------------------------------------------

def get_guests(db, event_id):
    """QUERY: return the guests that belong to one event, sorted by name.
    The event_id field is what links each guest to its event."""
    query = db.collection("guests").where(filter=FieldFilter("event_id", "==", event_id))
    return sorted(query.stream(), key=lambda doc: doc.to_dict()["name"].lower())


def display_guests(guests):
    """Print a numbered table of guests and a headcount by RSVP answer."""
    if not guests:
        print("No guests yet.")
        return
    print(f"\n{'#':<4}{'Name':<22}{'Email':<28}RSVP")
    print("-" * 60)
    for number, doc in enumerate(guests, start=1):
        guest = doc.to_dict()
        print(f"{number:<4}{guest['name']:<22}{guest.get('email') or '-':<28}{guest['rsvp']}")

    # Headcount: count how many guests gave each RSVP answer
    counts = {option: 0 for option in RSVP_OPTIONS}
    for doc in guests:
        counts[doc.to_dict()["rsvp"]] += 1
    print("-" * 60)
    print(f"Total: {len(guests)}   Yes: {counts['Yes']}   "
          f"Maybe: {counts['Maybe']}   No: {counts['No']}")


def choose_guest(db, event_id):
    """Show the event's guests and let the user pick one by number."""
    guests = get_guests(db, event_id)
    display_guests(guests)
    if not guests:
        return None
    while True:
        choice = input("\nEnter the guest number (or press Enter to cancel): ").strip()
        if choice == "":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(guests):
            return guests[int(choice) - 1]
        print(f"  Please enter a number from 1 to {len(guests)}.")


def add_guest(db, event_id):
    """INSERT: add a new guest document linked to the event."""
    print("\n--- Add a Guest ---")
    guest = {
        "event_id": event_id,
        "name": ask_text("Guest name: "),
        "email": ask_text("Email (optional): ", required=False),
        "rsvp": ask_rsvp("RSVP (Yes/No/Maybe): "),
    }
    db.collection("guests").add(guest)
    print(f"{guest['name']} was added to the guest list.")


def update_rsvp(db, event_id):
    """MODIFY: change a guest's RSVP answer."""
    print("\n--- Update an RSVP ---")
    doc = choose_guest(db, event_id)
    if doc is None:
        return
    guest = doc.to_dict()
    new_rsvp = ask_rsvp(f"New RSVP for {guest['name']} [{guest['rsvp']}]: ", allow_blank=True)
    if new_rsvp == "" or new_rsvp == guest["rsvp"]:
        print("No changes made.")
        return
    doc.reference.update({"rsvp": new_rsvp})
    print(f"{guest['name']}'s RSVP changed to {new_rsvp}.")


def remove_guest(db, event_id):
    """DELETE: remove a guest from the event's guest list."""
    print("\n--- Remove a Guest ---")
    doc = choose_guest(db, event_id)
    if doc is None:
        return
    name = doc.to_dict()["name"]
    confirm = input(f"Remove {name} from the guest list? (y/n): ").strip().lower()
    if confirm != "y":
        print("Remove cancelled.")
        return
    doc.reference.delete()
    print(f"{name} was removed from the guest list.")


def manage_guests(db):
    """Pick an event, then show a guest menu for that event until the user goes back."""
    print("\n--- Manage Guests ---")
    event_doc = choose_event(db)
    if event_doc is None:
        return
    event_name = event_doc.to_dict()["name"]

    while True:
        print(f"\n----- Guests for: {event_name} -----")
        print("1. View guest list")
        print("2. Add a guest")
        print("3. Update an RSVP")
        print("4. Remove a guest")
        print("0. Back to main menu")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            display_guests(get_guests(db, event_doc.id))
        elif choice == "2":
            add_guest(db, event_doc.id)
        elif choice == "3":
            update_rsvp(db, event_doc.id)
        elif choice == "4":
            remove_guest(db, event_doc.id)
        elif choice == "0":
            break
        else:
            print("Invalid option. Please choose a number from the menu.")


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
    print("8. Manage guests for an event")
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
        elif choice == "8":
            manage_guests(db)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please choose a number from the menu.")


if __name__ == "__main__":
    main()
    
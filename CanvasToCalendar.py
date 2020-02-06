# Author : Colby Hillman
# Last Edit : 9/15/19
# Title : Canvas to Google Calendar Importer
# Purpose : Pull assignments from Canvas and import them into Google Calendar
# Note : Requires Auth files from Canvas (txt) and Google (json). Canvas will allow you to generate the API Bearer Token
# and Google will require you to authenticate the use of their Calendar API

# Imports
import requests
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import time
from flask import Flask


app = Flask("Canvas To Calendar")

# Setup Connections to Google Calendar and Canvas
# Request JSON list of assignments from Canvas
def setup_connections(courses_URL, headers, params):
    # Set up connection to Google Calendar
    scopes = ['https://www.googleapis.com/auth/calendar']

    print()

    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', "rb") as token:
            print("Authenticating Google Calendar...\n")
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Redirecting to Google Calendar for Authentication...\n")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)


    # Make call to Canvas
    print("Starting Canvas Communication...\n")
    r = requests.get(url=courses_URL, headers=headers, params=params)

    # Encode response to JSON for parsing
    class_response = r.json()
    return class_response,service

# Pull all upcoming assignments from Canvas JSON Response
def pull_course_assignments(class_response, class_dict, class_ids, class_names, headers):

    assignments = []
    assignment = {}

    # Parse through Canvas Response for all active classes
    print("Parsing Canvas Data...\n")
    for item in class_response:
        # Print all courses - Test Code
        class_dict.update({item.get("id") : str(item.get("name"))})
        class_ids.append(item.get("id"))
        class_names.append(item.get("name"))

    for name in class_names:
        print(name)
    for id in class_ids:
        print(id)
    response = input("Enter the IDs of the courses you would like to track : ")
    response = response.strip("/n")
    tracked_ids = response.split(",")
    ids_to_keep = []
    for id in tracked_ids:
        class_id = int(id)
        ids_to_keep.append(class_id)

    for id in class_ids:
        if id not in ids_to_keep:
            class_dict.pop(id)

    # Parse through each class for assignments
    for course in class_dict:
        count = 0
        courses_URL = "https://moravian.instructure.com/api/v1/courses"
        course_URL_suffix = "/" + str(course) + "/assignments?per_page=100"
        r_classes = requests.get(url = str(courses_URL+course_URL_suffix), headers = headers)
        response = r_classes.json()
        for item in response:
            if(type(item) == dict):
                due_at = item['due_at']
                if str(due_at) != "None":
                    due_at_obj = datetime.datetime.strptime(due_at, "%Y-%m-%dT%H:%M:%SZ") - datetime.timedelta(hours=5)
                    if due_at_obj > datetime.datetime.utcnow():
                        assignment.update({"Class" : str(class_dict.get(course))})
                        assignment.update({ "Name" : str(item.get("name"))})
                        assignment.update({"Due": due_at_obj})
                        assignments.append(assignment)
                        assignment = {}
    return class_dict, assignments

# Check Google Calendar to add events
# Skips over this if there are no new updates or assignments in Canvas
# Cleans out the assignments if need be
def fetch_events(class_dict, assignments, events, service):

    deleted_assignments = []

    # Call Google Calendar for Events
    print("Starting Google Calendar Communication...\n")
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    for id in class_dict:
        currentClass = class_dict.get(id)
        scrap, currentClass = currentClass.split("       ")
        print('Fetching your upcoming assignments for', currentClass, "...","\n")
        events_result = service.events().list(calendarId="primary", timeMin=now, singleEvents=True,
                                              orderBy='startTime', q=currentClass).execute()
        events += events_result.get('items', [])
    if not events:
        print("\nNo upcoming assignments\n\n")

    # Filter out assignments
    for work in assignments:

        count = 0
        for assignmentEvent in events:
            if work.get("Name") in events[count]["summary"]:
                deleted_assignments.append(work.get("Name"))
            count += 1
    for item in deleted_assignments:
        for work in assignments:
            if work.get("Name") == item:
                assignments.remove(work)
                break
    return assignments,events

def create_events(assignments,events,service):
    # Create Events to put in Google Calendar
    if len(assignments) > 0:
        print("Adding assignments to calendar...\n")
        for work in assignments:
            newEvent = {}
            newEvent.update({"summary" : work.get("Name")})
            newEvent.update({"colorRgbFormat" : "true"})
            newEvent.update({"colorId" : "8"})
            newEvent.update({"description" : work.get("Class") + "\n\nDue at : " + str(work.get("Due").time())})
            newEvent.update({"start" : {"date" : str(work.get("Due").date()), "timeZone" : "America/New_York"}})
            newEvent.update({"end"   : {"date" : str(work.get("Due").date()), "timeZone" : "America/New_York"}})
            newEvent.update({"reminders" : {"useDefault" : False,
                                            "overrides" : [ {"method" : "popup", "minutes" : 24 * 60},
                                                                                  {"method" : "popup", "minutes" : 24 * 120}]}})
            if newEvent not in events:
                updateCalendar = service.events().insert(calendarId="primary", body=newEvent).execute()
                # Print Calendar Link - Test Code
                print("Assignment Added : %s" % (updateCalendar.get('htmlLink')))
    else:
        print("NOTICE : No Assignments to Add. Everything Up to Date")

    return 'Completed'

@app.route('/run_default')
def main():
    # Variables
    api_file = open("api.txt", "rt")
    apiKey = api_file.read()
    apiKey = apiKey.strip("\n")

    class_ids = []
    class_names = []
    class_dict = {}

    # Set URL data for GET call
    courses_URL = "https://moravian.instructure.com/api/v1/courses"

    # Set necessary information for GET call
    headers = {"Authorization": "Bearer " + str(apiKey)}
    params = {'enrollment_state': "active", "state[]": "active"}

    events = []
    class_response,service = setup_connections(courses_URL, headers, params)
    class_dict, assignments = pull_course_assignments(class_response, class_dict, class_ids, class_names,headers)
    assignments,events = fetch_events(class_dict, assignments, events, service)
    create_events(assignments,events,service)
    return "Calendar has been updated"

@app.route('/select_courses')
def select_classes():
    # Variables
    api_file = open("api.txt", "rt")
    apiKey = api_file.read()
    apiKey = apiKey.strip("\n")

    class_ids = []
    class_names = []
    class_dict = {}

    # Set URL data for GET call
    courses_URL = "https://moravian.instructure.com/api/v1/courses"

    # Set necessary information for GET call
    headers = {"Authorization": "Bearer " + str(apiKey)}
    params = {'enrollment_state': "active", "state[]": "active"}

    events = []
    class_response, service = setup_connections(courses_URL, headers, params)
    class_dict, assignments = pull_course_assignments(class_response, class_dict, class_ids, class_names, headers)
    assignments, events = fetch_events(class_dict, assignments, events, service)
    create_events(assignments, events, service)
    return "Calendar has been updated"

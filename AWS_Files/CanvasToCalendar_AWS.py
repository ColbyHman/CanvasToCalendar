# Author : Colby Hillman
# Last Edit : 9/15/19
# Title : Canvas to Google Calendar Importer
# Purpose : Pull assignments from Canvas and import them into Google Calendar
# Note : Requires Auth files from Canvas (txt) and Google (json). Canvas will allow you to generate the API Bearer Token
# and Google will require you to authenticate the use of their Calendar API
import sys
sys.path.insert(1, 'google-auth-httplib2/google/auth/')
sys.path.insert(1, 'google-api-python-client')
sys.path.insert(1, 'google-auth-oauthlib')
sys.path.insert(1, 'requests')

import datetime
import os.path
import pickle
import json
import requests
from transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from course_object import Course

# Variables
api_file = open("api.txt", "rt")
api_key = api_file.read()
api_key = api_key.strip("\n")
courses = []


# Setup Connections to Google Calendar and Canvas
# Request JSON list of assignments from Canvas
def setup_google_calendar():
    # Set up connection to Google Calendar
    scopes = ['https://www.googleapis.com/auth/calendar']
    creds = None

    with open('tmp/token.pickle', "rb") as token:
        creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Redirecting to Google Calendar for Authentication...\n")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
            creds = flow.run_local_server(port=8000)
        with open('tmp/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    return service


def setup_canvas():

    # Set URL data for GET call
    courses_url = "https://moravian.instructure.com/api/v1/courses"

    # Set necessary information for GET call
    headers = {"Authorization": "Bearer " + str(api_key)}
    params = {'enrollment_state': "active", "state[]": "active"}

    # Make call to Canvas
    r = requests.get(url=courses_url, headers=headers, params=params)

    # Encode response to JSON for parsing
    class_response = r.json()

    # Parse through Canvas Response for all active classes
    for item in class_response:
        new_course = Course(str(item.get("name")),item.get("id"))
        courses.append(new_course)

# Pull all upcoming assignments from Canvas JSON Response
def pull_course_assignments(classes):
    assignment = {}
    headers = {"Authorization": "Bearer " + str(api_key)}

    # Parse through each class for assignments
    for course in classes:
        assignments = course.get_assignments()
        courses_url = "https://moravian.instructure.com/api/v1/courses"
        course_url_suffix = "/" + str(course.get_id()) + "/assignments?per_page=100"
        r_classes = requests.get(url=str(courses_url + course_url_suffix), headers=headers)
        response = r_classes.json()
        for item in response:
            if type(item) == dict:
                due_at = item['due_at']
                if str(due_at) != "None":
                    due_at_obj = datetime.datetime.strptime(due_at, "%Y-%m-%dT%H:%M:%SZ") - datetime.timedelta(hours=4)
                    if due_at_obj > datetime.datetime.utcnow():
                        assignment.update({"Name": str(item.get("name"))})
                        assignment.update({"Due": due_at_obj})
                        if assignment not in assignments:
                            course.add_assignment(assignment)
                        assignment = {}


# Check Google Calendar to add events
# Skips over this if there are no new updates or assignments in Canvas
# Cleans out the assignments if need be
def fetch_events(classes, events, service):
    deleted_assignments = []

    # Call Google Calendar for Events
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    for course in classes:
        current_class = course.get_name()
        events_result = service.events().list(calendarId="primary", timeMin=now, singleEvents=True,
                                              orderBy='startTime', q=current_class).execute()
        events += events_result.get('items', [])

        # Filter out assignments
        for assignment in course.get_assignments():
            count = 0
            for _ in events:
                if assignment.get("Name") in events[count]["summary"]:
                    deleted_assignments.append(assignment.get("Name"))
                count += 1
        for item in deleted_assignments:
            for work in course.get_assignments():
                if work.get("Name") == item:
                    course.remove_assignment(work)
                    break
    return events


def create_events(courses, events, service):
    # Create Events to put in Google Calendar
    for course in courses:
        assignments = course.get_assignments()
        if len(assignments) > 0:
            for assignment in assignments:
                print("Adding assignments to calendar...\n")
                new_event = {}
                new_event.update({"summary": assignment.get("Name")})
                new_event.update({"colorRgbFormat": "true"})
                new_event.update({"colorId": "8"})
                new_event.update({"description": course.get_name() + "\n\nDue at : " + str(assignment.get("Due").time())})
                new_event.update({"start": {"date": str(assignment.get("Due").date()), "timeZone": "America/New_York"}})
                new_event.update({"end": {"date": str(assignment.get("Due").date()), "timeZone": "America/New_York"}})
                new_event.update({"reminders": {"useDefault": False,
                                                "overrides": [{"method": "popup", "minutes": 24 * 60},
                                                            {"method": "popup", "minutes": 24 * 120}]}})
                if new_event not in events:
                    update_calendar = service.events().insert(calendarId="primary", body=new_event).execute()
                    # Print Calendar Link - Test Code

def main():
    infile = open("selected_courses.txt", "rt")
    setup_canvas()
    filtered_course_ids = []
    
    for item in infile:
        item = item.strip('\n')
        try:
            filtered_course_ids.append(int(item))
        except:
            pass

    events = []
    service = setup_google_calendar()
    filtered_classes = []

    for course in courses:
        if course.get_id() in filtered_course_ids:
            filtered_classes.append(course)

    pull_course_assignments(filtered_classes)
    events = fetch_events(filtered_classes, events, service)
    create_events(filtered_classes, events, service)
    return "Classes Updated Successfully"

def lambda_handler(event,context):
    output = main()
    return {
        'statusCode' : 200,
        'body' : json.dumps(output)
    }

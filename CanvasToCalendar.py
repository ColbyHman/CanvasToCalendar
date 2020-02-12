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
from flask import Flask
from flask import render_template
from markupsafe import Markup
from flask import request

app = Flask("Canvas To Calendar")
# Variables
api_file = open("api.txt", "rt")
api_key = api_file.read()
api_key = api_key.strip("\n")


# Setup Connections to Google Calendar and Canvas
# Request JSON list of assignments from Canvas
def setup_google_calendar():
    # Set up connection to Google Calendar
    scopes = ['https://www.googleapis.com/auth/calendar']
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

    return service


def setup_canvas():
    class_ids = class_names = []
    class_dict = {}

    # Set URL data for GET call
    courses_url = "https://moravian.instructure.com/api/v1/courses"

    # Set necessary information for GET call
    headers = {"Authorization": "Bearer " + str(api_key)}
    params = {'enrollment_state': "active", "state[]": "active"}

    # Make call to Canvas
    print("Starting Canvas Communication...\n")
    r = requests.get(url=courses_url, headers=headers, params=params)

    # Encode response to JSON for parsing
    class_response = r.json()

    # Parse through Canvas Response for all active classes
    print("Parsing Canvas Data...\n")
    for item in class_response:
        # Print all courses - Test Code
        class_dict.update({item.get("id"): str(item.get("name"))})
        class_ids.append(item.get("id"))
        class_names.append(item.get("name"))

    return class_dict, class_ids, class_names


# Pull all upcoming assignments from Canvas JSON Response
def pull_course_assignments(class_dict, class_ids, class_names):
    assignments = []
    assignment = {}
    headers = {"Authorization": "Bearer " + str(api_key)}

    # Parse through each class for assignments
    for course in class_dict:
        courses_url = "https://moravian.instructure.com/api/v1/courses"
        course_url_suffix = "/" + str(course) + "/assignments?per_page=100"
        r_classes = requests.get(url=str(courses_url + course_url_suffix), headers=headers)
        response = r_classes.json()
        for item in response:
            if type(item) == dict:
                due_at = item['due_at']
                if str(due_at) != "None":
                    due_at_obj = datetime.datetime.strptime(due_at, "%Y-%m-%dT%H:%M:%SZ") - datetime.timedelta(hours=5)
                    if due_at_obj > datetime.datetime.utcnow():
                        assignment.update({"Class": str(class_dict.get(course))})
                        assignment.update({"Name": str(item.get("name"))})
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
        current_class = class_dict.get(id)
        scrap, current_class = current_class.split("       ")
        print('Fetching your upcoming assignments for', current_class, "...", "\n")
        events_result = service.events().list(calendarId="primary", timeMin=now, singleEvents=True,
                                              orderBy='startTime', q=current_class).execute()
        events += events_result.get('items', [])
    if not events:
        print("\nNo upcoming assignments\n\n")

    # Filter out assignments
    for work in assignments:

        count = 0
        for _ in events:
            if work.get("Name") in events[count]["summary"]:
                deleted_assignments.append(work.get("Name"))
            count += 1
    for item in deleted_assignments:
        for work in assignments:
            if work.get("Name") == item:
                assignments.remove(work)
                break
    return assignments, events


def create_events(assignments, events, service):
    # Create Events to put in Google Calendar
    if len(assignments) > 0:
        print("Adding assignments to calendar...\n")
        for work in assignments:
            new_event = {}
            new_event.update({"summary": work.get("Name")})
            new_event.update({"colorRgbFormat": "true"})
            new_event.update({"colorId": "8"})
            new_event.update({"description": work.get("Class") + "\n\nDue at : " + str(work.get("Due").time())})
            new_event.update({"start": {"date": str(work.get("Due").date()), "timeZone": "America/New_York"}})
            new_event.update({"end": {"date": str(work.get("Due").date()), "timeZone": "America/New_York"}})
            new_event.update({"reminders": {"useDefault": False,
                                            "overrides": [{"method": "popup", "minutes": 24 * 60},
                                                          {"method": "popup", "minutes": 24 * 120}]}})
            if new_event not in events:
                update_calendar = service.events().insert(calendarId="primary", body=new_event).execute()
                # Print Calendar Link - Test Code
                print("Assignment Added : %s" % (update_calendar.get('htmlLink')))
    else:
        print("NOTICE : No Assignments to Add. Everything Up to Date")

    return 'Completed'


@app.route('/select_courses', methods=['POST', 'GET'])
def filter_courses():
    class_dict, class_ids, class_names = setup_canvas()

    table_output = "<tr><th>Course Name</th><th>Course ID</th><th>Select Course</th></tr>"

    class_dict, assignments = pull_course_assignments(class_dict, class_ids, class_names)

    count = 0
    for id in class_dict:
        checkbox_name = "<input type=\"checkbox\" name=\"class{}\" value=\"{}\" />".format(count, id)
        table_output = table_output + "<tr>&nbsp;<td>{}</td>&nbsp;<td>{}</td>&nbsp;<td>{}</td>&nbsp;</tr>".format(
            class_dict[id], id, checkbox_name)
        count += 1

    table_output = Markup(table_output)

    return render_template('select_courses.html', course_list=table_output)


@app.route('/home')
def home():
    return render_template("home.html")


@app.route('/run_default')
def default():
    class_dict, class_ids, class_names = setup_canvas()

    class_dict, assignments = pull_course_assignments(class_dict, class_ids, class_names)

    return render_template('success.html')


# THIS WILL BE CHANGED TO INPUT FILTERED COURSES
@app.route('/filtered_courses', methods=['POST', 'GET'])
def filtered_classes():
    filtered_course_ids = []
    args = request.args.values()
    print(args)
    for item in args:
        print(item)
        try:
            filtered_course_ids.append(int(item))
        except:
            print('error')
            pass


    events = []
    class_dict, class_ids, class_names = setup_canvas()
    service = setup_google_calendar()
    filtered_class_dict = {}

    print(filtered_course_ids)

    for id in class_dict:
        print(id)
        if id in filtered_course_ids:
            print("GOT HERE")
            filtered_class_dict.update({id : class_dict.get(id)})

    print(class_dict.keys())
    print(filtered_class_dict)

    class_dict, assignments = pull_course_assignments(filtered_class_dict, filtered_course_ids, class_names)
    assignments, events = fetch_events(class_dict, assignments, events, service)
    create_events(assignments, events, service)
    return render_template('success.html')

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

#Variables
start = round(time.time())
api_file = open("api.txt", "rt")
apiKey = api_file.read()
apiKey = apiKey.strip("\n")

class_ids = []
class_names = []
class_id = 0
class_dict = {}

events = []

# Setup

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

# Set URL data for GET call
courses_URL = "https://moravian.instructure.com/api/v1/courses"
course_URL_suffix = "/" + str(class_id) + "/assignments"

# Set necessary information for GET call
headers = {"Authorization" : "Bearer " + str(apiKey)}
params = {'enrollment_state' : "active", "state[]" : "active"}

assignments = []
assignment = {}
deleted_assignments = []

# Make call to Canvas
print("Starting Canvas Communication...\n")
r = requests.get(url=courses_URL, headers=headers, params=params)

# Encode response to JSON for parsing
class_response = r.json()

# Test Code
# print(r.url)
# print(class_response)

# Backend Communication

# Parse through Canvas Response for all active classes
print("Parsing Canvas Data...\n")
for item in class_response:
    # Print all courses - Test Code
    # print("Course Name : " + str(item.get("name")) + "\nCourse ID : " + str(item.get("id")) + "\n")
    class_dict.update({item.get("id") : str(item.get("name"))})
    class_ids.append(item.get("id"))
    class_names.append(item.get("name"))

# Remove IT Class if included
if 5197 in class_ids:
    class_ids.remove(5197)
if "IT Work Study" in class_names:
    class_names.remove("IT Work Study")
if 5197 in class_dict:
    class_dict.pop(5197)

# Print all class IDs - Test Code
# print("Class IDs\n", class_ids, end="\n\n")

# Parse through each class for assignments
for classID in class_ids:

    count = 0
    course_URL_suffix = "/" + str(classID) + "/assignments"
    r_classes = requests.get(url = str(courses_URL+course_URL_suffix), headers = headers)
    response = r_classes.json()

    for item in response:
        due_at = item.get("due_at")
        if str(due_at) != "None":
            due_at_obj = datetime.datetime.strptime(due_at, "%Y-%m-%dT%H:%M:%SZ")
            if due_at_obj > datetime.datetime.utcnow():
                assignment.update({"Class" : str(class_dict.get(classID))})
                assignment.update({ "Name" : str(item.get("name"))})
                assignment.update({"Due": due_at_obj})
                assignments.append(assignment)
                assignment = {}

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
# Print out assignments found in Google Calendar - Test Code
#for event in events:
    # start = event['start'].get("dateTime", event['start'].get('date'))
    # print(event['description'], event['summary'])

# Filter out assignments
for work in assignments:
    count = 0
    for assignmentEvent in events:
        if work.get("Name") in events[count]["summary"]:
            deleted_assignments.append(work.get("Name"))
        # Print filtered classes - Test Code
        # elif not assignmentFound:
        #     print("Class : ", work.get("Class"))
        #     print("Name :" , work.get("Name"))
        #     print("Due By :", work.get("Due"))
        #     print()
        count += 1
for item in deleted_assignments:
    for work in assignments:
        if work.get("Name") == item:
            assignments.remove(work)
            break
# Create Events to put in Google Calendar
if len(assignments) > 0:
    print("Adding assignments to calendar...\n")
    for work in assignments:
        newEvent = {}
        newEvent.update({"summary" : work.get("Name")})
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

end = round(time.time())
totalRunTime = end - start
print("\nTime Taken :", totalRunTime, "seconds")
exit(0)

Canvas to Google Calendar

Requirements: Canvas API Key, Google Calendar OAuth

Optional: AWS Account

This program is intended to be used with Google Calendar and Canvas to pull assignment information and upload the information to Google Calendar.

The code can be modified to fit your needs, but this program is currently optimized for my personal use as I did not intend on creating a widely accessible application.

The use of Flask here allows for a usable GUI to manually sync over data between Canvas and GC, but we can bypass this step by placing the AWS script into a Lambda function and schedule it to run every day (or at any interval you wish). If you choose the AWS route, you can also enable SNS to email you with the results of the script's output.

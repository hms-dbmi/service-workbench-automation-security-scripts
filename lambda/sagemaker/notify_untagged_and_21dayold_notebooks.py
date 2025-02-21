import logging
import boto3
from datetime import timedelta, datetime as dt

# Configuration
Untagged_Notebooks_Email = "XXXXX"  # Email address to send notification of untagged SageMaker Notebooks.

# SES Configuration
SENDER = "sender@example.com"
SOURCEARN = "arn:aws:ses:us-west-2:123456789012:identity/example.com"
SUBJECT = "Service Workbench SageMaker workspace not logged in"
MISCONFIGURED_SUBJECT = "Untagged SageMaker Notebook instance"
CHARSET = "UTF-8"

def get_ses_message(notebook_instances):
    return "\n\n".join([
        "Thank you for using Service Workbench. The following instances have not been logged in for more than 21 days and are scheduled for termination in 7 days. Save your data in your user-specific folder to prevent loss. Log in within 7 days to avoid termination.",
        str(notebook_instances).replace("'", ""),
        "If you have any questions, please submit a helpdesk ticket."
    ])

def send_email(notebooks):
    ses = boto3.client("ses")
    for user, notebook_instances in notebooks.items():
        try:
            response = ses.send_email(
                Source=SENDER,
                SourceArn=SOURCEARN,
                Destination={"ToAddresses": [user]},
                Message={
                    "Subject": {"Charset": CHARSET, "Data": SUBJECT},
                    "Body": {"Text": {"Charset": CHARSET, "Data": get_ses_message(notebook_instances)}},
                },
            )
            print(f"Email sent to {user}. Message ID: {response.get('MessageId')}")
        except Exception as e:
            print(f"Error sending email to {user}: {e}")

def send_misconfigured_email(notebook_name):
    ses = boto3.client("ses")
    try:
        response = ses.send_email(
            Source=SENDER,
            SourceArn=SOURCEARN,
            Destination={"ToAddresses": [Untagged_Notebooks_Email]},
            Message={
                "Subject": {"Charset": CHARSET, "Data": MISCONFIGURED_SUBJECT},
                "Body": {"Text": {"Charset": CHARSET, "Data": f"Notebook {notebook_name} is missing a CreatedBy tag. Check logs for details."}},
            },
        )
        print(f"Misconfigured email sent. Message ID: {response.get('MessageId')}")
    except Exception as e:
        print(f"Error sending misconfigured email: {e}")

def fetch_old_notebooks(days):
    sm = boto3.client('sagemaker')
    old_notebooks_date = dt.utcnow() - timedelta(days=days)
    old_notebooks = {}

    notebooks = sm.list_notebook_instances(MaxResults=100)
    for notebook in notebooks.get("NotebookInstances", []):
        tags = sm.list_tags(ResourceArn=notebook['NotebookInstanceArn'])
        notebook_name = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'workspacename'), notebook['NotebookInstanceName'])
        created_by = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'createdby'), None)

        if not created_by:
            logging.error(f"Notebook {notebook_name} is missing CreatedBy tag")
            send_misconfigured_email(notebook_name)
            continue

        notebook['LastModifiedTime'] = notebook['LastModifiedTime'].replace(tzinfo=None)
        if notebook['LastModifiedTime'] < old_notebooks_date:
            old_notebooks[created_by] = old_notebooks.get(created_by, []) + [notebook_name]

    return old_notebooks

def lambda_handler(event, context):
    old_notebooks = fetch_old_notebooks(days=21)
    send_email(old_notebooks)

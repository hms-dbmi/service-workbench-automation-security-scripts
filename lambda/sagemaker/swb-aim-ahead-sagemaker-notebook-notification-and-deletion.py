import logging
import boto3
from datetime import timedelta, datetime as dt

Untagged_Notebooks_Email = "XXXXX"  # Email address to send notification of untagged SageMaker Notebooks.

# SES Options
SENDER = "sender@example.com"
SOURCEARN = "arn:aws:ses:us-west-2:123456789012:identity/example.com"
SUBJECT = "Service Workbench SageMaker workspace termination notice"
MISCONFIGURED_SUBJECT = "Untagged SageMaker notebook instance"
CHARSET = "UTF-8"

def get_ses_message(notebook_instances, is_expired=False):
    first_message_part = "Thank you for using Service Workbench. This is to notify you that the following instances have not been logged in for more than 21 days and are scheduled for termination in 7 days. All data not saved in your user-specific folder (based on your SWB log-in email) will be lost. To avoid this from happening, you will need to log into the instances within 7 days."

    if is_expired:
        first_message_part = "Thank you for using Service Workbench on AWS. This is to notify you that the following instances have not been logged in for more than 28 days and have been terminated."

    return "\n\n".join([
        first_message_part,
        str(notebook_instances).replace("'", ""),
        "If you have any questions, please submit a helpdesk ticket."
    ])

def send_email(notebooks, is_expired=False):
    ses = boto3.client("ses")

    for user, notebook_instances in notebooks.items():
        try:
            response = ses.send_email(
                Source=SENDER,
                SourceArn=SOURCEARN,
                Destination={
                    "ToAddresses": [
                        user,
                    ],
                },
                Message={
                    "Subject": {
                        "Charset": CHARSET,
                        "Data": SUBJECT,
                    },
                    "Body": {"Text": {"Charset": CHARSET, "Data": get_ses_message(notebook_instances, is_expired=is_expired)}},
                },
            )
            print(f"Email sent to {user}. Message ID: {response.get('MessageId')}")
        except Exception as e:
            print(f"An error occurred while sending the email to {user}: {e}")

def send_misconfigured_email(notebook_name):
    ses = boto3.client("ses")

    try:
        response = ses.send_email(
            Source=SENDER,
            SourceArn=SOURCEARN,
            Destination={
                "ToAddresses": [
                    Untagged_Notebooks_Email,
                ],
            },
            Message={
                "Subject": {
                    "Charset": CHARSET,
                    "Data": MISCONFIGURED_SUBJECT,
                },
                "Body": {
                    "Text": {"Charset": CHARSET, "Data": f"We found a notebook instance {notebook_name} that is not tagged with CreatedBy. Please check the logs for more details."}},
            },
        )
        print(f"Email sent to {Untagged_Notebooks_Email}. Message ID: {response.get('MessageId')}")
    except Exception as e:
        print(f"An error occurred while sending the email to {Untagged_Notebooks_Email}: {e}")

def fetch_old_notebooks(days, send_tag_notification=False):
    """
    Fetches all the old/expired notebooks
    :param send_tag_notification: Whether to send notification if a notebook is not tagged
    """

    old_notebooks = {}
    instance_names = {}

    sm = boto3.client('sagemaker')

    old_notebooks_date = dt.utcnow() - timedelta(days=days)

    notebooks = sm.list_notebook_instances(MaxResults=100)

    for notebook in notebooks.get("NotebookInstances", []):
        tags = sm.list_tags(ResourceArn=notebook['NotebookInstanceArn'])
        notebook_name = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'workspacename'), notebook['NotebookInstanceName'])
        notebook_instance_name = notebook['NotebookInstanceName']
        created_by = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'createdby'), None)

        if not created_by:
            if send_tag_notification:
                logging.error(f"Notebook {notebook_name} does not have a CreatedBy tag")
                send_misconfigured_email(notebook_name)
            continue

        notebook['LastModifiedTime'] = notebook['LastModifiedTime'].replace(tzinfo=None)

        if notebook['LastModifiedTime'] < old_notebooks_date:
            old_notebooks[created_by] = old_notebooks.get(created_by, []) + [notebook_name]
            instance_names[created_by] = instance_names.get(created_by, []) + [notebook_instance_name]

    return old_notebooks, instance_names

def delete_sagemaker_notebooks(notebooks):
    sm = boto3.client('sagemaker')

    for user, notebooks in notebooks.items():
        for notebook in notebooks:
            sm.delete_notebook_instance(NotebookInstanceName=notebook)

    return True

OLD_NOTEBOOKS_DAYS = 0
EXPIRED_NOTEBOOKS_DAYS = 0 + OLD_NOTEBOOKS_DAYS

def lambda_handler(event, context):
    old_notebooks, instance_names = fetch_old_notebooks(days=OLD_NOTEBOOKS_DAYS, send_tag_notification=True)
    send_email(old_notebooks)

    expired_notebooks, instance_names = fetch_old_notebooks(days=EXPIRED_NOTEBOOKS_DAYS)
    delete_sagemaker_notebooks(instance_names)
    send_email(expired_notebooks, is_expired=True)

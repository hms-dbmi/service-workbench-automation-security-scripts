import boto3
from datetime import timedelta, datetime as dt

# SES Configuration
SENDER = "sender@example.com"
SOURCEARN = "arn:aws:ses:us-west-2:123456789012:identity/example.com"
SUBJECT = "Service Workbench SageMaker workspace termination notice"
CHARSET = "UTF-8"

def get_ses_message(notebook_instances):
    return "\n\n".join([
        "Your SageMaker notebooks have been inactive for more than 28 days and have been terminated.",
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

def fetch_expired_notebooks(days):
    sm = boto3.client('sagemaker')
    expired_notebooks_date = dt.utcnow() - timedelta(days=days)
    expired_notebooks = {}
    instance_names = {}

    notebooks = sm.list_notebook_instances(MaxResults=100)
    for notebook in notebooks.get("NotebookInstances", []):
        tags = sm.list_tags(ResourceArn=notebook['NotebookInstanceArn'])
        notebook_name = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'workspacename'), notebook['NotebookInstanceName'])
        created_by = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'createdby'), None)

        if not created_by:
            continue

        notebook['LastModifiedTime'] = notebook['LastModifiedTime'].replace(tzinfo=None)
        if notebook['LastModifiedTime'] < expired_notebooks_date:
            expired_notebooks[created_by] = expired_notebooks.get(created_by, []) + [notebook_name]
            instance_names[created_by] = instance_names.get(created_by, []) + [notebook['NotebookInstanceName']]

    return expired_notebooks, instance_names

def delete_sagemaker_notebooks(notebooks):
    sm = boto3.client('sagemaker')
    for user, instances in notebooks.items():
        for instance in instances:
            sm.delete_notebook_instance(NotebookInstanceName=instance)
            print(f"Deleted notebook instance: {instance}")

def lambda_handler(event, context):
    expired_notebooks, instance_names = fetch_expired_notebooks(days=28)
    delete_sagemaker_notebooks(instance_names)
    send_email(expired_notebooks)

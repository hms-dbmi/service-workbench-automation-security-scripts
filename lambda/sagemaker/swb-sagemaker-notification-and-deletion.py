import logging

import boto3
from datetime import timedelta, datetime as dt

Untagged_Notebooks_Email="XXXXX" #Email address to send notification of untagged SageMaker Notebooks.

# SES Options
SENDER = "sender@example.com"
SOURCEARN = "arn:aws:ses:us-west-2:123456789012:identity/example.com"
SUBJECT = "Service Workbench SageMaker workspace termination notice"
MISCONFIGURED_SUBJECT = "Untagged SageMaker notebook instance"
CHARSET = "UTF-8"

# Assume role options
ASSUME_ROLE_ARN = "arn:aws:iam::123456789012:role/role-name"


def assume_role():
    sts = boto3.client("sts")
    assumed_role_object = sts.assume_role(
        RoleArn=ASSUME_ROLE_ARN, RoleSessionName="crossaccountaccess"
    )
    credentials = assumed_role_object["Credentials"]
    return credentials


def assumed_session():
    credentials = assume_role()
    session = boto3.Session(
        region_name='us-east-1',
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    return session


def get_ses_message(notebook_instances, is_expired=False):
    first_message_part = "Thank you for using Service Workbench. This is to notify you that the following instances have not been logged in for more than 21 days and are scheduled for termination in 7 days. All data not saved in your user-specific folder (based on your SWB log-in email) will be lost. To avoid this from happening, you will need to log into the instances within 7 days."

    if is_expired:
        first_message_part = "Thank you for using Service Workbench on AWS. This is to notify you that the following instances have not been logged in for more than 28 days and have been terminated."

    return "\n\n".join([
        first_message_part,
        str(notebook_instances).replace("'", ""),
        "If you have any questions, please submit a helpdesk ticket."
    ])


def send_email(session, notebooks, is_expired=False):
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


def send_misconfigured_email(session, notebook_name):
    # get ses client
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


def fetch_old_notebooks(session, days, send_tag_notification=False):
    """
    Fetches all the old/expired notebooks
    :param send_tag_notification: Whether to send notification if a notebook is not tagged
    """

    old_notebooks = {}
    instance_names = {}

    # get sagemaker client
    sm = session.client('sagemaker')

    # notebooks are old if they are prior to this date
    old_notebooks_date=dt.utcnow() - timedelta(days=days)

    notebooks = sm.list_notebook_instances(MaxResults=100)

    for notebook in notebooks.get("NotebookInstances", []):

        # Get notebook tags
        tags = sm.list_tags(ResourceArn=notebook['NotebookInstanceArn'])
        # get notebook name
        notebook_name = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'workspacename'), notebook['NotebookInstanceName'])
        notebook_instance_name = notebook['NotebookInstanceName']

        # Find out who created this notebook, as we need to notify them later
        created_by = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'createdby'), None)

        if not created_by:
            if send_tag_notification:
                logging.error(f"Notebook {notebook_name} does not have a CreatedBy tag")
                send_misconfigured_email(session, notebook_name)
            continue

        
        # convert notebook['LastModifiedTime'] to utc
        notebook['LastModifiedTime'] = notebook['LastModifiedTime'].replace(tzinfo=None)


        # one more additional check
        if notebook['LastModifiedTime'] < old_notebooks_date:
            old_notebooks[created_by] = old_notebooks.get(created_by, []) + [notebook_name]
            instance_names[created_by] = instance_names.get(created_by, []) + [notebook_instance_name]

    return old_notebooks, instance_names


def delete_sagemaker_notebooks(session, notebooks):
    # get sagemaker client
    sm = session.client('sagemaker')

    for user, notebooks in notebooks.items():
        for notebook in notebooks:
            sm.delete_notebook_instance(NotebookInstanceName=notebook)

    return True


OLD_NOTEBOOKS_DAYS = 0
EXPIRED_NOTEBOOKS_DAYS = 0 + OLD_NOTEBOOKS_DAYS


def lambda_handler(event, context):
    # get sagemaker client
    session = assumed_session()

    # Notify users about old notebooks
    old_notebooks, instance_names = fetch_old_notebooks(session, days=OLD_NOTEBOOKS_DAYS, send_tag_notification=True)
    send_email(session, old_notebooks)

    # Delete expired notebooks
    expired_notebooks, instance_names = fetch_old_notebooks(session, days=EXPIRED_NOTEBOOKS_DAYS)
    delete_sagemaker_notebooks(session, instance_names)
    send_email(session, expired_notebooks, is_expired=True)
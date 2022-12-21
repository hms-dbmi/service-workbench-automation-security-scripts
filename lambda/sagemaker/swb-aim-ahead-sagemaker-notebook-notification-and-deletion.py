import logging

import boto3
from datetime import timedelta, datetime as dt

Topic_Arn="XXXXX" #Topic Arn for the SNS topic that is used to send notifications to users.
Untagged_Notebooks_Email="XXXXX" #Email address to send notification of untagged SageMaker Notebooks.


def get_sns_message(notebook_instances, is_expired=False):
    first_message_part = "Thank you for using Service Workbench. This is to notify you that the following instances have not been logged in for more than 21 days and are scheduled for termination in 7 days. All data not saved in your user-specific folder (based on your SWB log-in email) will be lost. To avoid this from happening, you will need to log into the instances within 7 days."

    if is_expired:
        first_message_part = "Thank you for using Service Workbench on AWS. This is to notify you that the following instances have not been logged in for more than 28 days and have been terminated."

    return "\n\n".join([
        first_message_part,
        str(notebook_instances).replace("'", ""),
        "If you have any questions, please submit a helpdesk ticket."
    ])


def send_sns_notifications(session, notebooks, is_expired=False):
    # get sns client
    sns = session.client('sns')

    # get topic arn
    topic_arn = Topic_Arn

    # send notification to each user
    for user, notebook_instances in notebooks.items():
        sns.publish(
            TopicArn=topic_arn,
            Message=get_sns_message(notebook_instances, is_expired=is_expired),
            Subject="Service Workbench SageMaker workspace termination notice",
            MessageAttributes={
                'email': {
                    'DataType': 'String',
                    'StringValue': user,
                }
            }
        )


def send_notification(session, notebook_name):
    # get sns client
    sns = session.client('sns')

    # get topic arn
    topic_arn = Topic_Arn

    sns.publish(
        TopicArn=topic_arn,
        Message=f"We found a notebook instance {notebook_name} that is not tagged with CreatedBy. Please check the logs for more details.",
        Subject="Untagged SageMaker notebook instance",
        MessageAttributes={
            'email': {
                'DataType': 'String',
                'StringValue': Untagged_Notebooks_Email,
            }
        }
    )


def fetch_old_notebooks(session, days, send_tag_notification=False):
    """
    Fetches all the old/expired notebooks
    :param send_tag_notification: Whether to send notification if a notebook is not tagged
    """

    old_notebooks = {}

    # get sagemaker client
    sm = session.client('sagemaker')
    notebooks = sm.list_notebook_instances()

    for notebook in notebooks.get("NotebookInstances", []):
        # get notebook name
        notebook_name = notebook['NotebookInstanceName']

        # Get notebook tags
        tags = sm.list_tags(ResourceArn=notebook['NotebookInstanceArn'])

        # Find out who created this notebook, as we need to notify them later
        created_by = next((tag['Value'] for tag in tags['Tags'] if tag['Key'].lower() == 'createdby'), None)

        if not created_by:
            if send_tag_notification:
                logging.error(f"Notebook {notebook_name} does not have a CreatedBy tag")
                send_notification(session, notebook_name)
            continue

        # convert notebook['LastModifiedTime'] to utc
        notebook['LastModifiedTime'] = notebook['LastModifiedTime'].replace(tzinfo=None)

        # check if notebook is older than 21 days
        if notebook['LastModifiedTime'] < dt.utcnow() - timedelta(days=days):
            old_notebooks[created_by] = old_notebooks.get(created_by, []) + [notebook_name]

    return old_notebooks


def delete_sagemaker_notebooks(session, notebooks):
    # get sagemaker client
    sm = session.client('sagemaker')

    for user, notebooks in notebooks.items():
        for notebook in notebooks:
            sm.delete_notebook_instance(NotebookInstanceName=notebook)

    return True


OLD_NOTEBOOKS_DAYS = 21
EXPIRED_NOTEBOOKS_DAYS = 7 + OLD_NOTEBOOKS_DAYS


def lambda_handler(event, context):
    # get sagemaker client
    session = boto3.Session(region_name='us-east-1')

    # Notify users about old notebooks
    old_notebooks = fetch_old_notebooks(session, days=OLD_NOTEBOOKS_DAYS, send_tag_notification=True)
    send_sns_notifications(session, old_notebooks)

    # Delete expired notebooks
    expired_notebooks = fetch_old_notebooks(session, days=EXPIRED_NOTEBOOKS_DAYS)
    delete_sagemaker_notebooks(session, expired_notebooks)
    send_sns_notifications(session, expired_notebooks, is_expired=True)

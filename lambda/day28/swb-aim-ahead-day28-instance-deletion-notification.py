import boto3
import csv
import json
from io import StringIO, BytesIO
from boto3.dynamodb.conditions import Key, Attr

Topic_Arn="XXXXX" #Topic Arn for the SNS topic that is used to send notifications to users.
S3_Bucket_Name="XXXXX"
S3_File_Name="XXXXX"
DynamoDB_Table="XXXXX" #DynamoDB table used to track teh status of the swb instance.

client = boto3.client('ec2')

def update_DynamoDB(ec2_name):
    dynamodb=boto3.resource("dynamodb")
    table=dynamodb.Table(DynamoDB_Table)
    items = []
    response = table.scan(
        FilterExpression=Attr('ec2name').eq(ec2_name)
    )
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Attr('ec2name').eq(ec2_name),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])

    if response['Count'] == 0:
        return

    # update the item
    response['Items'][0]['swbstatus'] = 'TERMINATED'
    table.put_item(Item=response['Items'][0])


def get_s3_instances(csv_file):
    bucket_name = S3_Bucket_Name
    object_key = S3_File_Name

    s3 = boto3.client('s3')
    csvfile = BytesIO()
    s3.download_fileobj(bucket_name, object_key, csvfile)

    # Start at the first bytes
    csvfile.seek(0)

    instance_ids = csvfile.read().decode("UTF8").splitlines()

    return instance_ids
    

def is_email_subscribed(email_address: str):
    sns = boto3.client('sns')
    response = sns.list_subscriptions_by_topic(TopicArn=Topic_Arn)

    for subscription in response['Subscriptions']:
        if subscription['Protocol'] == "email" and subscription['Endpoint'] == email_address:
            return True

    # We couldn't find a subscription for the email
    return False


def subscribe_email(email_address: str):
    sns = boto3.client('sns')
    sns.subscribe(
        TopicArn=Topic_Arn,
        Protocol='email',
        Endpoint=email_address,
        Attributes={
            'FilterPolicy': json.dumps({"email": [email_address]})
        },
        ReturnSubscriptionArn=True
    )


def send_email(email_address: str, instances):
    subject = "Service Workbench workspace termination"

    message = "\n\n".join([
        "This is to notify that the following instances have not been logged in and are scheduled for termination.",
        str(instances).replace("'", ""),
        "If you have any questions, please submit a helpdesk ticket."
    ])

    if not is_email_subscribed(email_address):
        subscribe_email(email_address)
    sns = boto3.client('sns')
    sns.publish(
        TopicArn=Topic_Arn,
        Message=message,
        Subject=subject,
        MessageAttributes={
            'email': {
                'DataType': 'String',
                'StringValue': email_address,
            }
        }
    )


def delete_instances(instance_ids):
    if instance_ids:
        client.terminate_instances(InstanceIds=instance_ids)
    else:
        print("No instances to delete")

    
def send_final_notifications():
    instance_ids = get_s3_instances(S3_File_Name)
    count = 0

    if instance_ids:
        response = client.describe_instances(InstanceIds=instance_ids)
        email_instance_hash = {}

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                for tag in instance["Tags"]:
                    if tag["Key"] == "CreatedBy":
                        name = next((t["Value"] for t in instance["Tags"] if t["Key"] == "Name"),
                                    instance['InstanceId'])
                        email = tag["Value"]
                        if email in email_instance_hash:
                            email_instance_hash[email].append(name)
                        else:
                            email_instance_hash[email] = [name]

        for email in email_instance_hash:
            count += 1
            instances = email_instance_hash[email]
            send_email(email, instances)

            for instance in instances:
                update_DynamoDB(instance)

        delete_instances(instance_ids)
    else:
        print("No instances to delete...")

    return count
    
    
def lambda_handler(event, context):
    status_code = 200
    try:
        count = send_final_notifications()
        if count > 0:
            message = f"Sent {count} notification(s) successfully"
        else:
            message = "No notifications required to send."
    except Exception as e:
        status_code = 500
        message = f"An error has occurred: [{str(e)}]"

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": message
        })
    }
    
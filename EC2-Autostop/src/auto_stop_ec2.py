import logging
import os
import re
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info('event received: {}'.format(event))

    alarm_arn = event.get("alarmArn")

    if not alarm_arn:
        logger.error("No alarmArn in event")
        return {
            'statusCode': 400,
            'body': 'No alarmArn in event'
        }

    match = re.search(r'i-[0-9a-f]+', alarm_arn)
    instance_id = match.group()

    if not instance_id:
        logger.error(f"Could not find instance id in alarmArn {alarm_arn}")
        return {
            'statusCode': 400,
            'body': 'Could not find instance id in alarmArn'
        }

    logger.info(f"The following instance is in alarm & needs to be shut down: {instance_id}")

    # Searches through the Dynamodb table for the instance id and updates the status to STOPPED if found
    role_arn = os.environ['DYNAMODB_ROLE_ARN']
    table_name = os.environ['DYNAMODB_TABLE']
    try:
        dynamodb = assume_role_dynamodb(role_arn, 'auto_stop_ec2_dev')
        logger.info(f"Searching for instance {instance_id} in DynamoDB table: {table_name}")
        response = dynamodb.get_item(TableName=table_name, Key={'id': {'S': instance_id}})

        if 'Item' not in response:
            logger.info(f"Instance {instance_id} not found in dynamodb table: {table_name}")
        else:
            logger.info(f"Found instance {instance_id} in dynamodb table: {table_name}")
            logger.info(f"Setting status to STOPPED")
            dynamodb.update_item(
                TableName=table_name,
                Key={'id': {'S': instance_id}},
                UpdateExpression='SET #status = :val1',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':val1': {'S': 'STOPPED'}
                }
            )
            logger.info(f"Set status to STOPPED in dynamodb table: {table_name}")
    except Exception as e:
        logger.error(f"Error updating status in dynamodb table: {table_name}")
        logger.error(e)

    # stop the instance itself
    try:
        ec2 = boto3.client('ec2')
        logger.info(f"Stopping instance {instance_id}")
        ec2.stop_instances(InstanceIds=[instance_id])
        logger.info(f"Stopped instance {instance_id}")
    except Exception as e:
        logger.error(f"Error stopping instance {instance_id}")
        logger.error(e)
        return {
            'statusCode': 400,
            'body': f'Error stopping instance {instance_id} - {e}'
        }

    return {
        'statusCode': 200,
        'body': f'Stopped instance {instance_id}'
    }


def assume_role_dynamodb(role_arn, session_name):
    sts_client = boto3.client('sts')
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )

    credentials = response['Credentials']

    dynamodb_client = boto3.client(
        'dynamodb',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

    return dynamodb_client

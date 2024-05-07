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

    # find the dynamodb record
    dynamodb_table_name = os.environ['DYNAMODB_TABLE_NAME']
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(dynamodb_table_name)

    logger.info(f"Searching for instance {instance_id} in dynamoddb table {dynamodb_table_name}")
    response = table.get_item(Key={'id': instance_id})

    if 'Item' not in response:
        logger.error(f"Instance {instance_id} not found in dynamodb table")
    else:
        logger.info(f"Found instance {instance_id} in dynamodb table")
        logger.info(f"Setting status to STOPPED")
        table.update_item(
            Key={'id': instance_id},
            UpdateExpression='SET #status = :val1',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':val1': 'STOPPED'
            }
        )
        logger.info(f"Set status to STOPPED in dynamodb table")

    # stop the instance itself
    ec2 = boto3.client('ec2')
    logger.info(f"Stopping instance {instance_id}")
    ec2.stop_instances(InstanceIds=[instance_id])
    logger.info(f"Stopped instance {instance_id}")

    return {
        'statusCode': 200,
        'body': f'Stopped instance {instance_id}'
    }

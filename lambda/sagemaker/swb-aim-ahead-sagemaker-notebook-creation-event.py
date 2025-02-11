import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = boto3.client("dynamodb")
sagemaker_client = boto3.client("sagemaker")

TABLE_NAME = "SageMakerNotebookStacks"

def get_stack_name(notebook_arn):
    """Retrieve the CloudFormation stack name from notebook tags."""
    response = sagemaker_client.list_tags(ResourceArn=notebook_arn)
    for tag in response.get("Tags", []):
        if tag["Key"] == "aws:cloudformation:stack-name":
            return tag["Value"]
    return None

def store_in_dynamodb(notebook_arn, stack_name):
    """Store notebook ARN and CloudFormation stack name in DynamoDB."""
    if not stack_name:
        logger.warning(f"Stack name not found for {notebook_arn}")
        return
    
    dynamodb_client.put_item(
        TableName=TABLE_NAME,
        Item={
            "NotebookInstanceArn": {"S": notebook_arn},
            "StackName": {"S": stack_name}
        }
    )
    logger.info(f"Stored notebook ARN and stack name in DynamoDB: {notebook_arn} -> {stack_name}")

def lambda_handler(event, context):
    """Triggered when a SageMaker notebook is created."""
    logger.info(f"Received event: {event}")

    notebook_arn = event.get("detail", {}).get("NotebookInstanceArn")
    if not notebook_arn:
        logger.error("Notebook ARN not found in event.")
        return

    stack_name = get_stack_name(notebook_arn)
    store_in_dynamodb(notebook_arn, stack_name)

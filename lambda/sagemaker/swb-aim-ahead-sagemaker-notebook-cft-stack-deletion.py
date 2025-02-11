import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = boto3.client("dynamodb")
cloudformation_client = boto3.client("cloudformation")

TABLE_NAME = "SageMakerNotebookStacks"

def get_stack_name(notebook_arn):
    """Retrieve CloudFormation stack name from DynamoDB."""
    response = dynamodb_client.get_item(
        TableName=TABLE_NAME,
        Key={"NotebookInstanceArn": {"S": notebook_arn}}
    )
    return response.get("Item", {}).get("StackName", {}).get("S")

def delete_stack(stack_name):
    """Delete the CloudFormation stack."""
    try:
        cloudformation_client.delete_stack(StackName=stack_name)
        logger.info(f"Successfully triggered deletion for stack: {stack_name}")
    except Exception as e:
        logger.error(f"Failed to delete stack {stack_name}: {str(e)}")

def delete_dynamodb_entry(notebook_arn):
    """Delete the entry from DynamoDB after stack deletion."""
    try:
        dynamodb_client.delete_item(
            TableName=TABLE_NAME,
            Key={"NotebookInstanceArn": {"S": notebook_arn}}
        )
        logger.info(f"Deleted DynamoDB entry for {notebook_arn}")
    except Exception as e:
        logger.error(f"Failed to delete DynamoDB entry for {notebook_arn}: {str(e)}")

def lambda_handler(event, context):
    """Triggered by SageMaker notebook deletion."""
    logger.info(f"Received event: {event}")

    notebook_arn = event.get("detail", {}).get("NotebookInstanceArn")
    if not notebook_arn:
        logger.error("Notebook ARN not found in event.")
        return

    stack_name = get_stack_name(notebook_arn)
    if not stack_name:
        logger.warning(f"No CloudFormation stack found for {notebook_arn}")
        return

    logger.info(f"Deleting CloudFormation stack: {stack_name}")
    delete_stack(stack_name)
    delete_dynamodb_entry(notebook_arn)

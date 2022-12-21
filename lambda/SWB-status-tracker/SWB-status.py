import json
import boto3
import time
from datetime import datetime
from datetime import timedelta
from boto3.dynamodb.conditions import Key, Attr
tablename1="XXXXXX" #The name of the EnvironmentSC table that SWB creates
tablename2="XXXXXX"
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
   table = dynamodb.Table(tablename1)
   table2 = dynamodb.Table(tablename2)
   
   response = table.scan(AttributesToGet=['id','cidr','createdAt','status','updatedAt','name'])
   items = response['Items']
   for item in items:
    #print(then)
    print (item)
    id=item["id"]
    cidr=item["cidr"]
    createdAt=item["createdAt"]
    status=item["status"]
    updatedAt=item["updatedAt"]
    name=item["name"]

    table2.update_item(
                    Key={
                        'id': item['id']
                    },
                    UpdateExpression='SET cidr = :cidr, createdAt = :createdAt,swbstatus = :status,updatedAt = :updatedAt,ec2name = :name ',
                    ExpressionAttributeValues={
                        ':cidr': cidr,
                        ':createdAt': createdAt,
                        ':status': status,
                        ':updatedAt': updatedAt,
                        ':name': name,
                    }
                )
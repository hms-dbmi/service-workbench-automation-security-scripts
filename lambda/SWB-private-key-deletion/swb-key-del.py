import json
import boto3
import time
from datetime import datetime
from datetime import timedelta
from boto3.dynamodb.conditions import Key, Attr
tablename="XXXXXX" #The name of the KeyPairs table that SWB creates 


def lambda_handler(event, context):
   dynamodb = boto3.resource('dynamodb')
   now = datetime.utcnow() 
   then = now-timedelta(days=90)
   then=then.isoformat()[:-3]+'Z'
   table = dynamodb.Table(tablename)

   response = table.scan(ProjectionExpression="id,createdAt",FilterExpression = Attr('createdAt').lt(then))
   items = response['Items']
   for item in items:
    #print(then)
    print (item)
    print (item["id"])
    id=item["id"]
    table.delete_item(
    Key={
        'id': id
    })
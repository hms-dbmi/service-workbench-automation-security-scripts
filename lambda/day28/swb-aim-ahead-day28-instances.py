from datetime import datetime, timedelta
    
import boto3

s3 = boto3.client('s3')

def get_instances(client, days_before=28):
    try:
        launch_date = datetime.today() - timedelta(days=days_before)
        response = client.describe_instances()
    
        instances = response['Reservations'][0]['Instances']
        
        instances_map = {}
        for instance in instances:
            instance_id = instance["InstanceId"]
            status = instance["State"]["Name"]
            name = instance["Tags"][0]["Value"]
            
            if instance_id not in instances_map:
                instances_map[instance_id] = {}

            instances_map[instance_id]["launched_after"] = True
            instances_map[instance_id]["status"] = status
            instances_map[instance_id]["name"] = name

            # Get instances launched before launch date
            if instance["LaunchTime"].timestamp() < launch_date.timestamp():
                instances_map[instance_id]["launched_after"] = False

        # Returns all instances' name, status, if launched X days before
        return instances_map

    except:
        print("Could not get instances")
        raise


def write_to_bucket(bucket, key, instance_ids):
    data = "\n".join([str(id) for id in instance_ids])
    s3.put_object(Bucket=bucket, Key=key, Body=data.encode('utf8'))


def lambda_handler(event, context):
    client = boto3.client('ec2')
    launched_days_before = 28 # X days before
    instances = get_instances(client, launched_days_before)

    old_instances = []
    for instance_id, instance in instances.items():
        if not instance["launched_after"]:
            old_instances.append(instance_id)
            
    # Save all "old" instance ids in S3
    filename = f"instances-launched-{launched_days_before}daysago.csv"
    write_to_bucket("swb-aim-ahead-unused-instances-artifacts", filename, old_instances)
    

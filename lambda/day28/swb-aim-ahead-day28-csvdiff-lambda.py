import boto3

import pandas as pd

print('Loading function')

s3 = boto3.client('s3')

def set_difference(master_list, other_file):
    master_unique_ids = set(master_list)
    other_unique_ids = set(other_file)
    diff = master_unique_ids.difference(other_unique_ids)

    return "\n".join([str(id) for id in list(diff)])


def extract_data(data):
    return data.decode('utf8').splitlines() # Ascii text

    """
    df = pd.read_excel(data, header=None) # Read Excel file
    keys = list(df.keys())
    ids = df[keys[0]].iloc[:]

    return list(ids)
    """


    
def get_instance_ids(bucket, key, encoding='utf-8'):
    response = s3.get_object(Bucket=bucket, Key=key)
    instance_ids = extract_data(response['Body'].read())

    return instance_ids

def write_to_bucket(bucket, key, data):
    s3.put_object(Bucket=bucket, Key=key, Body=data.encode('utf8'))
    

def lambda_handler(event, context):
    try:
        all_instance_ids = get_instance_ids("swb-aim-ahead-unused-instances-artifacts", "instances-launched-28daysago.csv")
        logged_instance_ids = get_instance_ids("aimahead-swb-prod-notification-artifacts", "swb_day28_loggedIn_instances.csv")
        instances_not_logged = set_difference(all_instance_ids, logged_instance_ids)
        write_to_bucket("swb-aim-ahead-unused-instances-artifacts", "swb-day28-instances-not-loggedIn.csv", instances_not_logged)

        return instances_not_logged
    except Exception as e:
        print(e)
        raise e

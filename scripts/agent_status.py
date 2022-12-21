#!/usr/bin/python

import boto3
import os
import subprocess
import json
import urllib.request
import subprocess
direct_output = subprocess.check_output('TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`  && curl -H "X-aws-ec2-metadata-token: $TOKEN" -v http://169.254.169.254/latest/meta-data/instance-id', shell=True)
print(direct_output)
instanceid=direct_output.decode("utf-8")
print(instanceid)

status = os.system('systemctl is-active SplunkForwarder.service')
cloudwatch = boto3.client('cloudwatch',region_name="us-east-1")

if status == 0:
# Put custom metrics
        cloudwatch.put_metric_data( MetricData=[{'MetricName': 'splunk_status','Dimensions': [{'Name': 'Status','Value': 'status_code'},{'Name' : 'InstanceID' , 'Value': instanceid},],'Unit': 'None','Value': 1.0, },],Namespace='splunk_status')
else:
# Put custom metrics
        cloudwatch.put_metric_data( MetricData=[{'MetricName': 'splunk_status','Dimensions': [{'Name': 'Status','Value':'status_code'},{'Name' : 'InstanceID' , 'Value': instanceid}, ],'Unit': 'None','Value': 0.0},],Namespace='splunk_status')
        


status1 = os.system('systemctl is-active ds_agent.service')
cloudwatch = boto3.client('cloudwatch',region_name="us-east-1")

if status1 == 0:
# Put custom metrics
        cloudwatch.put_metric_data( MetricData=[{'MetricName': 'dsmagent_status','Dimensions': [{'Name': 'Status','Value': 'status_code'},{'Name' : 'InstanceID' , 'Value': instanceid}, ],'Unit': 'None','Value': 1.0, },],Namespace='dsmagent_status')
        
else:
# Put custom metrics
        cloudwatch.put_metric_data( MetricData=[{'MetricName': 'dsmagent_status','Dimensions': [{'Name': 'Status','Value':'status_code'},{'Name' : 'InstanceID' , 'Value': instanceid}, ],'Unit': 'None','Value': 0.0},],Namespace='dsmagent_status')
        


status2 = os.system('systemctl is-active nessusagent.service')
cloudwatch = boto3.client('cloudwatch',region_name="us-east-1")

if status2 == 0:
# Put custom metrics
        cloudwatch.put_metric_data( MetricData=[{'MetricName': 'nessusagent_status','Dimensions': [{'Name': 'Status','Value': 'status_code'},{'Name' : 'InstanceID' , 'Value': instanceid}, ],'Unit': 'None','Value': 1.0, },],Namespace='nessusagent_status')
        
else:
# Put custom metrics
        cloudwatch.put_metric_data( MetricData=[{'MetricName': 'nessusagent_status','Dimensions': [{'Name': 'Status','Value':'status_code'},{'Name' : 'InstanceID' , 'Value': instanceid}, ],'Unit': 'None','Value': 0.0},],Namespace='nessusagent_status')
        
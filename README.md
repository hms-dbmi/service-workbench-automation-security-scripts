# Service Workbench automation and security scripts

## Features
* Notify users about unused EC2 instances and SageMaker notebooks after 21 days of unuse
* Delete unused EC2 Instances & SageMaker notebooks after 7 days
* Use AWS Lambda, DynamoDB, S3, SNS, and EventBridge to power the service
* Lambda function to track and delete SSH keys older than 90 days from the DynamoDB Table
* SWB Auto Stop functionality for EC2 instances based on CPU Utilization that is customized for the platform and instance type

## Getting Started
To use the HMS Service Workbench, you'll need to set up the following prerequisites:
* An SWB AWS account
* The AWS CLI installed and configured on your machine
* AWS IAM permissions to create and manage Lambda functions, DynamoDB tables, S3 buckets, SNS topics, and EventBridge rules and events

## Usage
Once the HMS Service Workbench is deployed, it will automatically begin checking for unused EC2 instances and SageMaker notebooks according to the configured frequencies. If any unused resources are found, the service will send a notification to the specified email address based on Tags. If a resource has not been used in the specified grace period, it will be deleted.

## Agents/Scripts installed and purpose of each

Linux
* A script is in place to send the staus of each of the agent to CloudWatch metrics on linux instances. 
* Splunk agent V9.0.1 is used to pull in system logs into the Splunk SIEM in boundary. 
* Trend Micro DSM agent (latest available stable version) used for Anti Virus/Malware, IDS/IPS, Firewall etc. 
* Nessus Agent v10.3.1 is used to perform vulnerablity scans. 

Windows

* CloudWatch agent (latest available stable version) to push status of agents. 
* Splunk agent V9.0.1 is used to pull in system logs into the Splunk SIEM in boundary. 
* Trend Micro DSM agent (latest available stable version) used for Anti Virus/Malware, IDS/IPS, Firewall etc. 
* Nessus Agent v10.3.1 is used to perform vulnerablity scans.


This was developed by stackArmor ( https://stackarmor.com ) in support of HMS/DBMI for their SWB efforts.

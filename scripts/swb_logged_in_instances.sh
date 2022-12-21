#!/bin/bash

cd /opt/splunk/etc/apps/search/lookups/

# Remove heading and quotes from the files
sed -i -e '1d' -e 's/"//g' /opt/splunk/etc/apps/search/lookups/swb_win_logged_in_instances.csv
sort -u /opt/splunk/etc/apps/search/lookups/swb_win_logged_in_instances.csv -o /opt/splunk/etc/apps/search/lookups/swb_win_logged_in_instances.csv

sed -i -e '1d' -e 's/"//g' /opt/splunk/etc/apps/search/lookups/swb_lin_logged_in_instances.csv
sed -i 's/.ec2.internal//g' swb_lin_logged_in_instances.csv
sed -i 's/[^ ]*ip[^ ]*//ig' swb_lin_logged_in_instances.csv
sort -u /opt/splunk/etc/apps/search/lookups/swb_lin_logged_in_instances.csv -o /opt/splunk/etc/apps/search/lookups/swb_lin_logged_in_instances.csv

# Combine the files into one file
cat swb_win_logged_in_instances.csv swb_lin_logged_in_instances.csv > /opt/splunk/etc/apps/search/lookups/swb_day21_loggedIn_instances.csv

# Copy file to s3 bucket
aws s3 cp /opt/splunk/etc/apps/search/lookups/swb_day21_loggedIn_instances.csv s3://aimahead-swb-notification-artifacts/ --acl bucket-owner-full-control
aws s3 cp /opt/splunk/etc/apps/search/lookups/swb_day21_loggedIn_instances.csv s3://aimahead-swb-prod-notification-artifacts/ --acl bucket-owner-full-control
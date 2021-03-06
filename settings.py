# Override any keys below by putting them in a local_settings.py. Some
# overrides are required, signaled by a #* on the same line.

import os

### Get these from: http://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key
aws_access_key = None #*
aws_secret_key = None #*

### aws security config
security_groups = None #*

### key pair name
key_pair_name = None #*

### path to ssh private key
ec2_ssh_key = None #*
ec2_ssh_username = 'ubuntu' # ami specific

### five cannons is a healthy blast
num_cannons = 5

### Availbility zones: http://alestic.com/2009/07/ec2-availability-zones
placement = 'us-east-1a'

### ami key from: http://uec-images.ubuntu.com/releases/10.10/release/
ami_key = 'ami-ccf405a5'
instance_type = 't1.micro'

### scripts for building environments
env_scripts_dir = os.path.abspath(os.path.dirname('./env_scripts/'))

try:
    from local_settings import *
except:
    pass

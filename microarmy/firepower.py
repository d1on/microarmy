import eventlet
import boto
import time
import os

from microarmy.communications import (
    ssh_connect,
    exec_command,
    put_file,
)

### Override any defaults in config.py with a local_config.py
from settings import (
    aws_access_key,
    aws_secret_key,
    security_groups,
    key_pair_name,
    num_cannons,
    placement,
    ami_key,
    instance_type,
    env_scripts_dir,
)

pool = eventlet.GreenPool()

###
### Cannon functions
###

CANNON_INIT_SCRIPT = 'build_cannon.sh'

def init_cannons():
    """Creates the ec2 instances and returns a list of publicly accessible
    dns names, mapped to each instance.
    """
    ec2_conn = boto.connect_ec2(aws_access_key, aws_secret_key)

    ### Track down an image for our AMI
    images = ec2_conn.get_all_images(ami_key)
    image = images[0]

    ### Will need unbuffered output
    print 'Deploying cannons... ',
    
    ### Create n instances
    r = image.run(min_count=num_cannons,
                  max_count=num_cannons,
                  placement=placement,
                  security_groups=security_groups,
                  key_name=key_pair_name,
                  instance_type=instance_type)

    ### Store public_dns_names
    public_dns_names = []

    running = False
    while not running:
        time.sleep(5)
        [i.update() for i in r.instances]
        status = [i.state for i in r.instances]
        if status.count('running') == len(r.instances):
            running = True
            print 'Done!'
            for i in r.instances:
                print '%s|%s|%s|%s' % (i.ami_launch_index, r.id, 
                                       i.public_dns_name, i.private_dns_name)
                public_dns_names.append(i.public_dns_name)
    return public_dns_names

def _setup_a_cannon(hostname):
    """Connects to the hostname and installs all the tools required for the
    load test.

    Returns a boolean for successful setup.
    """
    ssh_conn = ssh_connect(hostname)
    
    # copy script to cannon and make it executable
    script_path = env_scripts_dir + '/' + CANNON_INIT_SCRIPT
    put_file(ssh_conn, script_path, CANNON_INIT_SCRIPT)
    response = exec_command(ssh_conn, 'chmod 755 ~/%s' % CANNON_INIT_SCRIPT)
    if response: # response would be error output
        print 'Unable to chmod cannon script: %s' % (CANNON_INIT_SCRIPT)
        print response
        return False

    # execute the setup script (expect this call to take a while)
    response = exec_command(ssh_conn, 'sudo ./%s' % CANNON_INIT_SCRIPT)
    return (hostname, response)

def setup_cannons(hostnames):
    """Launches a coroutine to configure each host and waits for them to
    complete before compiling a list of responses
    """
    print 'Loading cannons... ',
    pile = eventlet.GreenPile(pool)
    for h in hostnames:
        pile.spawn(_setup_a_cannon, h)
    responses = list(pile)
    print 'Done!'
    return responses

def fire_cannon(cannon_host, target):
    """Handles the details of telling a host to fire"""
    ssh_conn = ssh_connect(cannon_host)
    remote_command = 'siege -c200 -t10s %s' % (target)
    # Siege writes stats to stderr
    response = exec_command(ssh_conn, remote_command, return_stderr=True)
    return response
    

def slam_host(cannon_hosts, target):
    """Coordinates `cannon_hosts` to use the specified siege coordates on
    `target` and report back the performance.
    """
    pile = eventlet.GreenPile(pool)
    for h in cannon_hosts:
        pile.spawn(fire_cannon, h, target)
    responses = list(pile)
    report = parse_responses(responses)
    return report

def parse_responses(responses):
    """Quick and dirty."""
    aggregate_dict = {
        'num_trans': [],
        'elapsed': [],
        'tran_rate': [],
    }
    
    for response in responses:
        num_trans = response[5].split('\t')[2].strip()[:-5]
        elapsed = response[7].split('\t')[2].strip()[:-5]
        tran_rate = response[10].split('\t')[1].strip()[:-10]
        
        aggregate_dict['num_trans'].append(num_trans)
        aggregate_dict['elapsed'].append(elapsed)
        aggregate_dict['tran_rate'].append(tran_rate)
        
    return aggregate_dict

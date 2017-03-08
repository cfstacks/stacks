import time

import botocore
import botocore.exceptions


def get_ami_id(conn, name):
    '''Return the first AMI ID given its name'''
    images = list(conn.images.filter(Filters=[{'Name': 'name', 'Values': [name]}]))
    if len(images) != 0:
        return images[0].id
    else:
        raise RuntimeError('{} AMI not found'.format(name))


def get_zone_id(conn, name):
    '''Return the first Route53 zone ID given its name'''
    zone = conn.list_hosted_zones_by_name(
        DNSName=name,
        MaxItems="1",
    )
    if zone:
        return zone['HostedZones'][0]['Id'].split('/')[2]
    else:
        raise RuntimeError('{} zone not found'.format(name))


def get_vpc_id(conn, name):
    '''Return the first VPC ID given its name'''
    vpcs = list(conn.vpcs.filter(Filters=[{'Name': 'tag:name', 'Values': [name]}]))
    if len(vpcs) == 1:
        return vpcs[0].id
    else:
        raise RuntimeError('{} VPC not found'.format(name))


def get_stack_output(conn, name, key):
    '''Return stack output key value'''
    result = conn.describe_stacks(name)
    if len(result) != 1:
        raise RuntimeError('{} stack not found'.format(name))
    outputs = [s.outputs for s in result][0]
    for output in outputs:
        if output.key == key:
            return output.value
    raise RuntimeError('{} output not found'.format(key))


def get_stack_tag(conn, name, tag):
    '''Return stack tag'''
    result = conn.describe_stacks(name)
    if len(result) != 1:
        raise RuntimeError('{} stack not found'.format(name))
    tags = [s.tags for s in result][0]
    return tags.get(tag, '')


def get_stack_resource(conn, stack_name, logical_id):
    '''Return a physical_resource_id given its logical_id'''
    resources = conn.describe_stack_resources(StackName=stack_name)
    for resource in resources['StackResources']:
        # TODO: would be nice to check for resource_status
        if resource['LogicalResourceId'] == logical_id:
            return resource['PhysicalResourceId']
    return None

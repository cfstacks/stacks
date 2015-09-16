from .utils import throttling_retry


@throttling_retry
def get_ami_id(conn, name):
    '''Returns the first AMI ID given its name'''
    images = conn.get_all_images(filters={'name': name})
    conn.close()
    if len(images) != 0:
        return images[0].id
    else:
        raise RuntimeError('{} AMI not found'.format(name))


@throttling_retry
def get_zone_id(conn, name):
    '''Returns the first Route53 zone ID given its name'''
    zone = conn.get_zone(name)
    conn.close()
    if zone:
        return zone.id
    else:
        raise RuntimeError('{} zone not found'.format(name))


@throttling_retry
def get_vpc_id(conn, name):
    '''Returns the first VPC ID given its name and region'''
    vpcs = conn.get_all_vpcs(filters={'tag:Name': name})
    conn.close()
    if len(vpcs) == 1:
        return vpcs[0].id
    else:
        raise RuntimeError('{} VPC not found'.format(name))


@throttling_retry
def get_stack_output(conn, name, key):
    '''Returns stack output key value'''
    result = conn.describe_stacks(name)
    if len(result) != 1:
        raise RuntimeError('{} stack not found'.format(name))
    outputs = [s.outputs for s in result][0]
    for output in outputs:
        if output.key == key:
            return output.value
    raise RuntimeError('{} output not found'.format(key))


@throttling_retry
def get_stack_tag(conn, name, tag):
    '''Returns stack tag'''
    result = conn.describe_stacks(name)
    if len(result) != 1:
        raise RuntimeError('{} stack not found'.format(name))
    tags = [s.tags for s in result][0]
    return tags.get(tag, '')

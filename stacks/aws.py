import time

from boto.exception import BotoServerError


def throttling_retry(func):
    '''Retry when AWS is throttling API calls'''
    def retry_call(*args, **kwargs):
        retries = 0
        while True:
            try:
                retval = func(*args)
                return retval
            except BotoServerError as err:
                if err.code == 'Throttling' and retries <= 3:
                    sleep = 3 * (2**retries)
                    print('Being throttled. Retrying after {} seconds..'.format(sleep))
                    time.sleep(sleep)
                    retries += 1
                else:
                    raise err
    return retry_call


@throttling_retry
def get_ami_id(conn, name):
    '''Return the first AMI ID given its name'''
    images = conn.get_all_images(filters={'name': name})
    conn.close()
    if len(images) != 0:
        return images[0].id
    else:
        raise RuntimeError('{} AMI not found'.format(name))


@throttling_retry
def get_zone_id(conn, name):
    '''Return the first Route53 zone ID given its name'''
    zone = conn.get_zone(name)
    conn.close()
    if zone:
        return zone.id
    else:
        raise RuntimeError('{} zone not found'.format(name))


@throttling_retry
def get_vpc_id(conn, name):
    '''Return the first VPC ID given its name and region'''
    vpcs = conn.get_all_vpcs(filters={'tag:Name': name})
    conn.close()
    if len(vpcs) == 1:
        return vpcs[0].id
    else:
        raise RuntimeError('{} VPC not found'.format(name))


@throttling_retry
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


@throttling_retry
def get_stack_tag(conn, name, tag):
    '''Return stack tag'''
    result = conn.describe_stacks(name)
    if len(result) != 1:
        raise RuntimeError('{} stack not found'.format(name))
    tags = [s.tags for s in result][0]
    return tags.get(tag, '')

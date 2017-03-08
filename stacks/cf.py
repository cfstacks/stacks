'''
Cloudformation related functions
'''
# An attempt to support python 2.7.x
from __future__ import print_function

import builtins
import hashlib
import json
import sys
import time
from fnmatch import fnmatch
from os import path

import jinja2
import jinja2.meta
import yaml
from tabulate import tabulate

import botocore
import botocore.exceptions
from stacks.aws import get_stack_tag

YES = ['y', 'Y', 'yes', 'YES', 'Yes']
FAILED_STACK_STATES = [
    'CREATE_FAILED',
    'ROLLBACK_FAILED',
    'DELETE_FAILED',
    'UPDATE_ROLLBACK_FAILED'
]
COMPLETE_STACK_STATES = [
    'CREATE_COMPLETE',
    'UPDATE_COMPLETE',
]
ROLLBACK_STACK_STATES = [
    'ROLLBACK_COMPLETE',
    'UPDATE_ROLLBACK_COMPLETE',
]
IN_PROGRESS_STACK_STATES = [
    'CREATE_IN_PROGRESS',
    'ROLLBACK_IN_PROGRESS',
    'DELETE_IN_PROGRESS',
    'UPDATE_IN_PROGRESS',
    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
    'UPDATE_ROLLBACK_IN_PROGRESS',
    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
]


def gen_template(tpl_file, config):
    '''Return a tuple of json string template and options dict'''
    tpl_path, tpl_fname = path.split(tpl_file.name)
    env = _new_jinja_env(tpl_path)

    _check_missing_vars(env, tpl_file, config)

    tpl = env.get_template(tpl_fname)
    rendered = tpl.render(config)
    try:
        docs = list(yaml.load_all(rendered))
    except yaml.parser.ParserError as err:
        print(err)
        sys.exit(1)

    if len(docs) == 2:
        stack = json.dumps(docs[1], indent=2, sort_keys=True)
        stack_metadata = docs[0]
    else:
        stack = json.dumps(docs[0], indent=2, sort_keys=True)
        stack_metadata = None
    return (stack, stack_metadata)


def _check_missing_vars(env, tpl_file, config):
    '''Check for missing variables in a template string'''
    tpl_str = tpl_file.read()
    ast = env.parse(tpl_str)
    required_properties = jinja2.meta.find_undeclared_variables(ast)
    missing_properties = required_properties - config.keys() - set(dir(builtins))

    if len(missing_properties) > 0:
        print('Required properties not set: {}'.format(','.join(missing_properties)))
        sys.exit(1)


def _new_jinja_env(tpl_path):
    loader = jinja2.loaders.FileSystemLoader(tpl_path)
    env = jinja2.Environment(loader=loader)
    return env


# TODO(vaijab): fix 'S3ResponseError: 301 Moved Permanently', this happens when
# a connection to S3 is being made from a different region than the one a bucket
# was created in.
def upload_template(conn, config, tpl, stack_name):
    '''Upload a template to S3 bucket and returns S3 key url'''
    bn = config.get('templates_bucket_name', '{}-stacks-{}'.format(config['env'], config['region']))

    try:
        config['s3_conn'].head_bucket(Bucket=bn)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            print('Bucket {} does not exist.'.format(bn))
        else:
            print('Error connecting to bucket: {}'.format(bn))
            exit(1)

    h = _calc_md5(tpl)
    config['s3_conn'].put_object(
        Bucket=bn,
        Key='{}/{}/{}'.format(config['env'], stack_name, h),
        Body=tpl,
        )

    url = config['s3_conn'].generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bn,
            'Key': '{}/{}/{}'.format(config['env'], stack_name, h),
        },
        ExpiresIn=30)

    return url


def stack_resources(conn, stack_name, logical_resource_id=None):
    '''List stack resources'''
    describe_args = {
        "StackName": stack_name
    }
    if logical_resource_id != None:
        describe_args['LogicalResourceId'] = logical_resource_id
    try:
        result = conn.describe_stack_resources(**describe_args)
    except botocore.exceptions.ClientError as e:
        print(e)
        sys.exit(1)
    resources = []
    if logical_resource_id:
        resources.append([r.physical_resource_id for r in result])
    else:
        for r in result:
            columns = [
                r.logical_resource_id,
                r.physical_resource_id,
                r.resource_type,
                r.resource_status,
            ]
            resources.append(columns)

    if len(result) >= 1:
        return tabulate(resources, tablefmt='plain')
    return None


def stack_outputs(conn, stack_name, output_name):
    '''List stacks outputs'''
    try:
        result = conn.describe_stacks(StackName=stack_name)
    except botocore.exceptions.ClientError as err:
        print(err.message)
        sys.exit(1)

    outputs = []
    outs = [s.outputs for s in result][0]
    for o in outs:
        if not output_name:
            columns = [o.key, o.value]
            outputs.append(columns)
        elif output_name and o.key == output_name:
            outputs.append([o.value])

    if len(result) >= 1:
        return tabulate(outputs, tablefmt='plain')
    return None


def list_stacks(conn, name_filter='*', verbose=False):
    '''List active stacks'''
    # FIXME this needs to handle pagination
    stacks = conn.list_stacks()['StackSummaries']

    results = []
    for stack in stacks:
        if name_filter and fnmatch(stack['StackName'], name_filter):
            columns = [stack['StackName'], stack['StackStatus']]
            if verbose:
                env = get_stack_tag(conn, stack['StackName'], 'Env')
                columns.append(env)
                columns.append(stack['TemplateDescription'])
            results.append(columns)
            columns = []

    if len(results) >= 1:
        return tabulate(results, tablefmt='plain')
    return None


def create_stack(conn, stack_name, tpl_file, config, update=False, dry=False,
                 follow=False, create_on_update=False):
    '''Create or update CloudFormation stack from a jinja2 template'''
    tpl, metadata = gen_template(tpl_file, config)

    # Set default tags which cannot be overwritten
    default_tags = [
        {'Key': 'Env',
         'Value': config['env']},
        {'Key': 'MD5Sum',
         'Value': _calc_md5(tpl)}
    ]

    if metadata:
        # Tags are specified in the format
        # tags:
        #  - key: <key>
        #    value: <value>
        # in metadata, so we have to rebuild that list with the 'key' and
        # 'value' keys capitalised (which is how Cloudformation wants them)
        tags = [{'Key': tag['key'], 'Value': tag['value']} for tag in metadata.get('tags', [])]
        tags.extend(default_tags)
        name_from_metadata = metadata.get('name')
        disable_rollback = metadata.get('disable_rollback')
        if disable_rollback == None:
            disable_rollback = False
    else:
        name_from_metadata = None
        tags = default_tags
        disable_rollback = False

    if stack_name:
        sn = stack_name
    elif name_from_metadata:
        sn = name_from_metadata
    else:
        print('Stack name must be specified via command line argument or stack metadata.')
        sys.exit(1)

    tpl_size = len(tpl)

    if dry:
        print(tpl, flush=True)
        print('Name: {}'.format(sn), file=sys.stderr, flush=True)
        print('Tags: {}'.format(', '.join(['{}={}'.format(tag['Key'], tag['Value']) for tag in tags])), file=sys.stderr, flush=True)
        print('Template size:', tpl_size, file=sys.stderr, flush=True)
        return True

    stack_args = {
        'StackName': sn,
        "Tags": tags,
        "Capabilities": ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
        "DisableRollback": disable_rollback
    }

    if tpl_size > 51200:
        stack_args['TemplateURL'] = upload_template(conn, config, tpl, sn)
    else:
        stack_args['TemplateBody'] = tpl

    try:
        if update and create_on_update and not stack_exists(conn, sn):
            conn.create_stack(**stack_args)
        elif update:
            #Can't disable rollback when updating
            del stack_args['DisableRollback']
            conn.update_stack(**stack_args)
        else:
            conn.create_stack(**stack_args)
        if follow:
            get_events(conn, sn, follow, 10)
    except botocore.exceptions.ClientError as err:
        # Do not exit with 1 when one of the below messages are returned
        non_error_messages = [
            'No updates are to be performed',
            'already exists',
        ]
        if any(s in str(err) for s in non_error_messages):
            print(str(err))
            sys.exit(0)
        print(str(err))
        sys.exit(1)


def _calc_md5(j):
    '''Calculate an MD5 hash of a string'''
    return hashlib.md5(j.encode()).hexdigest()


# FIXME: this function takes a region, but only uses it to print out a message
# about what region you're about to delete. We should probably work this out
# from the session info...
def delete_stack(conn, stack_name, region, profile, confirm):
    '''Deletes stack given its name'''
    msg = ('You are about to delete the following stack:\n'
           'Name: {}\n'
           'Region: {}\n'
           'Profile: {}\n').format(stack_name, region, profile)
    if not confirm:
        print(msg)
        response = input('Are you sure? [y/N] ')
    else:
        response = 'yes'

    if response in YES:
        try:
            conn.delete_stack(stack_name)
        except botocore.exceptions.ClientError as err:
            if 'does not exist' in err.message:
                print(err.message)
                sys.exit(0)
            else:
                print(err.message)
                sys.exit(1)


def get_events(conn, stack_name, follow, lines=None):
    '''Get stack events in chronological order

    Prints tabulated list of events in chronological order
    '''
    poll = True
    seen_ids = set()
    describe_stack_events_args = {
        'StackName': stack_name
    }
    next_token = False
    try:
        while poll:
            #Only send the NextToken argument if we have a token
            if next_token:
                describe_stack_events_args['NextToken'] = next_token
            events = conn.describe_stack_events(**describe_stack_events_args)
            if 'NextToken' in events:
                next_token = events['NextToken']
            events_display = [(
                event['Timestamp'],
                event['ResourceStatus'],
                event['ResourceType'],
                event['LogicalResourceId'],
                event.get('ResourceStatusReason', '')
            ) for event in events['StackEvents'][:lines] if event['EventId'] not in seen_ids]

            seen_ids |= set([event['EventId'] for event in events['StackEvents']])

            if len(events_display) >= 1:
                print(tabulate(reversed(events_display), tablefmt='plain'), flush=True)

            # Check for stack status, exit with 1 if stack has failed or exit with 0
            # if it is in successfull state. Otherwise continue polling.
            stack_status = get_stack_status(conn, stack_name)
            if stack_status in FAILED_STACK_STATES + ROLLBACK_STACK_STATES:
                sys.exit(1)
            elif stack_status in COMPLETE_STACK_STATES:
                sys.exit(0)

            poll = follow
            if poll:
                time.sleep(5)
    except botocore.exceptions.ClientError as err:
        if 'does not exist' in err.message:
            print(err.message)
            sys.exit(0)
        else:
            print(err.message)
            sys.exit(1)


def get_stack_status(conn, stack_name):
    '''Check stack status'''
    stacks = []
    resp = conn.list_stacks()
    stacks.extend(resp['StackSummaries'])
    while 'NextToken' in resp:
        resp = conn.list_stacks(NextToken=resp['NextToken'])
        stacks.extend(resp['StackSummaries'])
    for s in stacks:
        if s['StackName'] == stack_name and s['StackStatus'] != 'DELETE_COMPLETE':
            return s['StackStatus']
    return None


def stack_exists(conn, stack_name):
    '''Check whether stack_name exists

    CF keeps deleted duplicate stack names with DELETE_COMPLETE status, which is
    treated as non existing stack.
    '''
    status = get_stack_status(conn, stack_name)
    if status == 'DELETE_COMPLETE' or status is None:
        return False
    return True

'''
Cloudformation related functions
'''

import sys
import time
import yaml
import json
import jinja2
import hashlib
import boto

from os import path
from jinja2 import meta
from fnmatch import fnmatch
from tabulate import tabulate
from boto.exception import BotoServerError

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


def gen_template(tpl_file, config, pretty=False):
    '''Return generated CloudFormation template string'''
    tpl_path, tpl_fname = path.split(tpl_file.name)
    env = _new_jinja_env(tpl_path)

    _check_missing_vars(env, tpl_file, config)

    tpl = env.get_template(tpl_fname)
    rendered = tpl.render(config)
    docs = list(yaml.load_all(rendered))
    indent = 2 if pretty else None

    if len(docs) == 2:
        return (json.dumps(docs[1], indent=indent), docs[0])
    else:
        return (json.dumps(docs[0], indent=indent), None)


def _check_missing_vars(env, tpl_file, config):
    '''Check for missing variables in a template string'''
    tpl_str = tpl_file.read()
    ast = env.parse(tpl_str)
    required_properties = meta.find_undeclared_variables(ast)
    missing_properties = required_properties - config.keys()

    if len(missing_properties) > 0:
        print('Requred properties not set: {}'.format(','.join(missing_properties)))
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
        b = config['s3_conn'].get_bucket(bn)
    except boto.exception.S3ResponseError as err:
        if err.code == 'NoSuchBucket':
            print('Bucket {} does not exist.'.format(bn))
        else:
            print(err)
        sys.exit(1)

    h = hashlib.md5(tpl.encode('utf-8')).hexdigest()
    k = boto.s3.key.Key(b)
    k.key = '{}/{}/{}'.format(config['env'], stack_name, h)
    k.set_contents_from_string(tpl)
    url = k.generate_url(expires_in=30)
    return url


def list_stacks(conn, name_filter='*', verbose=False):
    '''Lists active stacks'''
    states = FAILED_STACK_STATES + COMPLETE_STACK_STATES + IN_PROGRESS_STACK_STATES
    s = conn.list_stacks(states)

    stacks = []
    for n in s:
        if name_filter and _match_stack_name(n.stack_name, name_filter):
            columns = [n.stack_name, n.stack_status]
            if verbose:
                env = get_stack_tag(conn, n.stack_name, 'Env')
                columns.append(env)
                columns.append(n.template_description)
            stacks.append(columns)
            columns = []

    if len(stacks) >= 1:
        return tabulate(stacks, tablefmt='plain')
    else:
        return 'No stacks found'


def _match_stack_name(stack_name, pattern):
    '''Match stack name against a glob pattern'''
    return fnmatch(stack_name, pattern)


def create_stack(conn, stack_name, stack_template, config, update=False, dry=False):
    '''Creates or updates CloudFormation stack from a jinja2 template'''
    tpl, options = gen_template(stack_template, config, dry)

    tags = {'Env': config['env']}

    if options:
        tags.update(_extract_tags(options))
        extracted_name = _extract_name(options)

    if stack_name:
        sn = stack_name
    elif extracted_name:
        sn = extracted_name
    else:
        print('Stack name must be specified via command line argument or template metadata.')
        sys.exit(1)

    if dry:
        print(tpl)
        print('Name: {}'.format(sn), file=sys.stderr)
        print('Tags: ' + ', '.join(['{}={}'.format(k, v) for (k, v) in tags.items()]), file=sys.stderr)
        print("Template size: " + str(len(tpl)), file=sys.stderr)
        return True

    url = upload_template(conn, config, tpl, sn)

    try:
        if update:
            conn.update_stack(sn, template_url=url, tags=tags, capabilities=['CAPABILITY_IAM'])
        else:
            conn.create_stack(sn, template_url=url, tags=tags, capabilities=['CAPABILITY_IAM'])
    except BotoServerError as err:
        print(err)


def _extract_tags(options):
    '''Return tags from template options metadata'''
    tags = {}
    if options.get('metadata'):
        metadata = options.get('metadata')

    if metadata.get('tags'):
        for tag in metadata['tags']:
            if tag['key'] == 'Env':
                continue
            tags[tag['key']] = tag['value']
    return tags


def _extract_name(options):
    '''Return stack name from template options metadata'''
    if options.get('metadata'):
        metadata = options.get('metadata')

    return metadata.get('name')


def delete_stack(conn, stack_name, region, profile):
    '''Deletes stack given its name'''
    msg = ('You are about to delete the following stack:\n'
           'Name: {}\n'
           'Region: {}\n'
           'Profile: {}\n').format(stack_name, region, profile)
    print(msg)
    response = input('Are you sure? [y/N] ')
    if response in YES:
        conn.delete_stack(stack_name)


def get_events(conn, stack_name, follow, lines):
    '''Get stack events in chronological order

    Prints tabulated list of events in chronological order
    '''
    poll = True
    seen_ids = set()
    next_token = None
    while poll:
        events = conn.describe_stack_events(stack_name, next_token)
        next_token = events.next_token
        events_display = [(
            event.timestamp,
            event.resource_status,
            event.resource_type,
            event.logical_resource_id,
            event.resource_status_reason
        ) for event in events[:lines] if event.event_id not in seen_ids]

        seen_ids |= set([event.event_id for event in events])

        if len(events_display) >= 1:
            print(tabulate(reversed(events_display), tablefmt='plain'))

        # Check for stack status, exit with 1 if stack has failed or exit with 0
        # if it is in successfull state. Otherwise continue polling.
        stack_status = get_stack_status(conn, stack_name)
        if stack_status in FAILED_STACK_STATES + ROLLBACK_STACK_STATES:
            sys.exit(1)
        elif stack_status in COMPLETE_STACK_STATES:
            sys.exit(0)

        poll = follow
        if poll:
            time.sleep(1)


def get_stack_status(conn, stack_name):
    '''Return stack status'''
    stacks = conn.list_stacks()
    for s in stacks:
        if s.stack_name == stack_name:
            return s.stack_status
    return None

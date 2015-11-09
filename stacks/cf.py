'''
Cloudformation related functions
'''
# An attempt to support python 2.7.x
from __future__ import print_function

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
        return (json.dumps(docs[1], indent=2, sort_keys=True), docs[0])
    else:
        return (json.dumps(docs[0], indent=2, sort_keys=True), None)


def _check_missing_vars(env, tpl_file, config):
    '''Check for missing variables in a template string'''
    tpl_str = tpl_file.read()
    ast = env.parse(tpl_str)
    required_properties = meta.find_undeclared_variables(ast)
    missing_properties = required_properties - config.keys()

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
        b = config['s3_conn'].get_bucket(bn)
    except boto.exception.S3ResponseError as err:
        if err.code == 'NoSuchBucket':
            print('Bucket {} does not exist.'.format(bn))
        else:
            print(err)
        sys.exit(1)

    h = _calc_md5(tpl)
    k = boto.s3.key.Key(b)
    k.key = '{}/{}/{}'.format(config['env'], stack_name, h)
    k.set_contents_from_string(tpl)
    url = k.generate_url(expires_in=30)
    return url


def list_stacks(conn, name_filter='*', verbose=False):
    '''List active stacks'''
    states = FAILED_STACK_STATES + COMPLETE_STACK_STATES + IN_PROGRESS_STACK_STATES
    s = conn.list_stacks(states)

    stacks = []
    for n in s:
        if name_filter and fnmatch(n.stack_name, name_filter):
            columns = [n.stack_name, n.stack_status]
            if verbose:
                env = get_stack_tag(conn, n.stack_name, 'Env')
                columns.append(env)
                columns.append(n.template_description)
            stacks.append(columns)
            columns = []

    if len(stacks) >= 1:
        return tabulate(stacks, tablefmt='plain')
    return None


def create_stack(conn, stack_name, tpl_file, config, update=False, dry=False,
                 follow=False, create_on_update=False):
    '''Create or update CloudFormation stack from a jinja2 template'''
    tpl, metadata = gen_template(tpl_file, config)

    # Set default tags which cannot be overwritten
    default_tags = {
        'Env': config['env'],
        'MD5Sum': _calc_md5(tpl)
    }

    if metadata:
        tags = _extract_tags(metadata)
        tags.update(default_tags)
        name_from_metadata = metadata.get('name')
        disable_rollback = metadata.get('disable_rollback')
    else:
        name_from_metadata = None
        tags = default_tags
        disable_rollback = None

    if stack_name:
        sn = stack_name
    elif name_from_metadata:
        sn = name_from_metadata
    else:
        print('Stack name must be specified via command line argument or stack metadata.')
        sys.exit(1)

    tpl_size = len(tpl)

    if dry:
        print(tpl)
        print('Name: {}'.format(sn), file=sys.stderr)
        print('Tags: ' + ', '.join(['{}={}'.format(k, v) for (k, v) in tags.items()]), file=sys.stderr)
        print('Template size:', tpl_size, file=sys.stderr)
        return True

    if tpl_size > 51200:
        tpl_url = upload_template(conn, config, tpl, sn)
        tpl_body = None
    else:
        tpl_url = None
        tpl_body = tpl

    try:
        if update and create_on_update and not stack_exists(conn, sn):
            conn.create_stack(sn, template_url=tpl_url, template_body=tpl_body,
                              tags=tags, capabilities=['CAPABILITY_IAM'],
                              disable_rollback=disable_rollback)
        elif update:
            conn.update_stack(sn, template_url=tpl_url, template_body=tpl_body,
                              tags=tags, capabilities=['CAPABILITY_IAM'],
                              disable_rollback=disable_rollback)
        else:
            conn.create_stack(sn, template_url=tpl_url, template_body=tpl_body,
                              tags=tags, capabilities=['CAPABILITY_IAM'],
                              disable_rollback=disable_rollback)
        if follow:
            get_events(conn, sn, follow, 10)
    except BotoServerError as err:
        print(err.message)


def _extract_tags(metadata):
    '''Return tags from a metadata'''
    tags = {}

    for tag in metadata.get('tags', []):
        tags[tag['key']] = tag['value']
    return tags


def _calc_md5(j):
    '''Calculate an MD5 hash of a string'''
    return hashlib.md5(j.encode()).hexdigest()


def delete_stack(conn, stack_name, region, profile):
    '''Deletes stack given its name'''
    msg = ('You are about to delete the following stack:\n'
           'Name: {}\n'
           'Region: {}\n'
           'Profile: {}\n').format(stack_name, region, profile)
    print(msg)
    response = input('Are you sure? [y/N] ')

    if response in YES:
        try:
            conn.delete_stack(stack_name)
        except BotoServerError as err:
            print(err.message)
            sys.exit(0)


def get_events(conn, stack_name, follow, lines=None):
    '''Get stack events in chronological order

    Prints tabulated list of events in chronological order
    '''
    poll = True
    seen_ids = set()
    next_token = None
    try:
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
    except BotoServerError as err:
        print(err.message)
        sys.exit(0)


def get_stack_status(conn, stack_name):
    '''Check stack status'''
    stacks = conn.list_stacks()
    for s in stacks:
        if s.stack_name == stack_name:
            return s.stack_status
    return None


def stack_exists(conn, stack_name):
    '''Check whether stack_name exists.'''
    try:
        conn.describe_stacks(stack_name)
        return True
    except BotoServerError:
        return False

"""
Cloudformation related functions
"""
# An attempt to support python 2.7.x
from __future__ import print_function

import sys
import builtins
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
from operator import attrgetter

from stacks.aws import get_stack_tag
from stacks.aws import throttling_retry
from stacks.states import FAILED_STACK_STATES, COMPLETE_STACK_STATES, ROLLBACK_STACK_STATES, IN_PROGRESS_STACK_STATES

YES = ['y', 'Y', 'yes', 'YES', 'Yes']


def gen_template(tpl_file, config):
    """Return a tuple of json string template and options dict"""
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
        return json.dumps(docs[1], indent=2, sort_keys=True), docs[0]
    else:
        return json.dumps(docs[0], indent=2, sort_keys=True), None


def _check_missing_vars(env, tpl_file, config):
    """Check for missing variables in a template string"""
    tpl_str = tpl_file.read()
    ast = env.parse(tpl_str)
    required_properties = meta.find_undeclared_variables(ast)
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
    """Upload a template to S3 bucket and returns S3 key url"""
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


def stack_resources(conn, stack_name, logical_resource_id=None):
    """List stack resources"""
    try:
        result = conn.describe_stack_resources(stack_name_or_id=stack_name,
                                               logical_resource_id=logical_resource_id)
    except BotoServerError as err:
        print(err.message)
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
    """List stacks outputs"""
    try:
        result = conn.describe_stacks(stack_name)
    except BotoServerError as err:
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
    """List active stacks"""
    states = FAILED_STACK_STATES + COMPLETE_STACK_STATES + IN_PROGRESS_STACK_STATES + ROLLBACK_STACK_STATES
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


def create_stack(conn, stack_name, tpl_file, config, update=False, dry=False, create_on_update=False):
    """Create or update CloudFormation stack from a jinja2 template"""
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

    if not stack_name:
        stack_name = name_from_metadata
    if not stack_name:
        print('Stack name must be specified via command line argument or stack metadata.')
        sys.exit(1)

    tpl_size = len(tpl)

    if dry:
        print(tpl, flush=True)
        print('Name: {}'.format(stack_name), file=sys.stderr, flush=True)
        print('Tags: ' + ', '.join(['{}={}'.format(k, v) for (k, v) in tags.items()]), file=sys.stderr, flush=True)
        print('Template size:', tpl_size, file=sys.stderr, flush=True)
        return True

    if tpl_size > 51200:
        tpl_url = upload_template(conn, config, tpl, stack_name)
        tpl_body = None
    else:
        tpl_url = None
        tpl_body = tpl

    try:
        if update and create_on_update and not stack_exists(conn, stack_name):
            conn.create_stack(stack_name, template_url=tpl_url, template_body=tpl_body,
                              tags=tags, capabilities=['CAPABILITY_IAM'],
                              disable_rollback=disable_rollback)
        elif update:
            conn.update_stack(stack_name, template_url=tpl_url, template_body=tpl_body,
                              tags=tags, capabilities=['CAPABILITY_IAM'],
                              disable_rollback=disable_rollback)
        else:
            conn.create_stack(stack_name, template_url=tpl_url, template_body=tpl_body,
                              tags=tags, capabilities=['CAPABILITY_IAM'],
                              disable_rollback=disable_rollback)
    except BotoServerError as err:
        # Do not exit with 1 when one of the below messages are returned
        non_error_messages = [
            'No updates are to be performed',
            'already exists',
        ]
        if any(s in err.message for s in non_error_messages):
            print(err.message)
            sys.exit(0)
        print(err.message)
        sys.exit(1)
    return stack_name


def _extract_tags(metadata):
    """Return tags from a metadata"""
    tags = {}

    for tag in metadata.get('tags', []):
        tags[tag['key']] = tag['value']
    return tags


def _calc_md5(j):
    """Calculate an MD5 hash of a string"""
    return hashlib.md5(j.encode()).hexdigest()


def delete_stack(conn, stack_name, region, profile, confirm):
    """Deletes stack given its name"""
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
        except BotoServerError as err:
            if 'does not exist' in err.message:
                print(err.message)
                sys.exit(0)
            else:
                print(err.message)
                sys.exit(1)
    else:
        sys.exit(0)


def get_events(conn, stack_name, next_token):
    """Get stack events"""
    try:
        events = conn.describe_stack_events(stack_name, next_token)
        next_token = events.next_token
        return sorted_events(events), next_token
    except BotoServerError as err:
        if 'does not exist' in err.message:
            print(err.message)
            sys.exit(0)
        else:
            print(err.message)
            sys.exit(1)


def sorted_events(events):
    """Sort stack events by timestamp"""
    return sorted(events, key=attrgetter('timestamp'))


def print_events(conn, stack_name, follow, lines=100):
    """Prints tabulated list of events"""
    events_display = []
    seen_ids = set()
    next_token = None

    while True:
        events, next_token = get_events(conn, stack_name, next_token)
        status = get_stack_status(conn, stack_name)
        if follow:
            events_display = [(event.timestamp, event.resource_status, event.resource_type, event.logical_resource_id,
                               event.resource_status_reason) for event in events if event.event_id not in seen_ids]
            if len(events_display) > 0:
                print(tabulate(events_display, tablefmt='plain'), flush=True)
                seen_ids |= set([event.event_id for event in events])
            if status not in IN_PROGRESS_STACK_STATES and next_token is None:
                break
            if next_token is None:
                time.sleep(5)
        else:
            events_display.extend([(event.timestamp, event.resource_status, event.resource_type,
                                    event.logical_resource_id, event.resource_status_reason)
                                   for event in events])
            if len(events_display) >= lines or next_token is None:
                break

    if not follow:
        print(tabulate(events_display[:lines], tablefmt='plain'), flush=True)

    return status


@throttling_retry
def get_stack_status(conn, stack_name):
    """Check stack status"""
    stacks = []
    resp = conn.list_stacks()
    stacks.extend(resp)
    while resp.next_token:
        resp = conn.list_stacks(next_token=resp.next_token)
        stacks.extend(resp)
    for s in stacks:
        if s.stack_name == stack_name and s.stack_status != 'DELETE_COMPLETE':
            return s.stack_status
    return None


def stack_exists(conn, stack_name):
    """Check whether stack_name exists

    CF keeps deleted duplicate stack names with DELETE_COMPLETE status, which is
    treated as non existing stack.
    """
    status = get_stack_status(conn, stack_name)
    if status == 'DELETE_COMPLETE' or status is None:
        return False
    return True

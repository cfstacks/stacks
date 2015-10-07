import sys

from tabulate import tabulate
from boto.exception import BotoServerError

from .utils import match_stack_name
from .aws import get_stack_tag
from .template import gen_template
from .template import upload_template

YES = ['y', 'Y', 'yes', 'YES', 'Yes']


def list_stacks(conn, name_filter='*', verbose=False):
    '''Lists active stacks'''
    stacks_filters = [
        'CREATE_COMPLETE',
        'CREATE_IN_PROGRESS',
        'CREATE_FAILED',
        'DELETE_IN_PROGRESS',
        'DELETE_FAILED',
        'ROLLBACK_COMPLETE',
        'ROLLBACK_FAILED',
        'ROLLBACK_IN_PROGRESS',
        'UPDATE_COMPLETE',
        'UPDATE_IN_PROGRESS',
        'UPDATE_ROLLBACK_COMPLETE',
        'UPDATE_ROLLBACK_FAILED',
        'UPDATE_ROLLBACK_IN_PROGRESS',
        'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
    ]

    s = conn.list_stacks(stacks_filters)

    stacks = []
    for n in s:
        if name_filter and match_stack_name(n.stack_name, name_filter):
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


def create_stack(conn, name, stack_template, config, update=False, dry=False):
    '''Creates or updates CloudFormation stack from a jinja2 template'''
    tpl, options = gen_template(stack_template, config, dry)

    tags = {}
    if options != None and options['metadata'] and options['metadata']['tags']:
        for tag in options['metadata']['tags']:
            tags[tag['key']] = tag['value']
    else:
        tags['Env'] = config['env']

    if dry:
        print(tpl)
        print("Template size: " + str(len(tpl)), file=sys.stderr)
        print("Tags: " + ', '.join(["{}={}".format(k,v) for (k,v) in tags.items()]), file=sys.stderr)
        return True
    else:
        url = upload_template(conn, config, tpl, name)

        try:
            if update:
                conn.update_stack(name, template_url=url, tags=tags, capabilities=['CAPABILITY_IAM'])
            else:
                conn.create_stack(name, template_url=url, tags=tags, capabilities=['CAPABILITY_IAM'])
        except BotoServerError as err:
            print(err)


def delete_stack(conn, name, region, profile):
    '''Deletes stack given its name'''
    msg = ('You are about to delete the following stack:\n'
           'name: {}\n'
           'region: {}\n'
           'profile: {}\n').format(name, region, profile)
    print(msg)
    response = input('Are you sure? [y/N] ')
    if response in YES:
        conn.delete_stack(name)

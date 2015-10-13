import sys
import argparse
import time
import signal

from tabulate import tabulate

import boto.ec2
import boto.vpc
import boto.route53
import boto.cloudformation
import boto.s3


from .config import get_region_name
from .config import load_config
from .aws import get_ami_id
from .aws import get_stack_tag
from .aws import get_zone_id
from .aws import get_vpc_id
from .aws import get_stack_output
from .cf import list_stacks
from .cf import create_stack
from .cf import delete_stack
from .cf import list_stack_events

YES = ['y', 'Y', 'yes', 'YES', 'Yes']

def handler(signum = None, frame = None):
    print('Stopping.')
    sys.exit(0)


def main():
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--profile')
    parser.add_argument('-r', '--region')
    subparsers = parser.add_subparsers(title='available subcommands', dest='subcommand')

    parser_list = subparsers.add_parser('list', help='List stacks')
    parser_list.add_argument('-v', '--verbose', action='store_true')
    parser_list.add_argument('name', default='*', nargs='?',
                             help='stack name or unix shell-style pattern')

    parser_create = subparsers.add_parser('create', help='Create a new stack')
    parser_create.add_argument('-t', '--template', required=True, type=argparse.FileType())
    parser_create.add_argument('-c', '--config', default='config.yaml',
                               required=False, type=argparse.FileType())
    parser_create.add_argument('name')
    parser_create.add_argument('-e', '--env', required=True)
    parser_create.add_argument('-P', '--property', required=False, action='append')
    parser_create.add_argument('-d', '--dry-run', action='store_true')

    parser_update = subparsers.add_parser('update', help='Update an existing stack')
    parser_update.add_argument('-t', '--template', required=True, type=argparse.FileType())
    parser_update.add_argument('-c', '--config', default='config.yaml',
                               required=False, type=argparse.FileType())
    parser_update.add_argument('name')
    parser_update.add_argument('-e', '--env', required=True)
    parser_update.add_argument('-P', '--property', required=False, action='append')
    parser_update.add_argument('-d', '--dry-run', action='store_true')

    parser_delete = subparsers.add_parser('delete', help='Delete an existing stack')
    parser_delete.add_argument('name')

    parser_events = subparsers.add_parser('events', help='List events from a stack')
    parser_events.add_argument('name')
    parser_events.add_argument('-f', '--follow', action='store_true', help='Poll for new events until stopped')
    parser_events.add_argument('-n', '--lines', default='10', type=int)

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    # set profile
    if args.profile:
        profile = args.profile
    else:
        profile = None

    # Set region name from cli arg or aws config file
    if args.region:
        region = args.region
    elif get_region_name(profile):
        region = get_region_name(profile)

    ec2_conn = boto.ec2.connect_to_region(region, profile_name=profile)
    vpc_conn = boto.vpc.connect_to_region(region, profile_name=profile)
    cf_conn = boto.cloudformation.connect_to_region(region, profile_name=profile)
    r53_conn = boto.route53.connect_to_region(region, profile_name=profile)
    s3_conn = boto.s3.connect_to_region(region, profile_name=profile)

    if args.subcommand == 'list':
        print(list_stacks(cf_conn, args.name, args.verbose))
        cf_conn.close()

    if args.subcommand == 'create' or args.subcommand == 'update':
        config = load_config(args.config.name, args.env)
        config['name'] = args.name
        config['env'] = args.env
        config['region'] = region
        config['profile'] = profile
        config['ec2_conn'] = ec2_conn
        config['vpc_conn'] = vpc_conn
        config['cf_conn'] = cf_conn
        config['r53_conn'] = r53_conn
        config['s3_conn'] = s3_conn
        config['get_ami_id'] = get_ami_id
        config['get_vpc_id'] = get_vpc_id
        config['get_zone_id'] = get_zone_id
        config['get_stack_output'] = get_stack_output

        if args.property:
            properties = dict(p.split("=") for p in args.property)
            invalid_properties = properties.keys() & config.keys()
            if len(invalid_properties):
                print('Reserved property names: {}'.format(','.join(invalid_properties)))
                sys.exit(1)

            config.update(properties)

        if args.subcommand == 'create':
            if not args.name.startswith(args.env):
                msg = 'Stack name does not begin with env name. Are you sure?? [y/N] '
                response = input(msg)
                if response not in YES:
                    sys.exit(0)
            create_stack(cf_conn, args.name, args.template, config, dry=args.dry_run)
        else:
            if not args.env:
                config['env'] = get_stack_tag(cf_conn, args.name, 'Env')
            create_stack(cf_conn, args.name, args.template, config, update=True, dry=args.dry_run)

    if args.subcommand == 'delete':
        delete_stack(cf_conn, args.name, region, profile)

    if args.subcommand == 'events':
        poll = True
        first = True
        ids = set()
        while poll:
            events = list_stack_events(cf_conn, args.name, region, profile)
            events_display = [(
                    event.timestamp,
                    event.resource_status,
                    event.resource_type,
                    event.logical_resource_id,
                    event.resource_status_reason)
                    for event in events if event.event_id not in ids]
            ids |= set([event.event_id for event in events])

            if first:
                events_display = events_display[:args.lines]

            if len(events_display) >= 1:
                print(tabulate(reversed(events_display), tablefmt='plain'))

            first = False
            poll = args.follow
            if poll:
                time.sleep(1)
            elif len(events_display) == 0:
                print('No events found')

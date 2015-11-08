# An attempt to support python 2.7.x
from __future__ import print_function

import sys
import signal

import boto.ec2
import boto.vpc
import boto.route53
import boto.cloudformation
import boto.s3

from stacks import cli
from stacks import aws
from stacks import cf
from stacks.config import config_load
from stacks.config import get_region_name
from stacks.config import check_profile_exists
from stacks.config import validate_properties


def main():
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, handler)

    parser, args = cli.parse_options()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if not check_profile_exists(args.profile):
        print('Profile {} does not exist.'.format(args.profile))
        sys.exit(1)

    if args.region:
        region = args.region
    else:
        region = get_region_name(args.profile)

    ec2_conn = boto.ec2.connect_to_region(region, profile_name=args.profile)
    vpc_conn = boto.vpc.connect_to_region(region, profile_name=args.profile)
    cf_conn = boto.cloudformation.connect_to_region(region, profile_name=args.profile)
    r53_conn = boto.route53.connect_to_region(region, profile_name=args.profile)
    s3_conn = boto.s3.connect_to_region(region, profile_name=args.profile)

    config_file = vars(args).get('config', None)
    env = vars(args).get('env', None)

    config = config_load(env, config_file)
    config['region'] = region
    config['ec2_conn'] = ec2_conn
    config['vpc_conn'] = vpc_conn
    config['cf_conn'] = cf_conn
    config['r53_conn'] = r53_conn
    config['s3_conn'] = s3_conn
    config['get_ami_id'] = aws.get_ami_id
    config['get_vpc_id'] = aws.get_vpc_id
    config['get_zone_id'] = aws.get_zone_id
    config['get_stack_output'] = aws.get_stack_output

    if args.subcommand == 'list':
        output = cf.list_stacks(cf_conn, args.name, args.verbose)
        if output:
            print(output)
        cf_conn.close()

    if args.subcommand == 'create' or args.subcommand == 'update':
        if args.property:
            properties = validate_properties(args.property)
            config.update(properties)

        if args.subcommand == 'create':
            cf.create_stack(cf_conn, args.name, args.template, config,
                            update=args.update, dry=args.dry_run)
        else:
            cf.create_stack(cf_conn, args.name, args.template, config,
                            update=True, dry=args.dry_run)

    if args.subcommand == 'delete':
        cf.delete_stack(cf_conn, args.name, region, args.profile)

    if args.subcommand == 'events':
        cf.get_events(cf_conn, args.name, args.follow, args.lines)


def handler(signum, frame):
    print('Signal {} received. Stopping.'.format(signum))
    sys.exit(0)

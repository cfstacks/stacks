# An attempt to support python 2.7.x
from __future__ import print_function

import signal
import sys

import boto3
import botocore.exceptions
from stacks import aws, cf, cli
from stacks.config import config_load, print_config, validate_properties


#Uncomment to get extensive AWS logging from Boto3
#boto3.set_stream_logger('botocore', level='DEBUG')

def main():
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, handler)

    parser, args = cli.parse_options()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    config_file = vars(args).get('config', None)
    config_dir = vars(args).get('config_dir', None)
    env = vars(args).get('env', None)
    config = config_load(env, config_file, config_dir)

    if args.subcommand == 'config':
        print_config(config, args.property_name, output_format=args.output_format)
        sys.exit(0)

    config['get_ami_id'] = aws.get_ami_id
    config['get_vpc_id'] = aws.get_vpc_id
    config['get_zone_id'] = aws.get_zone_id
    config['get_stack_output'] = aws.get_stack_output
    config['get_stack_resource'] = aws.get_stack_resource

    session_kwargs = {}
    if args.profile:
        session_kwargs['profile_name'] = args.profile
    if args.region:
        session_kwargs['region_name'] = args.region

    try:
        botosession = boto3.Session(**session_kwargs)
        config['region'] = botosession.region_name
        s3_conn = botosession.client('s3')
        ec2_conn = botosession.resource('ec2')
        vpc_conn = ec2_conn
        r53_conn = botosession.client('route53')
        cf_conn = botosession.client('cloudformation')
        config['ec2_conn'] = ec2_conn
        config['vpc_conn'] = vpc_conn
        config['cf_conn'] = cf_conn
        config['r53_conn'] = r53_conn
        config['s3_conn'] = s3_conn
    except botocore.exceptions.ClientError as e:
        print(e)
        sys.exit(1)

    if args.subcommand == 'resources':
        output = cf.stack_resources(cf_conn, args.name, args.logical_id)
        if output:
            print(output)
        cf_conn.close()

    if args.subcommand == 'outputs':
        output = cf.stack_outputs(cf_conn, args.name, args.output_name)
        if output:
            print(output)
        cf_conn.close()

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
                            dry=args.dry_run, follow=args.events_follow)
        else:
            cf.create_stack(cf_conn, args.name, args.template, config,
                            update=True, dry=args.dry_run,
                            follow=args.events_follow, create_on_update=args.create_on_update)

    if args.subcommand == 'delete':
        cf.delete_stack(cf_conn, args.name, botosession.region_name, botosession.profile_name, args.yes)
        if args.events_follow:
            cf.get_events(cf_conn, args.name, args.events_follow, 10)

    if args.subcommand == 'events':
        cf.get_events(cf_conn, args.name, args.events_follow, args.lines)


def handler(signum, frame):
    print('Signal {} received. Stopping.'.format(signum))
    sys.exit(0)

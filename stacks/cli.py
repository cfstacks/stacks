import os.path

import configargparse

from stacks import __about__


def parse_options():
    """Handle command-line options

    Return parser object and list of arguments
    """
    parser = configargparse.ArgumentParser()
    parser.add_argument('-p', '--profile', required=False)
    parser.add_argument('-r', '--region', required=False)
    parser.add_argument('--version', action='version', version=__about__.__version__)
    subparsers = parser.add_subparsers(title='available subcommands', dest='subcommand')

    # resources subparser
    parser_resources = subparsers.add_parser('resources', help='List stack resources')
    parser_resources.add_argument('name', help='Stack name')
    parser_resources.add_argument('logical_id', nargs='?', default=None,
                                  help='Logical resource id. Returns physical_resource_id.')

    # outputs subparser
    parser_outputs = subparsers.add_parser('outputs', help='List stack outputs')
    parser_outputs.add_argument('name', help='Stack name')
    parser_outputs.add_argument('output_name', nargs='?', default=None,
                                help='Output name. Returns output value.')

    # config subparser
    parser_config = subparsers.add_parser('config', help='Print config properties')
    # noinspection PyArgumentList
    parser_config.add_argument('-e', '--env', env_var='STACKS_ENV', required=False, default=None)
    parser_config.add_argument('-o', '--output', default='text', choices=['text', 'yaml', 'json'],
                               dest='output_format', help='Output format')
    # noinspection PyArgumentList
    parser_config.add_argument('-c', '--config', default='config.yaml',
                               env_var='STACKS_CONFIG', required=False,
                               type=_is_file)
    # noinspection PyArgumentList
    parser_config.add_argument('--config-dir', default='config.d',
                               env_var='STACKS_CONFIG_DIR', required=False,
                               type=_is_dir)
    parser_config.add_argument('property_name', nargs='?', default=None)

    # list subparser
    parser_list = subparsers.add_parser('list', help='List stacks')
    parser_list.add_argument('-v', '--verbose', action='store_true')
    parser_list.add_argument('name', default='*', nargs='?',
                             help='Stack name or unix shell-style pattern')

    # create subparser
    parser_create = subparsers.add_parser('create', help='Create a new stack')
    parser_create.add_argument('-t', '--template', required=True, type=configargparse.FileType())
    # noinspection PyArgumentList
    parser_create.add_argument('-c', '--config', default='config.yaml',
                               env_var='STACKS_CONFIG', required=False,
                               type=_is_file)
    # noinspection PyArgumentList
    parser_create.add_argument('--config-dir', default='config.d',
                               env_var='STACKS_CONFIG_DIR', required=False,
                               type=_is_dir)
    parser_create.add_argument('name', nargs='?', default=None)
    # noinspection PyArgumentList
    parser_create.add_argument('-e', '--env', env_var='STACKS_ENV', required=False, default=None)
    parser_create.add_argument('-P', '--property', required=False, action='append')
    parser_create.add_argument('-d', '--dry-run', action='store_true')
    parser_create.add_argument('-f', '--follow', dest='events_follow', help='Follow stack events', action='store_true')

    # update subparser
    parser_update = subparsers.add_parser('update', help='Update an existing stack')
    parser_update.add_argument('-t', '--template', required=True, type=configargparse.FileType())
    # noinspection PyArgumentList
    parser_update.add_argument('-c', '--config', env_var='STACKS_CONFIG',
                               default='config.yaml', required=False,
                               type=_is_file)
    # noinspection PyArgumentList
    parser_update.add_argument('--config-dir', default='config.d',
                               env_var='STACKS_CONFIG_DIR', required=False,
                               type=_is_dir)
    parser_update.add_argument('name', nargs='?', default=None)
    # noinspection PyArgumentList
    parser_update.add_argument('-e', '--env', env_var='STACKS_ENV', required=False, default=None)
    parser_update.add_argument('-P', '--property', required=False, action='append')
    parser_update.add_argument('-d', '--dry-run', action='store_true')
    parser_update.add_argument('--create', dest='create_on_update',
                               help='Create if stack does not exist.',
                               action='store_true')
    parser_update.add_argument('-f', '--follow', dest='events_follow', help='Follow stack events', action='store_true')

    # delete subparser
    parser_delete = subparsers.add_parser('delete', help='Delete an existing stack')
    parser_delete.add_argument('-f', '--follow', dest='events_follow', help='Follow stack events', action='store_true')
    parser_delete.add_argument('-y', '--yes', help='Confirm stack deletion.', action='store_true')
    parser_delete.add_argument('name')

    # events subparser
    parser_events = subparsers.add_parser('events', help='List events from a stack')
    parser_events.add_argument('name')
    parser_events.add_argument('-f', '--follow', dest='events_follow', action='store_true',
                               help='Poll for new events until stopped (overrides -n)')
    parser_events.add_argument('-n', '--lines', default=100, type=int)

    # diff subparser
    parser_create = subparsers.add_parser('diff', help='Print diff of current vs compiled template')
    parser_create.add_argument('-t', '--template', required=True, type=configargparse.FileType())
    # noinspection PyArgumentList
    parser_create.add_argument('-c', '--config', default='config.yaml',
                               env_var='STACKS_CONFIG', required=False,
                               type=_is_file)
    # noinspection PyArgumentList
    parser_create.add_argument('--config-dir', default='config.d',
                               env_var='STACKS_CONFIG_DIR', required=False,
                               type=_is_dir)
    parser_create.add_argument('name', nargs='?', default=None)
    # noinspection PyArgumentList
    parser_create.add_argument('-e', '--env', env_var='STACKS_ENV', required=False, default=None)
    parser_create.add_argument('-P', '--property', required=False, action='append')

    return parser, parser.parse_args()


def _is_file(fname):
    """Check whether fname is a file

    To be used as a type argument in add_argument()
    """
    return fname if os.path.isfile(fname) else None


def _is_dir(dirname):
    """Check whether dirname is a dir

    To be used as a type argument in add_argument()
    """
    return dirname if os.path.isdir(dirname) else None

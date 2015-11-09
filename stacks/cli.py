import os.path
import configargparse


def parse_options():
    '''Handle command-line options

    Return parser object and list of arguments
    '''
    parser = configargparse.ArgumentParser()
    parser.add_argument('-p', '--profile', env_var='AWS_DEFAULT_PROFILE', default='default')
    parser.add_argument('-r', '--region', env_var='AWS_DEFAULT_REGION', required=False)
    subparsers = parser.add_subparsers(title='available subcommands', dest='subcommand')

    parser_list = subparsers.add_parser('list', help='List stacks')
    parser_list.add_argument('-v', '--verbose', action='store_true')
    parser_list.add_argument('name', default='*', nargs='?',
                             help='stack name or unix shell-style pattern')

    parser_create = subparsers.add_parser('create', help='Create a new stack')
    parser_create.add_argument('-t', '--template', required=True, type=configargparse.FileType())
    parser_create.add_argument('-c', '--config', default='config.yaml',
                               env_var='STACKS_CONFIG', required=False,
                               type=_is_file)
    parser_create.add_argument('name', nargs='?', default=None)
    parser_create.add_argument('-e', '--env', env_var='STACKS_ENV', required=True)
    parser_create.add_argument('-P', '--property', required=False, action='append')
    parser_create.add_argument('-d', '--dry-run', action='store_true')
    parser_create.add_argument('-f', '--follow', dest='events_follow', help='Follow stack events', action='store_true')

    parser_update = subparsers.add_parser('update', help='Update an existing stack')
    parser_update.add_argument('-t', '--template', required=True, type=configargparse.FileType())
    parser_update.add_argument('-c', '--config', env_var='STACKS_CONFIG',
                               default=None, required=False,
                               type=_is_file)
    parser_update.add_argument('name', nargs='?', default=None)
    parser_update.add_argument('-e', '--env', env_var='STACKS_ENV', required=True)
    parser_update.add_argument('-P', '--property', required=False, action='append')
    parser_update.add_argument('-d', '--dry-run', action='store_true')
    parser_update.add_argument('--create', dest='create_on_update',
                               help='Create if stack does not exist.',
                               action='store_true')
    parser_update.add_argument('-f', '--follow', dest='events_follow', help='Follow stack events', action='store_true')

    parser_delete = subparsers.add_parser('delete', help='Delete an existing stack')
    parser_delete.add_argument('-f', '--follow', dest='events_follow', help='Follow stack events', action='store_true')
    parser_delete.add_argument('name')

    parser_events = subparsers.add_parser('events', help='List events from a stack')
    parser_events.add_argument('name')
    parser_events.add_argument('-f', '--follow', dest='events_follow', action='store_true',
                               help='Poll for new events until stopped.')
    parser_events.add_argument('-n', '--lines', default='10', type=int)

    return parser, parser.parse_args()


def _is_file(fname):
    '''Check whether fname is a file

    To be used as a type argument in add_argument()
    '''
    return fname if os.path.isfile(fname) else None

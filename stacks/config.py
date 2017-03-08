import json
import os
import sys

import yaml

AWS_CONFIG_FILE = os.environ.get('HOME', '') + '/.aws/credentials'
RESERVED_PROPERTIES = ['region', 'profile', 'env']


def config_load(env, config_file=None, config_dir=None):
    '''Load stack configuration files'''
    config = {}
    conf_files = list_files(config_dir)
    if config_file:
        conf_files.insert(0, config_file)
    for conf_file in conf_files:
        config.update(config_merge(env, conf_file))
    config['env'] = env
    return config


def config_merge(env, config_file=None):
    '''Merge stacks configuration file environments'''
    config = _load_yaml(config_file)
    merged_config = {}
    if config:
        merged = _merge(config, env)
        merged_config.update(merged)
    else:
        merged_config.update({})

    return merged_config


def list_files(dirname):
    '''Return a sorted list of files from dirname'''
    dirlist = os.listdir(dirname)
    ymlfiles = []
    if not dirname:
        return ymlfiles
    for filename in dirlist:
        joined = os.path.join(dirname, filename)
        if os.path.isfile(joined) and joined.endswith('.yaml'):
            ymlfiles.append(joined)
    return sorted(ymlfiles, reverse=True)


def _merge(config, env):
    '''
    Takes `config` loaded from a config file and the environment name `env`.

    If "common" and `env` are keys in `config`, return
    config['common'].update(config[env]) (i.e. the common config updated with
    environmet specific config)

    If one of env or common exists, return that config.

    Otherwise just return the whole of `config` unmodified.
    '''
    if 'common' in config and env in config:
        merged_config = config['common'].copy()
        merged_config.update(config[env])
    elif env in config.keys():
        merged_config = config[env]
    elif 'common' in config.keys():
        merged_config = config['common']
    else:
        merged_config = config
    return merged_config


def _load_yaml(fname):
    try:
        with open(fname) as filehandle:
            contents = yaml.load(filehandle)
            return contents
    # FIXME: bare excepts are bad
    except:
        return None

def validate_properties(props_arg):
    properties = dict(p.split('=') for p in props_arg)
    reserved = [i for i in RESERVED_PROPERTIES if i in properties.keys()]
    if len(reserved):
        print('Unable to override reserved properties: {}'.format(','.join(reserved)))
        sys.exit(1)
    return properties


def print_config(config, property_name=None, output_format=None):
    if property_name is not None:
        if config.get(property_name):
            if output_format == 'json':
                print(json.dumps(config[property_name], indent=2))
            elif output_format == 'yaml':
                print(yaml.dump(config[property_name]))
            else:
                print(config[property_name])
        return

    elif output_format == 'yaml':
        print(yaml.dump(config))
    elif output_format == 'json':
        print(json.dumps(config, indent=2))
    else:
        for key, value in config.items():
            print('{}={}'.format(key, value))
    return

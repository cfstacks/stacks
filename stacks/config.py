import json
import os
import sys

import boto
import yaml

AWS_CONFIG_FILE = os.environ.get('HOME', '') + '/.aws/config'
AWS_CREDENTIALS_FILE = os.environ.get('HOME', '') + '/.aws/credentials'
RESERVED_PROPERTIES = ['region', 'profile', 'env']


def config_load(env, config_file=None, config_dir=None):
    """Load stack configuration files"""
    config = {}
    conf_files = list_files(config_dir)
    if config_file:
        conf_files.insert(0, config_file)
    for f in conf_files:
        config.update(config_merge(env, f))
    config['env'] = env
    return config


def config_merge(env, config_file=None):
    """Merge stacks configuration file environments"""
    c = _load_yaml(config_file)
    config = {}
    if c:
        merged = _merge(c, env)
        config.update(merged)
    else:
        config.update({})

    return config


def list_files(dirname):
    """Return a sorted list of files from dirname"""
    lf = []
    if not dirname:
        return lf
    for f in os.listdir(dirname):
        joined = os.path.join(dirname, f)
        if os.path.isfile(joined) and joined.endswith('.yaml'):
            lf.append(joined)
    return sorted(lf, reverse=True)


def _merge(config, env):
    """
    Takes `config` loaded from a config file and the environment name `env`.

    If "common" and `env` are keys in `config`, return
    config['common'].update(config[env]) (i.e. the common config updated with
    environmet specific config)

    If one of env or common exists, return that config.

    Otherwise just return the whole of `config` unmodified.
    """
    if 'common' in config and env in config:
        c = config['common'].copy()
        c.update(config[env])
    elif env in config.keys():
        c = config[env]
    elif 'common' in config.keys():
        c = config['common']
    else:
        c = config
    return c


def _load_yaml(fname):
    try:
        with open(fname) as f:
            return yaml.full_load(f)
    except (FileNotFoundError, PermissionError, yaml.YAMLError):
        return None


def get_region_name(profile):
    """Get region name from AWS_CREDENTIALS_FILE

    Return region name
    """
    if os.path.isfile(AWS_CREDENTIALS_FILE):
        boto.config.load_credential_file(AWS_CREDENTIALS_FILE)

        if boto.config.get(profile, 'region'):
            return boto.config.get(profile, 'region')
        else:
            return None
    return None


def get_default_region_name():
    """Get default region name from AWS_CONFIG_FILE

    Return region name
    """
    if os.path.isfile(AWS_CONFIG_FILE):
        boto.config.load_credential_file(AWS_CONFIG_FILE)

        if boto.config.get('default', 'region'):
            return boto.config.get('default', 'region')
        else:
            return None
    return None


def profile_exists(profile):
    """Return True if profile exists in AWS_CREDENTIALS_FILE"""
    if os.path.isfile(AWS_CREDENTIALS_FILE):
        boto.config.load_credential_file(AWS_CREDENTIALS_FILE)
        if boto.config.get(profile, 'region'):
            return True
        else:
            return False
    return False


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
        for k, v in config.items():
            print('{}={}'.format(k, v))
    return

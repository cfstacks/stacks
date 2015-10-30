import sys
import os.path
import yaml
import botocore.config

AWS_CONFIG_FILE = os.environ.get('HOME', '') + '/.aws/credentials'
RESERVED_PROPERTIES = ['region', 'profile', 'env']


def config_load(env, config_file=None):
    '''Load stack configuration file'''
    c = _load_yaml(config_file)
    config = {}
    if c:
        merged = _merge(c, env)
        config.update(merged)
    else:
        config.update({})

    config['env'] = env
    return config


def _merge(config, env):
    if set(('common', env)) <= set(config):
        c = config['common'].copy()
        c.update(config[env])
    elif env in config.keys():
        c = config[env]
    elif 'common' in config.keys():
        c = config['common']
    return c


def _load_yaml(fname):
    try:
        with open(fname) as f:
            y = yaml.load(f)
            return y
    except:
        return None


def get_region_name(profile):
    '''Get region name from AWS_CONFIG_FILE

    Return region name
    '''
    if os.path.isfile(AWS_CONFIG_FILE):
        c = botocore.config.load_config(AWS_CONFIG_FILE)
        r = c.get(profile, {}).get('region')
        return r
    return None


def check_profile_exists(profile):
    '''Return True if profile exists in AWS_CONFIG_FILE'''
    if os.path.isfile(AWS_CONFIG_FILE):
        c = botocore.config.load_config(AWS_CONFIG_FILE)
        return True if profile in c.keys() else False
    return False


def validate_properties(props_arg):
    properties = dict(p.split('=') for p in props_arg)
    reserved = [i for i in RESERVED_PROPERTIES if i in properties.keys()]
    if len(reserved):
        print('Unable to override reserved properties: {}'.format(','.join(reserved)))
        sys.exit(1)
    return properties

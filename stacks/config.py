import sys
import os
import yaml
import botocore.config

AWS_CONFIG_FILE = os.environ.get('HOME', '') + '/.aws/credentials'
RESERVED_PROPERTIES = ['region', 'profile', 'env']


def config_load(env, config_file=None, config_dir=None):
    '''Load stack configuration files'''
    config = {}
    conf_files = list_files(config_dir)
    if config_file:
        conf_files.insert(0, config_file)
    for f in conf_files:
        config.update(config_merge(env, f))
    config['env'] = env
    return config


def config_merge(env, config_file=None):
    '''Merge stacks configuration file environments'''
    c = _load_yaml(config_file)
    config = {}
    if c:
        merged = _merge(c, env)
        config.update(merged)
    else:
        config.update({})

    return config


def list_files(dirname):
    '''Return a sorted list of files from dirname'''
    l = os.listdir(dirname)
    lf = []
    if not dirname:
        return lf
    for f in l:
        joined = os.path.join(dirname, f)
        if os.path.isfile(joined) and joined.endswith('.yaml'):
            lf.append(joined)
    return sorted(lf, reverse=True)


def _merge(config, env):
    if set(('common', env)) <= set(config):
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
        if profile == 'default':
            r = c['profiles'].get('default', {}).get('region')
        else:
            r = c.get(profile, {}).get('region')
        return r
    return None


def profile_exists(profile):
    '''Return True if profile exists in AWS_CONFIG_FILE'''
    if os.path.isfile(AWS_CONFIG_FILE):
        c = botocore.config.load_config(AWS_CONFIG_FILE)
        if profile == 'default':
            return True if 'default' in c['profiles'].keys() else False
        else:
            return True if profile in c.keys() else False
    return False


def validate_properties(props_arg):
    properties = dict(p.split('=') for p in props_arg)
    reserved = [i for i in RESERVED_PROPERTIES if i in properties.keys()]
    if len(reserved):
        print('Unable to override reserved properties: {}'.format(','.join(reserved)))
        sys.exit(1)
    return properties


def print_config(config, property_name=None):
    if property_name:
        if config.get(property_name):
            print(config[property_name])
        return

    for k, v in config.items():
        print('{}={}'.format(k, v))
    return

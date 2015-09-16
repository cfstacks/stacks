import os
import os.path
import botocore.config

from .utils import load_yaml

AWS_CONFIG_FILE = os.environ['HOME'] + '/.aws/credentials'
DEFAULT_REGION = 'us-east-1'


def merge_config(config, env):
    '''Merges config common with environment specific section'''
    c = config['common'].copy()
    c.update(config[env])
    return c


def _aws_config_file_present(file_name=AWS_CONFIG_FILE):
    '''Checks whether AWS config file is present'''
    return os.path.isfile(file_name)


def load_config(config_file, env):
    '''Loads stack configuration file'''
    with open(config_file) as f:
        c = load_yaml(f)
        if c:
            return merge_config(c, env)
        else:
            return {}


def get_region_name(profile, config_file=AWS_CONFIG_FILE):
    '''Return region name

    Use credentials file, otherwise return DEFAULT_REGION
    '''
    if 'AWS_DEFAULT_REGION' in os.environ:
        return os.environ.get('AWS_DEFAULT_REGION')
    elif _aws_config_file_present():
        c = botocore.config.load_config(config_file)
        r = c.get(profile, {}).get('region', DEFAULT_REGION)
        return r
    return DEFAULT_REGION

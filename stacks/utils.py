import yaml
import time

from fnmatch import fnmatch
from boto.exception import BotoServerError


def load_yaml(f):
    try:
        y = yaml.load(f)
        return y
    except:
        return None


# Decorator for retrying when AWS is throttling API calls
def throttling_retry(func):
    def retry_call(*args, **kwargs):
        retries = 0
        while True:
            try:
                retval = func(*args)
                return retval
            except BotoServerError as err:
                if err.code == 'Throttling' and retries <= 3:
                    sleep = 3 * (2**retries)
                    print('Being throttled. Retrying after {} seconds..'.format(sleep))
                    time.sleep(sleep)
                    retries += 1
                else:
                    raise err
    return retry_call


def match_stack_name(name, pattern):
    return fnmatch(name, pattern)

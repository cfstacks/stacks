import sys
import yaml
import json
import jinja2
import hashlib
import boto


from jinja2 import meta


def gen_template(template, config, pretty=False):
    '''Return generated CloudFormation template string'''
    tpl_str = template.read()

    env = jinja2.Environment()
    ast = env.parse(tpl_str)
    required_properties = meta.find_undeclared_variables(ast)
    missing_properties = required_properties - config.keys()

    if len(missing_properties) > 0:
        print('Requred properties not set: {}'.format(','.join(missing_properties)))
        sys.exit(1)

    tpl = jinja2.Template(tpl_str)
    out = tpl.render(config)
    yaml_out = yaml.load(out)
    indent = 2 if pretty else None
    return json.dumps(yaml_out, indent=indent)


def upload_template(conn, config, tpl, name):
    '''Uploads a template to S3 bucket and returns S3 key url'''
    bn = config.get('templates_bucket_name', '{}-stacks-{}'.format(config['env'], config['region']))

    try:
        b = config['s3_conn'].get_bucket(bn)
    except boto.exception.S3ResponseError as err:
        if err.code == 'NoSuchBucket':
            print('Bucket {} does not exist.'.format(bn))
        else:
            print(err)
        sys.exit(1)

    h = hashlib.md5(tpl.encode('utf-8')).hexdigest()
    k = boto.s3.key.Key(b)
    k.key = '{}/{}/{}'.format(config['env'], name, h)
    k.set_contents_from_string(tpl)
    url = k.generate_url(expires_in=30)
    return url

# stacks

CloudFormation stacks management tool. It can generate templates, list, create,
delete and update stacks.

## Features

- Templated YAML in jinja2
- Cross-stack resource referencing
- Multiple environments support
- Flexible common and per environment configuration

## Installation

It is written in Python and you need to have python 3.x installed. Stacks
dependencies are very minimal and can be installed via pip3 using virtualenv.

```
$ git clone https://github.com/State/stacks.git && cd stacks
$ mkvirtualenv --python=python3 stacks
$ pip install .
```

If you don't want to use virtualenv, then can just use pip3 to install stacks
from git:

```
$ sudo pip3 install git+https://github.com/State/stacks.git
```

## AWS Configuration

AWS cli tool and boto configuration lives in `${HOME}/.aws/credentials`.
Stacks tool uses AWS configuration profiles for different AWS accounts. Default
profile is `default`.

Example configuration below:

```ini
[default]
aws_access_key_id = CHANGEME
aws_secret_access_key = CHANGEME
output = json
region = us-east-1

[project-one]
aws_access_key_id = CHANGEME
aws_secret_access_key = CHANGEME
output = json
region = us-west-1

[project-two]
aws_access_key_id = CHANGEME
aws_secret_access_key = CHANGEME
output = json
region = eu-west-1
```

## Stacks Templates

Stacks uses `config.yaml` data to populate jinja2 templates. The file can have
a section per environment as well as a section called `common`.  The `common`
section gets merged into your specific environment configuration.

There are no strictly defined key names and any key you add is immediately
available to be used inside jinja2 templates. In addition, there are some
functions exposed to jinja2 templates:

- `get_ami_id()`
- `get_vpc_id()`
- `get_stack_output()`
- `get_zone_id()`

CloudFormation allows to reference resources within the same CF stack only.
Many times you would want your stacks to be decoupled, for example VPC stack
should be decoupled from instances auto scaling group stack, but in order to
launch the ASG in a particular VPC, you need to know VPCZoneIdentifier or VPC ID.

See [examples directory](examples/) for some templates.

Templating language is [jinja2](http://jinja.pocoo.org/docs/dev/templates/).

Templates do not enforce stack naming convention, but a desired convention is
to prefix stack names with env name.

CloudFormation API has a template size limit. Instead of submiting templates
over the API, we first upload them to S3 and then provide an https url. For
that to work you must have an S3 bucket created and specified in `config.yaml`,
either in `common` section or per env. Configuration key name is
`templates_bucket_name`.

## Usage

There is a help page which can be invoked on a subcommand as well: `bin/stacks create --help`.

### Examples

To list all the stacks from a profile `project-one` in us-east-1 (uses default
from the aws config if not specified):
```bash
$ bin/stacks --profile project-one --region us-east-1 list
dev-infra           CREATE_COMPLETE
dev-coreos          UPDATE_COMPLETE
<..>
```

List command takes a positional argument, which supports unix shell-style pattern
matching as well:
```bash
$ bin/stacks --region eu-west-1 list 'qa*'
qa2  CREATE_COMPLETE
qa4  UPDATE_COMPLETE
qa1  CREATE_COMPLETE
qa5  CREATE_COMPLETE
qa3  CREATE_COMPLETE
```


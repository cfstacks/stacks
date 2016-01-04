# stacks
[![Build Status](https://travis-ci.org/cfstacks/stacks.svg?branch=master)](https://travis-ci.org/cfstacks/stacks)
[![Documentation Status](https://readthedocs.org/projects/stacks/badge/?version=stable)](https://stacks.tools/en/stable/?badge=stable)

Stacks is CloudFormation management tool that allows you to define AWS
resources configuration in YAML with Jinja2 templating.

Using stacks, you create flexible and declarative templates that deploy various
AWS resources.

Use stacks to define and configure the infrastructure for your services, to
create repeatable deployments that you can reuse, to create different
deployment environments. For example, you can use stacks to deploy
production, staging, and development environments for the same service, and
take advantage of stacks's templating syntax so you can selectively roll out or
test new features.

Stacks does not make any assumptions how you should manage your infrastructure.
If you use CloudFormation JSON templates already, you can just convert them to
YAML and start using stacks and grow from there.


## Features

* Templates written in YAML
* For loops, conditionals and more with the power of Jinja2
* Cross-stack resource referencing
* Reusable snippets support
* Multiple environments
* Flexible configuration
* Stack events streaming


## [Documentation](https://stacks.tools/en/stable/#documentation)

#### Quickstarts

* [Getting Started](https://stacks.tools/en/stable/quickstarts/getting_started.html)

#### Guides

* [Step-by-Step Walkthrough](https://stacks.tools/en/stable/guides/step_by_step_walkthrough.html)


## Contribution

Please get involved in helping us improve stacks! It's very easy to get started.

Before you make a change it's best to file the bug or feature as a [github issues](https://github.com/cfstacks/stacks/issues)
so that no one else is working on a similar change.

You can use pip to install stacks in editable mode. This means changes you make to the
checkout will affect the global `stacks` command.

```
$ git clone https://github.com/cfstacks/stacks.git && cd stacks
$ mkvirtualenv --python=python3 stacks
$ pip install -e .
```

Once you've got a change please open a pull-request to master then we'll review and merge the change!

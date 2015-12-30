stacks
======
Stacks is CloudFormation management tool that allows you to define AWS
resources configuration in YAML with `Jinja2 <http://jinja.pocoo.org/docs/dev/templates/>`_
templating.

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

Features
--------

* Templates written in YAML
* For loops, conditionals and more with the power of Jinja2
* Cross-stack resource referencing
* Reusable snippets support
* Multiple environments
* Flexible configuration
* Stack events streaming


Documentation
-------------

Quickstarts
^^^^^^^^^^^

.. toctree::
   :maxdepth: 2

   quickstarts/getting_started


Guides
^^^^^^

.. toctree::
   :maxdepth: 2

   guides/step_by_step_walkthrough


Fundamentals
^^^^^^^^^^^^

.. toctree::
   :maxdepth: 2

   fundamentals/configuration
   fundamentals/templates


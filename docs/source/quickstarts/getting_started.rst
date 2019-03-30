Getting Sarted Guide
====================
Use this Getting Started Guide to get you up and running as quickly as possible
with your first deployment.

The goal of this guide is to create a given number of S3 buckets. The
quickstart assumes you're familiar with YAML syntax, comfortable with Linux
command line and have a working Python 3.x installation.

Create an AWS account
----------------------
.. warning::
  We are not responsible for any charges that may incur. However, this guide
  does not create AWS resources which are outside of free tier.

If you don't already have an AWS account, you can sign up for a free trial:

1. Go to https://aws.amazon.com/free
2. Follow the instructions to sign up for the free trial.
3. Go to IAM and create a user with ``AdministratorAccess`` policy
   attached and generate access keys.


Install stacks
--------------
There are different ways you can install stacks, but the simplest one is to
install it with pip:

.. parsed-literal::

  $ sudo pip3 install git+https://github.com/cfstacks/stacks.git@v\ |version|

Export aws access keys and default region to shell environment, replacing
``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY`` with your own keys.

.. code-block:: shell

  export AWS_ACCESS_KEY_ID=AKIAIERE3KJY2EJB8U2Q
  export AWS_SECRET_ACCESS_KEY=BAA3Vpu3X2X493WG63sVRDovoXB8lxgKi3qU9YYl
  export AWS_DEFAULT_REGION=us-east-1


Define a template
-----------------
A template describes all the resources for a single CloudFormation stack. A
template is written in YAML syntax and is made of two documents: stack metadata
document, followed by resources document.

* Metadata document defines stack-specific properties, like stack name,
  tags, rollback policy, etc.
* Resources document defines AWS resources and it is a standard CloudFormation
  template, only in YAML.

Create a template file named ``buckets.yaml``:

.. code-block:: jinja

    ---
    name: s3-buckets

    ---
    AWSTemplateFormatVersion: '2010-09-09'
    Description: S3 buckets
    Resources:
      {% for n in range(buckets_count|int) %}
      S3Bucket{{ loop.index0 }}:
        Type: AWS::S3::Bucket
        Properties:
          BucketName: {{ env }}-{{ bucket_name_prefix }}{{ loop.index0 }}-{{ region }}
      {% endfor -%}

In summary, the template describes, that ``s3-buckets`` stack contains
a number of ``AWS::S3::Bucket`` type resources. The number of buckets is
defined via ``buckets_count`` property.


Deploy your template
--------------------

Create our first stack:

.. code-block:: shell

  $ stacks create --template buckets.yaml --env dev
  Required properties not set: buckets_count,bucket_name_prefix

We get an error about missing properties. To fix that, we must specify the
missing properties. Add the ``--follow`` flag, to follow stack events:

.. code-block:: shell

    $ stacks create --template buckets.yaml --env dev --follow \
      --property bucket_name_prefix=my-awesome-bucket \
      --property buckets_count=3
    2018-09-10 18:30:08.428000+01:00  CREATE_IN_PROGRESS  AWS::CloudFormation::Stack  s3-buckets  User Initiated
    2018-09-10 18:30:10.883000+01:00  CREATE_IN_PROGRESS  AWS::S3::Bucket  S3Bucket0
    2018-09-10 18:30:10.963000+01:00  CREATE_IN_PROGRESS  AWS::S3::Bucket  S3Bucket2
    2018-09-10 18:30:10.966000+01:00  CREATE_IN_PROGRESS  AWS::S3::Bucket  S3Bucket1
    2018-09-10 18:30:11.732000+01:00  CREATE_IN_PROGRESS  AWS::S3::Bucket  S3Bucket2  Resource creation Initiated
    2018-09-10 18:30:11.837000+01:00  CREATE_IN_PROGRESS  AWS::S3::Bucket  S3Bucket0  Resource creation Initiated
    2018-09-10 18:30:11.923000+01:00  CREATE_IN_PROGRESS  AWS::S3::Bucket  S3Bucket1  Resource creation Initiated
    2018-09-10 18:30:32.608000+01:00  CREATE_COMPLETE  AWS::S3::Bucket             S3Bucket2
    2018-09-10 18:30:32.615000+01:00  CREATE_COMPLETE  AWS::S3::Bucket             S3Bucket0
    2018-09-10 18:30:32.782000+01:00  CREATE_COMPLETE  AWS::S3::Bucket             S3Bucket1
    2018-09-10 18:30:34.229000+01:00  CREATE_COMPLETE  AWS::CloudFormation::Stack  s3-buckets

Use of ``--env`` is optional, however it's a good practice to separate resources by environment.

See your new deployment
-----------------------

See the status of your new stack by running:

.. code-block:: shell

    $ stacks list
    s3-buckets  CREATE_COMPLETE

If you want to see what resources have been created by the stack, you can do that by running:

.. code-block:: shell

    $ stacks resources s3-buckets
    S3Bucket0  dev-my-awesome-bucket0-us-east-1  AWS::S3::Bucket  CREATE_COMPLETE
    S3Bucket1  dev-my-awesome-bucket1-us-east-1  AWS::S3::Bucket  CREATE_COMPLETE
    S3Bucket2  dev-my-awesome-bucket2-us-east-1  AWS::S3::Bucket  CREATE_COMPLETE


Clean up
--------
Once you are done with your deployment, make sure to delete it to avoid being
charged for resources by AWS.

To delete the deployment, run:

.. code-block:: shell

    $ stacks delete s3-buckets -y


Next steps
----------
Now that you have an idea of how stacks enhances CloudFormation, we recommend
going through :doc:`/guides/step_by_step_walkthrough` for more comprehensive
walkthrough.

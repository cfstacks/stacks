Step-by-Step Walkthrough
========================

Use this step-by-step guide as a comprehensive walkthrough of stacks. The goal
of this guide is to build a simple deployment and then gradually create a more
complex deployment using features of stacks that you will probably reuse in
your own deployments.

This guide uses a Linux command-line tool and assumes you are familiar with
YAML syntax and are comfortable running commands on a Linux command-line
window.

.. note:: If this is your first time using stacks, try the :doc:`/quickstarts/getting_started` first.

Installation and Setup
----------------------
Follow the setup steps to prepare your local environment to use stacks.

Install stacks
^^^^^^^^^^^^^^

Using pip
"""""""""

.. parsed-literal::

  $ sudo pip3 install git+https://github.com/cfstacks/stacks.git@v\ |version|


Single PEX binary
"""""""""""""""""
Alternatively, you can download a single PEX binary. Go to
https://github.com/cfstacks/stacks/releases/latest and find a pex file which
matches your OS and python version. For example, if you you're running linux
with Python 3.4:

.. parsed-literal::

  $ mkdir -p ~/bin
  $ wget -O ~/bin/stacks https://github.com/cfstacks/stacks/releases/download/v\ |version|\ /stacks-\ |version|\ -py34-linux-x86_64.pex
  $ chmod +x ~/bin/stacks


Using Docker
""""""""""""

.. code-block:: shell

  $ docker run -ti --rm quay.io/stacks/stacks


Verify that stacks is installed properly:

.. parsed-literal::

  $ stacks --version
  |version|


Configure Authentication
^^^^^^^^^^^^^^^^^^^^^^^^
Stacks supports standard AWS SDK configuration, which means you can interact
with multiple AWS accounts via profiles.

Be sure to replace access keys with your own ones.

AWS credentials file
""""""""""""""""""""
.. code-block:: shell

  $ install -d -m 0700 ~/.aws
  $ vim ~/.aws/credentials

.. code-block:: ini

  [project1]
  aws_access_key_id = AKIAIqH2jHP2BGMKPikN
  aws_secret_access_key = HFq+nQfq59yStF+qLl6/rW0AHFq+nQfq59yStF+q
  output = json
  region = us-east-1

  [project2]
  aws_access_key_id = AKIAIj2UPlaLJgMmNejS
  aws_secret_access_key = UZSYq2dzZqLzc1s+sXENnzEmUZSYq2dzZqLzc1s+
  output = json

As you can see ``project2`` profile does not have region specified, in this
case, the region will have to either be provided via ``AWS_DEFAULT_REGION``
environment variable or command line argument ``stacks --region us-west-1``.


Environment variables
"""""""""""""""""""""
.. code-block:: shell

  export AWS_ACCESS_KEY_ID="AKIAIqH2jHP2BGMKPikN"
  export AWS_SECRET_ACCESS_KEY="HFq+nQfq59yStF+qLl6/rW0AHFq+nQfq59yStF+q"
  export AWS_DEFAULT_REGION="us-east-1"

Now that you have set up your environment, you can begin constructing your
deployment.


Create a Deployment
-------------------

For this guide, let's define a set of templates that will create a new multi-AZ
VPC and an autoscaling group to launch an instance in the new VPC.

If you were working with native CloudFormation JSON templates, you would have
to define all your AWS resources for this deployment in a single JSON template,
because CloudFormation JSON templates are static - there is no way to reference
resources created by different CloudFormation templates.

Stacks aims to solve this problem, by allowing you to logically separate out
AWS resources. As your infrastructure grows, it makes sense to have your VPC
defined in a separate template from S3 buckets or RDS instances.

First of all, we need to create a local directory structure, it will help keep
all the files you create in this guide organized:

.. code-block:: shell

  $ mkdir -p step-by-step/{templates/snippets,config.d}
  $ cd step-by-step


.. _create-properties-file:

Create a properties file
^^^^^^^^^^^^^^^^^^^^^^^^
If you remember from :doc:`/quickstarts/getting_started` guide, we used command
line arguments to specify template properties. In this guide we are going to
create properties configuration file ``config.yaml``. A properties file allows
us to set key/value pairs and reference values from within templates.

.. code-block:: shell

  $ vim config.yaml

.. code-block:: yaml

  ---
  vpc_name: MyVPC
  vpc_cidr: 10.10.0.0/16
  vpc_subnets:
    - 10.10.0.0/24
    - 10.10.1.0/24
    - 10.10.2.0/24

  ami_name: CoreOS-beta-877.1.0-hvm
  instance_type: t2.micro


Define a VPC template
^^^^^^^^^^^^^^^^^^^^^
From this point, we assume that you are familiar with CloudFormation templates.
Let's jump right in and start by creating a VPC template.

.. code-block:: shell

  $ vim templates/vpc.yaml

.. code-block:: jinja

  ---
  name: {{ env }}-vpc
  disable_rollback: true
  tags:
    - key: Project
      value: step-by-step

  ---
  AWSTemplateFormatVersion: '2010-09-09'
  Description: VPC stack in {{ env }} environment
  Resources:
    VPC:
      Type: AWS::EC2::VPC
      Properties:
        CidrBlock: {{ vpc_cidr }}
        EnableDnsSupport: true
        EnableDnsHostnames: true
        Tags:
        - Key: Name
          Value: {{ vpc_name }}
        - Key: Env
          Value: {{ env }}

    DefaultSG:
      Type: AWS::EC2::SecurityGroup
      Properties:
        VpcId:
          Ref: VPC
        GroupDescription: {{ env }}-vpc Default SG
        SecurityGroupEgress:
          - IpProtocol: -1
            CidrIp: 0.0.0.0/0
            FromPort: -1
            ToPort: -1
        Tags:
          - Key: Name
            Value: {{ env }}-default
          - Key: Env
            Value: {{ env }}

    # Allow traffic within subnets
    AllTrafficSGIn:
      Type: AWS::EC2::SecurityGroupIngress
      Properties:
        GroupId:
          Ref: DefaultSG
        IpProtocol: -1
        SourceSecurityGroupId:
          Ref: DefaultSG
        FromPort: -1
        ToPort: -1

  # Create a subnet in each AZ
  {% for n in vpc_subnets %}
    Subnet{{ loop.index0 }}:
      Type: AWS::EC2::Subnet
      Properties:
        AvailabilityZone:
          Fn::Select:
            - '{{ loop.index0 }}'
            - Fn::GetAZs: ''
        VpcId:
          Ref: VPC
        CidrBlock: {{ n }}
        Tags:
        - Key: Name
          Value: {{ env }}-az{{ loop.index0 }}
        - Key: Env
          Value: {{ env }}

    SubnetRouteTableAssociation{{ loop.index0 }}:
      Type: AWS::EC2::SubnetRouteTableAssociation
      Properties:
        SubnetId:
          Ref: Subnet{{ loop.index0 }}
        RouteTableId:
          Ref: RouteTable
  {%- endfor %}

    InternetGateway:
      Type: AWS::EC2::InternetGateway
      Properties:
        Tags:
          - Key: Name
            Value: {{ env }}-igw
          - Key: Env
            Value: {{ env }}

    AttachGateway:
      Type: AWS::EC2::VPCGatewayAttachment
      Properties:
        VpcId:
          Ref: VPC
        InternetGatewayId:
          Ref: InternetGateway

    RouteTable:
      Type: AWS::EC2::RouteTable
      Properties:
        VpcId:
          Ref: VPC
        Tags:
          - Key: Name
            Value: {{ env }}-default-routetable
          - Key: Env
            Value: {{ env }}

    Route:
      Type: AWS::EC2::Route
      DependsOn: AttachGateway
      Properties:
        RouteTableId:
          Ref: RouteTable
        DestinationCidrBlock: 0.0.0.0/0
        GatewayId:
          Ref: InternetGateway

There are two YAML documents in the above template. First one is a stack metadata
document and the second one is where we define AWS resources. Both documents
can be templated using Jinja2 syntax. In fact, the metadata document says that
a stack name starts with an environment name, which makes it easy to reuse this
template for different environments.

We defined the following AWS resources in the VPC template:

* **VPC**

  ``vpc_cidr`` and ``vpc_name`` properties are being referenced from the
  properties file. Yes, we could hard-code them into the template, but by not
  doing so, we made our template more flexible.

* **DefaultSG**

  A default security group with a single rule allowing all egress traffic.

* **AllTrafficSGIn**

  Adds an ingress rule to ``DefaultSG`` to allow all traffic between instances
  with the same security group.

* **SubnetN**

  We iterate over ``vpc_subnets`` and create a subnet in each availability
  zone.

The rest should be self-explanatory.

Now that we have our VPC template defined, it's time to create another template
to define our auto scaling group.


Define an AutoScaling Group Template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

  $ vim templates/coreos-asg.yaml

.. code-block:: jinja

  ---
  name: {{ env }}-coreos-asg
  tags:
    - key: Project
      value: step-by-step

  ---
  AWSTemplateFormatVersion: '2010-09-09'
  Description: CoreOS ASG in {{ env }} environment
  Resources:
    ASG:
      Type: AWS::AutoScaling::AutoScalingGroup
      Properties:
        AvailabilityZones:
        {% for n in range(vpc_subnets|count) %}
          - Fn::Select:
            - '{{ n }}'
            - Fn::GetAZs: ''
        {% endfor -%}
        LaunchConfigurationName:
          Ref: LaunchConfiguration
        VPCZoneIdentifier:
        {% for n in range(vpc_subnets|count) %}
          - {{ get_stack_resource(cf_conn, env + '-vpc', 'Subnet' + n|string) }}
        {% endfor -%}
        TerminationPolicies:
          - 'OldestInstance'
          - 'Default'
        MaxSize: 1
        MinSize: 1
        Tags:
          - Key: Name
            Value: {{ env }}-coreos
            PropagateAtLaunch: true
          - Key: Env
            Value: {{ env }}
            PropagateAtLaunch: true
      UpdatePolicy:
        AutoScalingRollingUpdate:
          PauseTime: PT1S

    LaunchConfiguration:
      Type: AWS::AutoScaling::LaunchConfiguration
      Properties:
        AssociatePublicIpAddress: true
        ImageId: {{ get_ami_id(ec2_conn, ami_name) }}
        InstanceMonitoring: false
        InstanceType: {{ instance_type }}
        SecurityGroups:
          - {{ get_stack_resource(cf_conn, env + '-vpc', 'DefaultSG') }}


This template demonstrates the power of cross-stack referencing.

In our VPC stack we created 3 subnets, one in each availability zone. An
autoscaling group can dynamically spread instances across availability zones,
but for that to work, it needs to be given a list of availability zones and a
list of VPC subnets corresponding to each particular availability zone. Using
stacks we can simply iterate over a number of ``vpc_subnets`` and get each
subnet's physical id using ``get_stack_resource()`` helper function.

If you look at ``LaunchConfiguration`` resource definition, you notice that
instead of specifying an AMI id for the CoreOS instances, we used
``get_ami_id()`` function to get the correct AMI id, by providing just
``ami_name``, which we set in our properties file, see
:ref:`create-properties-file`.

This allows us to reuse this template in different regions, because otherwise
you would have to create some sort of AMI to region mapping, because AMIs are
region specific.

Now that we have both templates defined, let's deploy them.


Deploy templates
----------------
We are going to be deploying stacks using ``project1`` profile. If you prefer
using environment variables for configuring AWS authentication, then you
don't have to specify the profile.

Sample templates requires you to provide an environment name, for this guide, let's call
it ``learning``. Properties file is environment-aware and can have a common set
of properties as well as per-environment ones. See :doc:`/fundamentals/configuration`.

There are two ways to set an environment:

* ``STACKS_ENV`` environment variable
* ``--env`` or ``-e`` command line argument to the subcommands

Create the VPC stack:

.. code-block:: shell

  $ stacks -p project1 create -e learning -t templates/vpc.yaml -f


Wait for the VPC stack to finish creating, because we know that the coreos-asg
stack depends on the VPC and other infrastructure resources being there.

.. code-block:: shell

  $ stacks -p project1 create -e learning -t templates/coreos-asg.yaml -f


Check the status:

.. code-block:: shell

  $ stacks -p project1 list
  learning-coreos-asg  CREATE_COMPLETE
  learning-vpc         CREATE_COMPLETE


Deployment update
-----------------
After you have successfully launched your stacks, you might want to update or change the deployment
as your application evolves. Stacks allows you to change a stack by:

* Adding or removing resources to the deployment
* Updating some properties of existing resources in your stack

Remember that stacks uses CloudFormation, which uses the underlying APIs of AWS
services to manage resources. If an API doesn't support a certain action,
stacks cannot perform that action either. For example, CloudFormation can
only update an existing resource if there is an update method in the
corresponding API. Some resources have to be replaced instead.

Let's change the version CoreOS in ``config.yaml``, so that it now looks like
this:

.. code-block:: yaml
  :emphasize-lines: 9

  ---
  vpc_name: MyVPC
  vpc_cidr: 10.10.0.0/16
  vpc_subnets:
    - 10.10.0.0/24
    - 10.10.1.0/24
    - 10.10.2.0/24

  ami_name: CoreOS-alpha-899.1.0-hvm
  instance_type: t2.micro

Since ``ami_name`` is not used anywhere in VPC stack, we only need to update
the autoscaling group stack:

.. code-block:: shell

  $ stacks -p project1 update -e learning -t templates/coreos-asg.yaml

This time we didn't set ``-f`` command line flag to follow events, which means
that stacks fires an API call and exits. But luckily, there is a way to get
events from an existing stack:

.. code-block:: shell
  :emphasize-lines: 2

  $ stacks -p project1 list
  learning-coreos-asg  UPDATE_IN_PROGRESS
  learning-vpc         CREATE_COMPLETE

  $ stacks -p project1 events -f learning-coreos-asg

Wait until the update has finished, and check the status:

.. code-block:: shell

  $ stacks --profile project1 list
  learning-coreos-asg  UPDATE_COMPLETE
  learning-vpc         CREATE_COMPLETE


Clean up
--------
AWS resources incur charges, so you should delete this deployment.
Deleting this deployment takes care of deleting all the resources
created by both templates.

To delete this deployment:

.. code-block:: shell

  $ stacks -p project1 delete learning-coreos-asg -f --yes
  $ stacks -p project1 delete learning-vpc -f --yes


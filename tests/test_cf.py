import unittest

import boto
from moto import mock_cloudformation_deprecated

from stacks import cf


class TestTemplate(unittest.TestCase):

    def test_gen_valid_template(self):
        config = {'env': 'dev', 'test_tag': 'testing'}
        tpl_file = open('tests/fixtures/valid_template.yaml')
        tpl, metadata, errors = cf.gen_template(tpl_file, config)
        self.assertIsInstance(tpl, str)
        self.assertIsInstance(metadata, dict)
        self.assertEqual(len(errors), 0)

    def test_gen_invalid_template(self):
        config = {'env': 'dev', 'test_tag': 'testing'}
        tpl_file = open('tests/fixtures/invalid_template.yaml')

        with self.assertRaises(SystemExit) as err:
            cf.gen_template(tpl_file, config)
        self.assertEqual(err.exception.code, 1)

    def test_gen_template_missing_properties(self):
        config = {'env': 'unittest'}
        tpl_file = open('tests/fixtures/valid_template.yaml')

        with self.assertRaises(SystemExit) as err:
            cf.gen_template(tpl_file, config)
        self.assertEqual(err.exception.code, 1)

    def test_gen_invalid_template_with_null_value(self):
        config = {'env': 'dev', 'test_tag': 'testing'}
        tpl_file = open('tests/fixtures/invalid_template_with_null_value.yaml')
        tpl, metadata, errors = cf.gen_template(tpl_file, config)
        self.assertIsInstance(tpl, str)
        self.assertIsInstance(metadata, dict)
        self.assertEqual(len(errors), 1)


@mock_cloudformation_deprecated
class TestStackActions(unittest.TestCase):

    def setUp(self):
        self.config = {
            'env': 'unittest',
            'custom_tag': 'custom-tag-value',
            'region': 'us-east-1',
        }
        self.config['cf_conn'] = boto.cloudformation.connect_to_region(self.config['region'])
        self.config['s3_conn'] = boto.s3.connect_to_region(self.config['region'])

    def test_create_stack(self):
        stack_name = None
        with open('tests/fixtures/create_stack_template.yaml') as tpl_file:
            cf.create_stack(self.config['cf_conn'], stack_name, tpl_file, self.config)

        stack = self.config['cf_conn'].describe_stacks('unittest-infra')[0]
        self.assertEqual('unittest-infra', stack.stack_name)
        self.assertEqual(self.config['env'], stack.tags['Env'])
        self.assertEqual(self.config['custom_tag'], stack.tags['Test'])
        self.assertEqual('b08c2e9d7003f62ba8ffe5c985c50a63', stack.tags['MD5Sum'])

    def test_update_stack(self):
        stack_name = None
        with open('tests/fixtures/create_stack_template.yaml') as tpl_file:
            cf.create_stack(self.config['cf_conn'], stack_name, tpl_file,
                            self.config, update=True)
        stack = self.config['cf_conn'].describe_stacks('unittest-infra')[0]
        self.assertEqual('b08c2e9d7003f62ba8ffe5c985c50a63', stack.tags['MD5Sum'])

    def test_create_on_update(self):
        stack_name = 'create-on-update-stack'
        with open('tests/fixtures/create_stack_template.yaml') as tpl_file:
            cf.create_stack(self.config['cf_conn'], stack_name, tpl_file,
                            self.config, update=True, create_on_update=True)
        stack = self.config['cf_conn'].describe_stacks(stack_name)[0]
        self.assertEqual('b08c2e9d7003f62ba8ffe5c985c50a63', stack.tags['MD5Sum'])

    def test_create_stack_no_stack_name(self):
        stack_name = None
        with open('tests/fixtures/no_metadata_template.yaml') as tpl_file:
            with self.assertRaises(SystemExit) as err:
                cf.create_stack(self.config['cf_conn'], stack_name, tpl_file, self.config)
            self.assertEqual(err.exception.code, 1)

    def test_create_stack_no_metadata(self):
        stack_name = 'my-stack'
        with open('tests/fixtures/no_metadata_template.yaml') as tpl_file:
            cf.create_stack(self.config['cf_conn'], stack_name, tpl_file, self.config)
        stack = self.config['cf_conn'].describe_stacks('my-stack')[0]
        self.assertEqual('my-stack', stack.stack_name)
        self.assertEqual(self.config['env'], stack.tags['Env'])
        self.assertEqual('b08c2e9d7003f62ba8ffe5c985c50a63', stack.tags['MD5Sum'])


if __name__ == '__main__':
    unittest.main()

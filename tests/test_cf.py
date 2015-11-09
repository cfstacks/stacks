import unittest
import boto
from moto import mock_cloudformation

from stacks import cf


class TestTemplate(unittest.TestCase):

    def test_gen_valid_template(self):
        config = {'env': 'dev', 'test_tag': 'testing'}
        tpl_file = open('tests/fixtures/valid_template.yaml')
        tpl, options = cf.gen_template(tpl_file, config)
        self.assertIsInstance(tpl, str)
        self.assertIsInstance(options, dict)

    def test_gen_invalid_template(self):
        config = {'env': 'dev', 'test_tag': 'testing'}
        tpl_file = open('tests/fixtures/invalid_template.yaml')

        with self.assertRaises(SystemExit) as err:
            tpl, options = cf.gen_template(tpl_file, config)
        self.assertEqual(err.exception.code, 1)

    def test_gen_template_missing_properties(self):
        config = {'env': 'unittest'}
        tpl_file = open('tests/fixtures/valid_template.yaml')

        with self.assertRaises(SystemExit) as err:
            tpl, options = cf.gen_template(tpl_file, config)
        self.assertEqual(err.exception.code, 1)


class TestStackActions(unittest.TestCase):

    def setUp(self):
        self.config = {
            'env': 'unittest',
            'custom_tag': 'custom-tag-value',
            'region': 'us-east-1',
        }
        self.config['cf_conn'] = boto.cloudformation.connect_to_region(self.config['region'])
        self.config['s3_conn'] = boto.s3.connect_to_region(self.config['region'])

    @mock_cloudformation
    def test_create_stack(self):
        stack_name = None
        with open('tests/fixtures/create_stack_template.yaml') as tpl_file:
            cf.create_stack(self.config['cf_conn'], stack_name, tpl_file, self.config)

        stack = self.config['cf_conn'].describe_stacks('unittest-infra')[0]
        self.assertEqual('unittest-infra', stack.stack_name)
        self.assertEqual(self.config['env'], stack.tags['Env'])
        self.assertEqual(self.config['custom_tag'], stack.tags['Test'])
        self.assertEqual('b08c2e9d7003f62ba8ffe5c985c50a63', stack.tags['MD5Sum'])

    @mock_cloudformation
    def test_create_stack_no_stack_name(self):
        stack_name = None
        with open('tests/fixtures/no_metadata_template.yaml') as tpl_file:
            with self.assertRaises(SystemExit) as err:
                cf.create_stack(self.config['cf_conn'], stack_name, tpl_file, self.config)
            self.assertEqual(err.exception.code, 1)

    @mock_cloudformation
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

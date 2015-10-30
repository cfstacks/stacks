import unittest
import uuid

from stacks import config


class TestConfig(unittest.TestCase):
    def test_load_yaml_valid_file(self):
        y = config._load_yaml('tests/fixtures/load_yaml.yaml')
        print(y)
        self.assertIsInstance(y, dict)

    def test_load_yaml_non_existing_file(self):
        y = config._load_yaml(str(uuid.uuid1()))
        self.assertIsNone(y)

    def test_get_region_name_no_file(self):
        config.AWS_CONFIG_FILE = str(uuid.uuid1())
        region = config.get_region_name('bar')
        self.assertIsNone(region)

    def test_get_region_name_file_exists(self):
        config.AWS_CONFIG_FILE = 'tests/fixtures/aws_credentials'
        region = config.get_region_name('bar')
        self.assertEqual(region, 'eu-west-1')


if __name__ == '__main__':
    unittest.main()

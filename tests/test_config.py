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
        config.AWS_CREDENTIALS_FILE = str(uuid.uuid1())
        region = config.get_region_name('bar')
        self.assertIsNone(region)

    def test_get_region_name_file_exists(self):
        config.AWS_CREDENTIALS_FILE = 'tests/fixtures/aws_credentials'
        region = config.get_region_name('bar')
        self.assertEqual(region, 'eu-west-1')

    def test_get_region_name_default_profile(self):
        config.AWS_CREDENTIALS_FILE = 'tests/fixtures/aws_credentials'
        region = config.get_region_name('default')
        self.assertEqual(region, 'us-east-1')

    def test_get_default_region_name(self):
        config.AWS_CONFIG_FILE = 'tests/fixtures/aws_config'
        region = config.get_default_region_name()
        self.assertEqual(region, 'us-east-1')

    def test_get_default_region_name_no_file(self):
        config.AWS_CONFIG_FILE = 'tests/fixtures/aws_nonexistingconfig'
        region = config.get_default_region_name()
        self.assertIsNone(region)

    def test_config_load_no_file(self):
        cfg = config.config_load('myenv')
        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['env'], 'myenv')

    def test_config_load_with_envs(self):
        config_file = 'tests/fixtures/config_with_envs.yaml'
        cfg = config.config_load('myenv', config_file)
        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['env'], 'myenv')
        self.assertEqual(cfg['foo'], 'foo-value-in-myenv')

    def test_config_load_flat(self):
        config_file = 'tests/fixtures/config_flat.yaml'
        cfg = config.config_load('myenv', config_file)
        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['env'], 'myenv')
        self.assertEqual(cfg['foo'], 'bar')

    def test_list_files_order(self):
        config_dir = 'tests/fixtures/config.d'
        correct_order = [
            'tests/fixtures/config.d/20-config.yaml',
            'tests/fixtures/config.d/10-config.yaml',
        ]
        ls = config.list_files(config_dir)
        self.assertListEqual(ls, correct_order)

    def test_config_dir_override(self):
        config_file = 'tests/fixtures/config_flat.yaml'
        config_dir = 'tests/fixtures/config.d'
        cfg = config.config_load('myenv', config_file, config_dir)
        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['env'], 'myenv')
        self.assertEqual(cfg['foo'], 'baz')
        self.assertEqual(cfg['comes_from'], '20-config')


class TestPrintConfig(unittest.TestCase):
    def test_print_config(self):
        config_file = 'tests/fixtures/config_flat.yaml'
        cfg = config.config_load('myenv', config_file)
        self.assertIsInstance(cfg, dict)
        self.assertEqual(cfg['env'], 'myenv')
        self.assertEqual(cfg['false_boolean'], False)
        self.assertEqual(cfg['zero'], 0)


if __name__ == '__main__':
    unittest.main()

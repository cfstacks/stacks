import unittest
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

if __name__ == '__main__':
    unittest.main()

import os

from setuptools import setup, find_packages

base_dir = os.path.dirname(__file__)

about = {}
with open(os.path.join(base_dir, 'stacks', '__about__.py')) as f:
    exec(f.read(), about)

install_requires = [
    'configargparse>=0.9.3',
    'PyYAML>=4.2b1',
    'Jinja2>=2.7.3',
    'boto>=2.40.0',
    'tabulate>=0.7.5',
    'setuptools',
    'pytz',
    'tzlocal',
]

tests_require = [
    'moto',
]

config = {
    'name': 'cfstacks',
    'description': 'Manage CloudFormation sanely with templates written in YAML',
    'url': about['__url__'],
    'download_url': about['__url__'],
    'version': about['__version__'],
    'maintainer': about['__maintainer__'],
    'maintainer_email': about['__maintainer_email__'],
    'packages': find_packages(),
    'install_requires': install_requires,
    'tests_require': tests_require,
    'entry_points': {
        'console_scripts': [
            'stacks = stacks.__main__:main',
        ],
    },
    'python_requires': '>=3',
}

setup(**config)

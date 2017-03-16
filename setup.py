import os
from setuptools import setup, find_packages

base_dir = os.path.dirname(__file__)

about = {}
with open(os.path.join(base_dir, 'stacks', '__about__.py')) as f:
    exec(f.read(), about)

install_requires = [
    'configargparse>=0.9.3',
    'PyYAML>=3.11',
    'Jinja2>=2.7.3',
    'boto3',
    'tabulate>=0.7.5',
    'setuptools',
]

tests_require = [
    'moto',
]

config = {
    'name': 'stacks',
    'description': 'Stacks',
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

}

setup(**config)

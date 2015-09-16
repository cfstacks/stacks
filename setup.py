import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from setuptools import find_packages

base_dir = os.path.dirname(__file__)

about = {}
with open(os.path.join(base_dir, 'stacks', '__about__.py')) as f:
    exec(f.read(), about)


config = {
    'name': 'stacks',
    'description': 'Stacks',
    'url': about['__url__'],
    'download_url': about['__url__'],
    'version': about['__version__'],
    'packages': find_packages(),
    'install_requires': [
        'PyYAML>=3.11',
        'Jinja2>=2.7.3',
        'boto>=2.38.0',
        'botocore>=1.1.1',
        'tabulate>=0.7.5',
    ],
    'entry_points': {
        'console_scripts': [
            'stacks = stacks.__main__:main',
        ],
    },

}

setup(**config)

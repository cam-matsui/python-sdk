import os
from setuptools import setup

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'statsig', 'version.py')) as f:
    exec(f.read())  

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')) as r:
    README = r.read()

test_deps = [
    'Flask==2.0.3',
    'Werkzeug==2.0.3',
    'requests',
    'user_agents',
    'semver'
]
extras = {
    'test': test_deps,
}

setup(
    name='statsig',
    version=__version__, # type: ignore
    description='Statsig Python Server SDK',
    long_description=README,
    long_description_content_type="text/markdown",
    author='Tore Hanssen, Jiakan Wang',
    author_email='tore@statsig.com, jkw@statsig.com',
    url='https://github.com/statsig-io/python-sdk',
    license='ISC',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries'
    ],
    install_requires=[
        'requests',
        'ua_parser',
        'ip3country',
    ],
    tests_require=test_deps,
    extras_require=extras,
    include_package_data=True,
    packages=['statsig']
)

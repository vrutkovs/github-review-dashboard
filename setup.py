#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup
from pip.req import parse_requirements
from pip.download import PipSession

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

pip_session = PipSession()
parsed_reqs = parse_requirements('requirements.txt', session=pip_session)
parsed_reqs_dev = parse_requirements('requirements_dev.txt', session=pip_session)
requirements = [str(x.req) for x in parsed_reqs]
test_requirements = [str(x.req) for x in parsed_reqs_dev]

setup(
    name='github_review_dashboard',
    version='0.1.0',
    description="Github Review Dashboard is a tool to show the PRs user is involved and their status",
    long_description=readme + '\n\n' + history,
    author="Vadim Rutkovsky",
    author_email='vrutkovs@redhat.com',
    url='https://github.com/vrutkovs/github_review_dashboard',
    packages=[
        'github_review_dashboard',
    ],
    package_dir={'github_review_dashboard':
                 'github_review_dashboard'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='github_review_dashboard',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)

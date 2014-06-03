#!/usr/bin/env python

import os
from setuptools import setup
from distutils.core import setup

os.system("pandoc -o README.txt -f markdown -t rst README.md")

setup(name='charon',
      version='14.6',
      description='Database for IGN projects and samples, with RESTful interface.',
      author='Per Kraulis',
      author_email='per.kraulis@scilifelab.se',
      url='http://tools.scilifelab.se/',
      packages=['charon'],
      package_data={'charon': ['designs',
                               'static'
                               'templates',
                               'messages',
                               'example.yaml']},
      install_requires=['tornado',
                        'couchdb',
                        'pyyaml',
                        'requests'],
     )

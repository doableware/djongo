try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

LONG_DESCRIPTION = """

Use Mongodb as a backend database for your django project, without changing a
single django model!

Usage
-----

1. Install djongo::

      pip install djongo

2. Into settings.py file of your project, add::

      DATABASES = {
           'default': {
               'ENGINE': 'djongo',
               'NAME': 'your-db-name',
           }
       }

3. Run (ONLY the first time to create collections in mongoDB)::

      manage.py makemigrations
      manage.py migrate

YOUR ARE SET! HAVE FUN!

Requirements
------------

1. Djongo requires python 3.6 or above.


How it works
------------

Djongo is a SQL to mongodb query transpiler. It translates a SQL query string
into a mongoDB query document. As a result, all Django features, models etc
work as is.

Django contrib modules::

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',

and others... fully supported.

Important links
---------------

* `Full Documentation <https://nesdis.github.io/djongo/>`_
* `Source code <https://github.com/nesdis/djongo>`_
"""

setup(
    name='djongo',
    version=__import__('djongo').__version__,
    packages=['djongo', 'djongo.sql2mongo', 'djongo.models'],
    url='https://nesdis.github.io/djongo/',
    license='BSD',
    author='nesdis',
    author_email='nesdis@gmail.com',
    description=(
        'Driver for allowing Django to use MongoDB as the database backend.'),
    install_requires=[
        'sqlparse>=0.2.3',
        'pymongo>=3.2.0',
        'django>=1.8',
        'dataclasses>=0.1',
        'jsonfield>=2.0.2',
        'django-jsoneditor>=0.0.12',
    ],
    extras_require={
        'docs': [
            'django>=1.11',
            'sphinx>=1.7.2',
        ],
    },
    long_description=LONG_DESCRIPTION,
    python_requires='>=3.6',
    keywords='Django MongoDB driver connector',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.6',
    ]
)

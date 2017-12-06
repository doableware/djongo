from distutils.core import setup

LONG_DESCRIPTION = """

Use Mongodb as a backend database for your django project, without changing a single django model!

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

Djongo is a SQL to mongodb query transpiler. It translates a SQL query string into a mongoDB query document. As a result, all Django features, models etc work as is.

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
    version='1.2.10',
    packages=['djongo'],
    url='https://nesdis.github.io/djongo/',
    license='BSD',
    author='nesdis',
    author_email='nesdis@gmail.com',
    description='Driver for allowing Django to use MongoDB as the database backend.',
    install_requires=[
        'sqlparse>=0.2.3',
        'pymongo>=3.2.0',
        'django>=1.8'
    ],
	long_description=LONG_DESCRIPTION,
    python_requires='>=3.6'
)

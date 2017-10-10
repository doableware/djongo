from distutils.core import setup

LONG_DESCRIPTION = """
djongo
Driver for allowing Django to use MongoDB as the database backend.

Use Mongodb as a backend database for your django project, without changing a single django model!!!

Usage:

pip install djongo 
Into settings.py file of your project, add: 

DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'your-db-name',
    }
}

    Run manage.py migrate(ONLY the first time to create collections in mongoDB) 
    YOUR ARE SET! HAVE FUN! 

Requirements:

  1. djongo requires python 3.5 or above.


How it works:
djongo is a SQL to mongodb query compiler. It translates a SQL query string into a mongoDB query document. As a result, all Django features, models etc work as is.
  
  Django contrib modules: 
 
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',

 and others... fully supported.
 
 Full Documentation: 'https://nesdis.github.io/djongo/'
"""
setup(
    name='djongo',
    version='1.2.4',
    packages=['djongo'],
    url='https://nesdis.github.io/djongo/',
    license='BSD',
    author='nesdis',
    author_email='nesdis@gmail.com',
    description='Driver for allowing Django to use NoSQL databases',
    install_requires=[
        'sqlparse>=0.2.3',
        'pymongo>=3.2.0',
        'django>=1.8'
    ],
	long_description=LONG_DESCRIPTION,
    python_requires='>=3.5'
)

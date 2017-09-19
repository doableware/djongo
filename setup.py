from distutils.core import setup

setup(
    name='djongo',
    version='1.2.3',
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
    python_requires='>=3.5'
)

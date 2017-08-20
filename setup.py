from distutils.core import setup

setup(
    name='djongo',
    version='1.2.2',
    packages=['djongo'],
    url='https://github.com/nesdis/djongo',
    license='BSD',
    author='nesdis',
    author_email='nesdis@gmail.com',
    description='Driver for allowing Django to use NoSQL databases',
	install_requires=[
          'sqlparse>=0.2.3',
		  'pymongo>=3.2.0'
      ],
	 python_requires='>=3.3'
)

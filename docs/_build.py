
import os
import shutil
import subprocess
import djongo

BASE = os.path.dirname(os.path.abspath(__file__))
API = os.path.join(BASE, 'api')
SOURCE = os.path.join(BASE, '_apidocs')
doctrees = os.path.join(SOURCE, 'doctrees')
djongo = os.path.dirname(os.path.abspath(djongo.__file__))

subprocess.run(f'sphinx-apidoc -o {SOURCE} {djongo}', check=True)
os.remove(os.path.join(SOURCE, 'modules.rst'))
shutil.rmtree(API, ignore_errors=True)
subprocess.run(f'sphinx-build -b dirhtml -d {doctrees} {SOURCE} {API}', check=True)
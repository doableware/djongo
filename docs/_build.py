
import os
import shutil
import subprocess
import djongo

BASE = os.path.dirname(os.path.abspath(__file__))
API = os.path.join(BASE, 'api')
SOURCE = os.path.join(BASE, '_apidocs')
doctrees = os.path.join(SOURCE, 'doctrees')
djongo_dir = os.path.dirname(os.path.abspath(djongo.__file__))

if __name__ == '__main__':
    print(f'Building docs from package at: {djongo_dir}')
    subprocess.run(f'sphinx-apidoc -o {SOURCE} {djongo_dir}', check=True)
    os.remove(os.path.join(SOURCE, 'modules.rst'))
    shutil.rmtree(API, ignore_errors=True)
    shutil.rmtree(doctrees, ignore_errors=True)

    subprocess.run(f'sphinx-build -a -b dirhtml -d {doctrees} {SOURCE} {API}', check=True)
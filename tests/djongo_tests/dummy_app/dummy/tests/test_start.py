import os
import shutil

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
l = os.listdir(base)
if 'migrations' in l:
    mig = os.path.join(base, 'migrations')
    print('Removed migrations')
    shutil.rmtree(mig)


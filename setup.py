import os
import re
from setuptools import setup

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = f.read()
f.close()

f = open(os.path.join(os.path.dirname(__file__), 'asynmsg', 'asynmsg.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(f.read()).group(1)
f.close()

setup(
	name='asynmsg',
	version=VERSION,
    description='A library help to build tcp server/client application',
    long_description=readme,
    author='Sun Jin',
    author_email='sunjinopensource@qq.com',
    url='https://github.com/sunjinopensource/asynmsg/',
	packages=['asynmsg'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
)

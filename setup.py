import os
import re
from setuptools import setup


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = f.read()
f.close()


setup(
	name='asynmsg',
	version=__import__('asynmsg').__version__,
    description='A library help to build tcp server/client application',
    long_description=readme,
    author='Sun Jin',
    author_email='sunjinopensource@qq.com',
    url='https://github.com/sunjinopensource/asynmsg/',
	py_modules=['asynmsg'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)

#!/usr/bin/env python

import distutils.core


distutils.core.setup(
    name="ffv",
    version="0.1",
    url="https://github.com/andreyp/ffv",
    author="Andrey Petrov",
    author_email="andrey@ubuntarium.ru",
    description="yet another form validator",
    long_description=open('README.rst', 'r').read(),
    py_modules=['ffv'],
    platforms="any",
)

from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize("cython_print_test.pyx")
)
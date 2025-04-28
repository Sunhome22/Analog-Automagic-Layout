from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension
setup(name='a_star', ext_modules=cythonize([Extension(name='a_star', sources=['a_star.pyx'])]))

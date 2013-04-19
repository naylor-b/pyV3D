import sys
import os

from setuptools import setup, Extension
from Cython.Distutils import build_ext

try:
    import numpy
    numpy_include = os.path.join(os.path.dirname(numpy.__file__),
                                 'core', 'include')
except ImportError:
    print 'numpy was not found.  Aborting build'
    sys.exit(-1)

module1 = Extension('_pyV3D',
                    include_dirs=[numpy_include],
                    sources=["src/pyV3D/_pyV3D.pyx"])


kwds = {'name': 'pyV3D',
        'version': '0.1',
        'install_requires':['numpy', 'tornado', 'argparse'],
        'cmdclass': {'build_ext': build_ext},
        'ext_modules': [module1],
        'author': '',
        'author_email': '',
        'classifiers': ['Intended Audience :: Science/Research',
                        'Topic :: Scientific/Engineering'],
        'description': 'Python webGL based web viewer',
        'download_url': '',
        'include_package_data': True,
        'keywords': ['openmdao'],
        'license': 'Apache License, Version 2.0',
        'maintainer': 'Kenneth T. Moore',
        'maintainer_email': 'kenneth.t.moore-1@nasa.gov',
        'package_data': {
               'pyV3D': ['test/*.py', 'test/*.csm', 'test/*.col']
        },
        'package_dir': {'': 'src'},
        'packages': ['pyV3D'],
        'url': 'https://github.com/OpenMDAO/pyV3D',
        'zip_safe': False,
       }

setup(**kwds)


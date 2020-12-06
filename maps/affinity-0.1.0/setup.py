# Enfold Enterprise Server
# Copyright(C), 2004-5, Enfold Systems, LLC - ALL RIGHTS RESERVED

# Enfold Systems, LLC
# 4617 Montrose Blvd., Suite C215
# Houston, Texas 77006 USA
# p. +1 713.942.2377 | f. +1 832.201.8856
# www.enfoldsystems.com
# info@enfoldsystems.com
"""affinity - control processor affinity on windows and linux

'affinity' provides a simple api for setting the processor affinity by
wrapping the specific underlying function calls of each
platform. works on windows (requires pywin32) and linux (kernel 2.6 or
patched 2.4).
"""

classifiers = """\
Development Status :: 3 - Alpha
Environment :: Other Environment
License :: OSI Approved :: Python Software Foundation License
Operating System :: Microsoft :: Windows
Operating System :: POSIX :: Linux
Programming Language :: Python
Topic :: System :: Hardware :: Symmetric Multi-processing
"""

import sys
from setuptools import setup, find_packages
from distutils.core import Extension

doclines = __doc__.splitlines()

VERSION = '0.1.0'

ext = []
if sys.platform in ('linux2','linux',):
    ext.append(
        Extension(name='affinity._affinity',
                  sources=['affinity/_affinity.c'])
        )

setup(
    name='affinity',
    version=VERSION,
    author="Sidnei da Silva",
    author_email="sidnei@enfoldsystems.com",
    keywords="process affinity linux windows scheduler",
    url="http://cheeseshop.python.org/pypi/affinity",
    download_url="http://cheeseshop.python.org/packages/source/a/affinity/affinity-%s.tar.gz" % VERSION,
    description=doclines[0],
    classifiers=filter(None, classifiers.split("\n")),
    long_description="\n".join(doclines[2:]),
    packages=find_packages(),
    ext_modules=ext,
    )

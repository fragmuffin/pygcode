import codecs
import os
import re

from setuptools import setup, find_packages


###################################################################

NAME = "attrs"
PACKAGES = find_packages(where="src")
META_PATH = os.path.join("src", "attr", "__init__.py")
KEYWORDS = ["class", "attribute", "boilerplate"]
CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
INSTALL_REQUIRES = []

###################################################################

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()


META_FILE = read(META_PATH)


def find_meta(meta):
    """
    Extract __*meta*__ from META_FILE.
    """
    meta_match = re.search(
        r"^(?P<name>__{meta}__)\s*=\s*['\"](?P<value>[^'\"]*)['\"]".format(meta=meta),
        META_FILE, re.M
    )
    if meta_match:
        return meta_match.group('value')
    raise RuntimeError("Unable to find __{meta}__ string.".format(meta=meta))


if __name__ == "__main__":
    setup(
        name=NAME,
        description=find_meta("description"),
        license=find_meta("license"),
        url=find_meta("uri"),
        version=find_meta("version"),
        author=find_meta("author"),
        author_email=find_meta("email"),
        maintainer=find_meta("author"),
        maintainer_email=find_meta("email"),
        keywords=KEYWORDS,
        long_description=read("README.rst"),
        packages=PACKAGES,
        package_dir={"": "src"},
        zip_safe=False,
        classifiers=CLASSIFIERS,
        install_requires=INSTALL_REQUIRES,
    )

#VERSION = '0.1.dev'  # *.dev = release candidate
#
#setup(
#  name = 'pygcode',
#  packages = ['pygcode'],
#  version = VERSION,
#  description = 'basic g-code parser, interpreter, and writer library',
#  author = 'Peter Boin',
#  author_email = 'peter.boin@gmail.com',
#  url = 'https://github.com/fragmuffin/pygcode',
#  download_url = 'https://github.com/fragmuffin/pygcode/archive/%s.tar.gz' % VERSION,
#  keywords = ['gcode', 'cnc', 'parser', 'interpreter'],
#  classifiers = [],
#)

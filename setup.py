import codecs
import os
import re

from setuptools import setup, find_packages


# Setup template thanks to: Hynek Schlawack
#   https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
###################################################################

NAME = "pygcode"
PACKAGES = find_packages(where="src")
META_PATH = os.path.join("src", NAME, "__init__.py")
KEYWORDS = ['gcode', 'cnc', 'parser', 'interpreter']
CLASSIFIERS = [
    "Development Status :: 2 - Pre-Alpha",  # see src/pygcode/__init__.py
    "Intended Audience :: Developers",
    "Intended Audience :: Manufacturing",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering",
]
INSTALL_REQUIRES = [
    'euclid3',  # 2D and 3D vector, matrix, quaternion and geometry module.
    'six',  # Python 2 and 3 compatibility utilities
]

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
        r"^(?P<name>__{meta}__)\s*=\s*['\"](?P<value>[^'\"]*)['\"](\s*#.*)?$".format(meta=meta),
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
        url=find_meta("url"),
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

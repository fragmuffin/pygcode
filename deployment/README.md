# Notes on deployment

How I deployed this package (mainly just notes for myself)

Method based on the articles:

  * http://peterdowns.com/posts/first-time-with-pypi.html and
  * https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/


## PyPi deployment

### Pre-requisites

```
pip install -U "pip>=1.4" "setuptools>=0.9" "wheel>=0.21" twine
```

### PyPi rc

`cat ~/.pypirc`

```
[distutils]
index-servers =
  prod
  test

[prod]
repository = https://upload.pypi.org/legacy/
username=FraggaMuffin
password=secret

[test]
repository=https://test.pypi.org/legacy/
username=FraggaMuffin
password=secret
```

`chmod 600 ~/.pypirc`


### Building

```
rm -rf build/
python setup.py sdist bdist_wheel
```

#### Test Build (sdist)

**Python 2.x**

```
rmvirtualenv 27-test
mkvirtualenv 27-test

$WORKON_HOME/27-test/bin/pip install dist/pygcode-0.1.0.tar.gz

$WORKON_HOME/27-test/bin/python

>>> import pygcode
>>> pygcode.Line('g1 x2 y3 m3 s1000 f100').block.gcodes  # or whatever
```

**Python 3.x**

```
rmvirtualenv 35-test
mkvirtualenv -p $(which python3) 35-test

$WORKON_HOME/35-test/bin/pip install dist/pygcode-0.1.0.tar.gz

$WORKON_HOME/35-test/bin/python

>>> import pygcode
>>> pygcode.Line('g1 x2 y3 m3 s1000 f100').block.gcodes  # or whatever
```

#### Test Build (wheel)

similar to above, but the `pip` call references `pygcode-0.1.0-py2.py3-none-any.whl` instead

make sure to `rmvirtualenv` to ensure `pygcode` is uninstalled from virtual environment


### Upload to PyPi Test server

`twine upload -r test dist/pygcode-0.1.0*`

Then another round of testing, where `pip` call is:

`$WORKON_HOME/<envname>/bin/pip install -i https://testpypi.python.org/pypi pygcode`


### Upload to PyPy server

all good!? sweet :+1: time to upload to 'production'

`twine upload -r prod dist/pygcode-0.1.0*`

and final tests with simply:

`$WORKON_HOME/<envname>/bin/pip install pygcode`

## Deployment in Git

after merging to `master`

```
git tag 0.1.0 -m "Initial version"
git push --tags origin master
```

tadaaaaaa!

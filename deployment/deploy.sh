#!/usr/bin/env bash
source $(which virtualenvwrapper.sh)

function pyver() {
    # write python version to stdout
    $1 -c 'import sys; print("{}.{}.{}".format(*sys.version_info))'
}

function lib_ver() {
    # Get library vesion number
    pushd ../src > /dev/null
    python -c 'import pygcode; print(pygcode.__version__)'
    popd > /dev/null
}

# ============ Local Parameters
LIB_NAME=pygcode
LIB_VER=$(lib_ver)

# ============ Help Text
function show_help() {
    [ "$@" ] && echo "$@"
cat << EOF
Usage: ./${0##*/} {build|test|and so on ...}

This script is to maintain a consistent method of deployment and testing.

Deployment target: ${LIB_NAME} ${LIB_VER}

Arguments:
    Setup:
        setup:      Installs packages & sets up environment (requires sudo)

    Compiling:
        build:      Execute setup to build packages (populates ../dist/)
                    creates both 'sdist' and 'wheel' distrobutions.

    Virtual Environments:
        rmenv py#       Remove virtual environment
        remkenv py#     Remove, then create re-create virtual environment

    Deploy:
        deploy test     Upload to PyPi test server
        deploy prod     Upload to PyPi (official)

    Install:
        install sdist py#       Install from local sdist
        install wheel py#       Install from local wheel
        install pypitest py#    Install from PyPi test server
        install pypi py#        Install from PyPi (official)

    Testing:
        test dev py#        Run tests on local dev in a virtual env
        test installed py#  Run tests on installed library in virtual env

    Help:
        -h | --help     display this help message

    py#: when referenced above means
        'py2' for Python $(pyver python2)
        'py3' for Python $(pyver python3)
EOF
}

# ============ Commands
function setup() {
    # Install pre-requisite tooling
    sudo pip install -U "pip>=1.4" "setuptools>=0.9" "wheel>=0.21" twine
}

function build() {
    # Run setup.py to build sdist and wheel distrobutions
    pushd ..
    rm -rf build/
    python setup.py sdist bdist_wheel
    popd
}

function rmenv() {
    # Remove virtual environment
    set_venv_variables $1
    rmvirtualenv ${env_name}
}

function remkenv() {
    # Remove virtual environment, then re-create it from scratch
    set_venv_variables $1
    rmvirtualenv ${env_name}
    mkvirtualenv --python=${python_bin} ${env_name}
}

function deploy() {
    # Deploy compiled distributions to the test|prod server
    _deployment_env=$1
    pushd ..
    twine upload -r ${_deployment_env} dist/${LIB_NAME}-${LIB_VER}*
    popd
}

function install() {
    # Install library from a variety of sources
    _install_type=$1
    _env_key=$2

    set_venv_variables ${_env_key}
    workon ${env_name}

    case "${_install_type}" in
        sdist)
            # Install from locally compiled 'sdist' file
            ${env_pip_bin} install ../dist/${LIB_NAME}-${LIB_VER}.tar.gz
            ;;
        wheel)
            # Install from locally compiled 'wheel' file
            ${env_pip_bin} install ../dist/${LIB_NAME}-${LIB_VER}-py2.py3-none-any.whl
            ;;
        pypitest)
            # Install from PyPi test server
            ${env_pip_bin} install -i https://testpypi.python.org/pypi ${LIB_NAME}
            ;;
        pypi)
            # Install from official PyPi server
            ${env_pip_bin} install ${LIB_NAME}
            ;;
        *)
            echo invalid install type: \"${_install_type}\" >&2
            exit 1
            ;;
    esac

    deactivate
}

function test() {
    # Run tests

    _test_scope=$1
    _env_key=$2

    set_venv_variables ${_env_key}

    case "${_test_scope}" in
        dev)
            export PYGCODE_TESTSCOPE=local
            ;;
        installed)
            export PYGCODE_TESTSCOPE=installed
            ;;
        *)
            echo invalid test scope: \"${_test_scope}\" >&2
            exit 1
            ;;
    esac

    pushd ../tests
    workon ${env_name}
    ${env_python_bin} -m unittest discover -s . -p 'test_*.py' --verbose
    deactivate
    popd
}

# ============ Utilities
function set_venv_variables() {
    # on successful exit, environment variables are set:
    #   env_name        = virtual environment's name
    #   env_pip_bin     = environment's pip binary
    #   env_python_bin  = environment's python binary
    #   python_bin      = python binary in host environment
    _env_key=$1

    env_name=${LIB_NAME}_${_env_key}
    env_pip_bin=${WORKON_HOME}/${env_name}/bin/pip
    env_python_bin=${WORKON_HOME}/${env_name}/bin/python
    case "${_env_key}" in
        py2)
            python_bin=$(which python2)
            ;;
        py3)
            python_bin=$(which python3)
            ;;
        *)
            echo invalid environment key: \"${_env_key}\" >&2
            exit 1
            ;;
    esac
}

# ============ Option parsing
case "$1" in
    # Show help on request
    -h|--help)
        show_help
        exit 0
        ;;

    # Valid Commands
    setup) setup ;;
    build) build ;;
    rmenv) rmenv $2 ;;
    remkenv) remkenv $2 ;;
    deploy) deploy $2 ;;
    install) install $2 $3 ;;
    test) test $2 $3 ;;

    # otherwise... show help
    *)
        show_help >&2
        exit 1
        ;;
esac

echo ./${0##*/} completed successfully

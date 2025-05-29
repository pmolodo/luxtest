# no hashbang - should be sourced!

set -e
set -u

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# need to run find_hython.py - need python for that, so create / use
# the uv-managed venv
LUXTEST_HYTHON="$("${THIS_DIR}/luxtest_python.sh" "${THIS_DIR}/find_hython.py")"

export LUXTEST_VENV_NAME=.venv_houdini

. "${THIS_DIR}/uv_install.sh"


# Could use, ie, `hython -c "import sys; print(sys.version_info[:3])"``...
# ...but `hython -c` is VERY slow to startup (while `hython --version` is speedy)
hython_ver_str="$("${LUXTEST_HYTHON}" --version)"

if [[ "${hython_ver_str}" =~ (([0-9]+\.[0-9]+)\.[0-9]) ]]; then
    export LUXTEST_HYTHON_VER_3="${BASH_REMATCH[1]}"
    export LUXTEST_HYTHON_VER_2="${BASH_REMATCH[2]}"
else
    echo "Failed to determine hython python version: '$hython_ver_str'"
    exit 201
fi

# Try to see if uv recognizes this python version (first trying
# 3-part version, ie, 3.10.10, then 2-part, ie, 3.10)
uv_python_ver=""
for test_ver in "${LUXTEST_HYTHON_VER_3}" "${LUXTEST_HYTHON_VER_2}"; do
    if [ -n "$("${LUXTEST_UV_PATH}" python list "${test_ver}")" ]; then
        uv_python_ver="${test_ver}"
        break
    fi
done
if [ -z "$uv_python_ver" ]; then
    echo "uv did not recognize houdini python version: '${LUXTEST_HYTHON_VER_2}'"
    exit 202
fi

# Initially wanted to use "uv venv --python $LUXTEST_HYTHON", but uv errors when
# trying to query for interpreter info, due to an error with "import setuptools",
# resulting in it considering LUXTEST_HYTHON an invalid interpreter
#    Tested with: Houdini 20.5.445, 20.0.653

# So, instead, we setup a venv for a "compatible" python version interpreter,
# using uv_python_ver

if ! [ -f "${LUXTEST_VENV_ACTIVATE}" ]; then
    if [ -d "${UV_PROJECT_ENVIRONMENT}" ]; then
        # if the venv dir exists, but the activate script doesn't, assume it's a failed / incomplete venv
        rm -rf "${UV_PROJECT_ENVIRONMENT}"
    fi
    "${LUXTEST_UV_PATH}" --quiet venv --python "${uv_python_ver}" "${LUXTEST_VENV_NAME}"
fi

"${LUXTEST_UV_PATH}" --quiet sync

# can't rely on the "activate" script since we didn't use $LUXTEST_HYTHON when setting up our "venv"

# ...so add to PATH/PYTHONPATH manually

if [[ "${LUXTEST_OS_TYPE}" == "windows" ]]; then
    export LUXTEST_VENV_PYLIB_SUBDIR="Lib"
else
    export LUXTEST_VENV_PYLIB_SUBDIR="lib/python${LUXTEST_HYTHON_VER_2}"
fi
export LUXTEST_VENV_SITE_PACKAGES_DIR="${UV_PROJECT_ENVIRONMENT}/${LUXTEST_VENV_PYLIB_SUBDIR}/site-packages"

varname_to_native_path LUXTEST_VENV_BIN_DIR
varname_to_native_path LUXTEST_VENV_SITE_PACKAGES_DIR

export PATH="${LUXTEST_VENV_BIN_DIR}${PATH:+:${PATH}}"
export PYTHONPATH="${LUXTEST_VENV_SITE_PACKAGES_DIR}${PYTHONPATH:+${PATHSEP}${PYTHONPATH}}"

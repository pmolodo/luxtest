 #!/bin/bash

set -e
set -u

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export LUXTEST_VENV_NAME=.venv

. "${THIS_DIR}/uv_install.sh"

if ! [ -f "${LUXTEST_VENV_ACTIVATE}" ]; then
    "${LUXTEST_UV_PATH}" --quiet venv --managed-python "${LUXTEST_VENV_NAME}"
fi

. "${LUXTEST_VENV_ACTIVATE}" &> /dev/null

"${LUXTEST_UV_PATH}" --quiet sync

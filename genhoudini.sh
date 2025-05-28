#!/bin/bash

set -e
set -u

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${THIS_DIR}/luxtest_hython.sh" "${THIS_DIR}/genhoudini.py" "$@"
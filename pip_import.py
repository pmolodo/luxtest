import importlib
import inspect
import os
import subprocess
import sys

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

DEPS_DIR = os.path.join(THIS_DIR, ".deps")
PY_DEPS_DIR = os.path.join(DEPS_DIR, f"python{sys.version_info[0]}.{sys.version_info[1]}")

###############################################################################
# Functions
###############################################################################


def pip_import(module_name, pip_package_name=None):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        pass

    # couldn't import - first, ensure PY_DEPS_DIR is on path, and retry
    os.makedirs(PY_DEPS_DIR, exist_ok=True)
    if PY_DEPS_DIR not in sys.path:
        sys.path.insert(0, PY_DEPS_DIR)
        try:
            return importlib.import_module(module_name)
        except ImportError:
            pass

    # still couldn't import - install via pip
    if pip_package_name is None:
        pip_package_name = module_name
    os.makedirs(PY_DEPS_DIR, exist_ok=True)

    pip_install(pip_package_name)
    print("=" * 80)

    return importlib.import_module(module_name)


def pip_install(pip_package_name: str):
    # ensurepip not necessary, houdini's python install includes it... and it was erroring
    # subprocess.check_call([sys.executable, "-m", "ensurepip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", PY_DEPS_DIR, pip_package_name])

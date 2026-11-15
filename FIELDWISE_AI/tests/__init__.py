"""Test package.

Every test run uses a throw-away SQLite file, so tests never touch the real
``data/kairo.db`` with saved plans.
"""

import atexit
import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="kairo-test-db-")
os.environ["KAIRO_DB_PATH"] = os.path.join(_TMP, "test.db")
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)

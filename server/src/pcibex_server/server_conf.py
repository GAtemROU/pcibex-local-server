# This software is licensed under a BSD license; see the LICENSE file for details.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


_SOURCE_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if (_SOURCE_PROJECT_ROOT / "ibex").is_dir():
    _DEFAULT_DATA_ROOT = _SOURCE_PROJECT_ROOT / "ibex"
else:
    _DEFAULT_DATA_ROOT = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    ) / "pcibex" / "ibex"


def _configured_path(name, default, base=_DEFAULT_DATA_ROOT):
    configured = os.environ.get(name)
    value = Path(configured).expanduser() if configured else Path(default).expanduser()
    if not value.is_absolute():
        value = base / value
    return str(value.resolve())


DATA_ROOT = _configured_path("PCIBEX_DATA_DIR", _DEFAULT_DATA_ROOT)
IBEX_WORKING_DIR = _configured_path("IBEX_WORKING_DIR", DATA_ROOT, Path(DATA_ROOT))

# Options are "toy" or "cgi" (case-sensitive); the value "paste"
# is equivalent to "toy" and is supported for backwards compatibility.
#
# If "toy", the server will run in stand-alone mode.
# If "cgi", the server will run as a CGI process.
#
# Note that the value of this variable can be overridden by the
# "-m" command line option.
SERVER_MODE = "toy"

# The name of the directory where result files will be stored.
# The directory will automatically be created if it doesn't exist
# (but if it is itself contained within a non-existent directory,
# this won't happen).
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
RESULT_FILES_DIR = "results"

# The name of the file where results will be stored (within
# the RESULT_FILES_DIR directory).
RESULT_FILE_NAME = "results"
# The name of the file where raw results will be stored (within
# the RESULT_FILES_DIR directory).
RAW_RESULT_FILE_NAME = "raw_results"
# The name of the directory where server state will be stored.
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
SERVER_STATE_DIR = "server_state"

# Should each set of results be preceeded by a header in the results file? (The
# headers gives some info about the results, e.g. the browser used).
INCLUDE_HEADERS_IN_RESULTS_FILE = True
# Should the server insert comments in the results file documenting the values
# in each column?
INCLUDE_COMMENTS_IN_RESULTS_FILE = True
# Only applicable if 'INCLUDE_COMMENTS_IN_RESULTS_FILE' is set to True.
# If the following is set to True, the server uses a simple line-by-line
# commenting system instead of the somewhat fallible system that was the only
# option prior to 0.3-beta15.
SIMPLE_RESULTS_FILE_COMMENTS = False

# The name of the directory where Javascript includes are stored.
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
JS_INCLUDES_DIR = "js_includes"
# The name of the directory where CSS includes are stored.
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
CSS_INCLUDES_DIR = "css_includes"
# The name of the directory where data files are stored.
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
DATA_INCLUDES_DIR = "data_includes"
# The name of the directory where html chunks are stored.
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
CHUNK_INCLUDES_DIR = "chunk_includes"
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
OTHER_INCLUDES_DIR = "other_includes"

# The name of the directory where various caches are kept.
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
CACHE_DIR = "cache"

# Define this variable to set the directory containing static
# HTML/JavaScript files (e.g. 'experiment.html').
# ***** Applicable only when server mode is "toy". *****
# ***** Relative to IBEX_WORKING_DIR unless absolute path. *****
STATIC_FILES_DIR = "www"

# These variables specify which of the files in the js_includes,
# data_includes and css_includes directories should actually be included.
# The value of each variable should be a list whose first element
# is either the string "block" or the string "allow". The remainder
# of the list gives the filenames of those js/css files which should
# be allowed/blocked.
JS_INCLUDES_LIST   = ["block"]  # Block nothing (i.e. allow everything).
CSS_INCLUDES_LIST  = ["block"]  # Ditto.
DATA_INCLUDES_LIST = ["block"]  # Ditto.

# If this is set to True, JavaScript files are "minified" before being
# served up. This saves on bandwidth, but makes it much harder to
# debug JavaScript errors.
MINIFY_JS = False

# **********
# Most users should ignore the following options and skip to those
# in the rest of the file. See documentation. Note that if one
# of these options is defined, all must be defined.
# **********

# EXTERNAL_CONFIG_URL = "http:///foo.net:9854/conf" # "file:///foo/bar/conf"
# EXTERNAL_CONFIG_PASS_PARAMS = True
# EXTERNAL_CONFIG_METHOD = "GET" # 'POST' is currently not implemented.

PORT = int(os.environ.get("PORT") or "3001")
PRIVATE_DIRECTORY = _configured_path(
    "PRIVATE_DIRECTORY",
    Path(DATA_ROOT) / "results",
    Path(DATA_ROOT),
)
PUBLIC_DIRECTORY = _configured_path("PUBLIC_DIRECTORY", DATA_ROOT, Path(DATA_ROOT))
SOURCE_ZIP_DIRECTORY = _configured_path(
    "SOURCE_ZIP_DIRECTORY",
    Path(DATA_ROOT) / "source",
    Path(DATA_ROOT),
)
BASE_APPLICATION_URL = (
    os.environ.get("BASE_APPLICATION_URL") or "http://localhost:4200"
).rstrip("/")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
MONGO_DB = os.environ.get("MONGO_DB")
CORS_ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "",
    ).split(",")
    if origin.strip()
)
APP_ROLES = ['ADMIN', 'USER', 'STUDENT']
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$'
FULLNAME_REGEX = r"^(?:(?:\p{L}[\p{L}\p{M}']*)(?:[-'\s])?)+$"
EXPERIMENT_NAME_REGEX = r"^[a-zA-Z0-9_-]+$"
ALLOWED_DOMAINS = ["coli.uni-saarland.de","lsv.uni-saarland.de","uni-saarland.de","lst.uni-saarland.de"]
JWT_EXPIRATION=1
JWT_ALGORITHM="HS256"
EXPECTED_FOLDERS = [
    'chunk_includes',
    'css_includes',
    'data_includes',
    'js_includes'
]


"""
Provides the ability to replace any func's return value
with a fixture if we're in a development environment.
"""

from os.path import join
from functools import wraps
from tf_utils import env
from queue import conn# TODO this name is stupid now. it's not queueing-related.



def fixtureable(db, f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if env('HOSTNAME') == 'localhost:5000':
            fn = join(env('FIXTURE_ROOT'), db, args[0])
            with open(fn, 'r') as fh:
                return fh.read()
        return f(*args, **kwargs)
    return decorated

def dump_fixtures_redis_get(prefix):
    for key in conn.keys():
        if key.startswith(prefix):
            fn = join(env('FIXTURE_ROOT'), 'redis', key)
            with open(fn, 'w') as fh:
                fh.write(conn.get(key))

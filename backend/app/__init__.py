"""
Compatibility shim.

Some modules/CI import `backend.app.*`, but the real package lives at
`backend.backend.app.*`. This forwards `backend.app` to the real package.
"""
from importlib import import_module as _import_module

_real = _import_module("backend.backend.app")

# Make `backend.app` behave like the real package so `backend.app.settings`, etc. work.
__path__ = _real.__path__
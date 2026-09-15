"""Bridge to the native _pymium_native extension inside the Pymium renderer.

Outside a renderer the bridge is absent; every browser object then operates on
its local mirror, which is exactly how the standalone test suite works.
"""


class PyumiumNotEmbedded(RuntimeError):
    pass


_native = None


def install_native(native_module):
    global _native
    _native = native_module


def enabled():
    return _native is not None


def native():
    if _native is None:
        raise PyumiumNotEmbedded(
            "this pymium object is running outside a Pymium renderer; "
            "open the page with out/pymium/chrome instead"
        )
    return _native
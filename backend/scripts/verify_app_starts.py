"""
Import the FastAPI app exactly as the server does, and fail loudly if it cannot.

This exists because a single route annotation took production down.

    @router.delete("/csv/mappings/{id}", status_code=204)
    async def delete_mapping(...) -> None:

is fine on its own, but the module also had "from __future__ import
annotations". Under PEP 563 the return annotation becomes the string "None",
FastAPI resolves route return annotations to infer a response model, and the
result was

    AssertionError: Status code 204 must not have a response body

raised at IMPORT time. The container crash-looped and every endpoint 502'd —
a total outage from a change that passed compileall, passed tsc, and passed
41 unit checks, none of which ever import the app.

Run before every push:

    cd backend && python scripts/verify_app_starts.py

Third-party modules missing from a dev machine are stubbed so this can run
anywhere; the point is to exercise OUR import graph and FastAPI's route
registration, which is where this class of failure lives.
"""
import os
import sys
import types
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Stubs for deps that may not be installed locally. Each mimics only the shape
# main.py touches at import time.
_STUBS = {
    "slowapi": {
        "Limiter": type("Limiter", (), {
            "__init__": lambda self, **kwargs: None,
            "limit": lambda self, *a, **k: (lambda fn: fn),
        }),
    },
    "slowapi.util": {"get_remote_address": lambda *a, **k: ""},
    "slowapi.errors": {"RateLimitExceeded": type("RateLimitExceeded", (Exception,), {})},
}


def _install_stubs() -> list[str]:
    stubbed: list[str] = []
    for name, attributes in _STUBS.items():
        try:
            __import__(name)
            continue
        except ImportError:
            module = types.ModuleType(name)
            for key, value in attributes.items():
                setattr(module, key, value)
            sys.modules[name] = module
            stubbed.append(name)
    return stubbed


def main() -> int:
    stubbed = _install_stubs()
    if stubbed:
        print(f"stubbed locally-missing deps: {', '.join(stubbed)}")

    try:
        import main as app_module
    except Exception:
        print("FAIL — the app does not import. This would 502 in production.\n")
        traceback.print_exc()
        return 1

    app = app_module.app
    routes = [r for r in app.routes if hasattr(r, "methods")]
    print(f"PASS — app imports, {len(routes)} routes registered")

    csv_routes = sorted(
        (sorted(r.methods)[0], r.path) for r in routes if "csv" in r.path
    )
    print("\nCSV routes:")
    for method, path in csv_routes:
        print(f"  {method:6} {path}")

    expected = {
        "/api/connections/csv/analyze",
        "/api/connections/csv/commit",
        "/api/connections/csv/mappings",
        "/api/connections/csv-upload",
        "/api/connections/csv-parse",
        "/api/connections/csv-templates",
    }
    present = {path for _, path in csv_routes}
    missing = expected - present
    if missing:
        print(f"\nFAIL — expected routes missing: {sorted(missing)}")
        return 1

    # The specific trap: a no-content route that declares a response body.
    offenders = [
        r.path for r in routes
        if getattr(r, "status_code", None) in (204, 304)
        and getattr(r, "response_field", None) is not None
    ]
    if offenders:
        print(f"\nFAIL — no-content routes declaring a response body: {offenders}")
        return 1

    print("\nPASS — no 204/304 route declares a response body")
    return 0


if __name__ == "__main__":
    sys.exit(main())

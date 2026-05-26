"""DraftMyVan runtime-side consumer of the manifest contract.

This package is the **reference consumer** of a DraftMyVan module
manifest. It is deliberately separate from `tools/` — the tools
directory contains *gates* (schema validator, GLB validator) that run
before code is committed; this package is what something downstream
(an editor importer, a build script, a runtime) would call to **read**
a validated manifest into typed in-memory data.

Boundary:
    * Schema validation is upstream's responsibility
      (`tools/validate_manifest.py`). The runtime consumer assumes the
      manifest already passed that gate.
    * Asset existence / dimensional correctness is the Blender gate's
      responsibility (`tools/blender/validate_glb_against_manifest.py`).
      The runtime consumer reports asset presence but does not re-verify
      bounding boxes.
    * Missing required fields still raise a clear `ConsumerError` —
      defence in depth at the call site, since a malformed manifest
      should never reach a runtime in the first place.

Why this exists:
    Six PRs in, every consumer of the manifest has been a validator.
    This package proves the manifest is consumable by something **other
    than** a validator — i.e. that the contract works as a contract.
    A Unity / UE5 / Flutter importer in a different language would
    implement the same shape.
"""

# Re-export the data types and the error class. The loader function is
# reached via `runtime.load_module.load_module(...)`; re-exporting it
# here would shadow the submodule name and break the `python -m
# runtime.load_module <manifest>` CLI. All names come from
# `runtime.module` so this package import does not pre-load the loader
# submodule (which would also trigger a runpy warning under `-m`).
from .module import ConsumerError, Dimensions, Module  # noqa: F401

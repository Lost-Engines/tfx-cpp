# Reconstruction and verification

Reference: TFX 2.05, September 1994 CD. Native offsets refer to `TFX.DAT`, SHA-256 `2cc41a39fa95a2c9fd883c4220d7bdd9cca00c543c89b019eb270763f59d1d9a`.

## Working boundaries

* `DID.DAT` index, native filename substitution/hash, raw and RA v2 resources load directly from the selected installation.
* All 3,488 reference archive entries compare byte for byte against did-unpack (2,416 RA-compressed and 1,072 raw); malformed input is tested without game data.
* All 1,012 model programs decode directly from the archive. The C++ VM matches the checked inspection interpreter in 2,042 detail/state cases (253,334 vertices). This establishes program interpretation, not native camera/raster equivalence.
* All 703 valid SSD definitions match their decoded initial parts, anchored draw calls and parameter streams. All 1,240,000 cells in the 31 valid configured grids match their tile IDs and deterministic inspection variant choices. Actor initialiser random side effects are not yet simulated.
* Original x86 calls independently verify 1,332 condition predicates, 205 component matrices and 64 world random updates. All 1,024 regenerated sine samples match the executable, including the -32766 negative peak.
* No CD audio, campaign execution or flight simulation is implemented yet.

## Verification approach

Each subsystem needs evidence from the original code: controlled calls with declared memory/inputs, output and side-effect capture, then the same cases through C++. Preserve timing, random seeds and external callback results for sequence tests. Integer results should match exactly; numerical tolerances for x87-derived calculations require explicit justification and checks of resulting branches/state transitions.

Use isolated native calls first, subsystem sequences next, and instrumented DOSBox traces for behaviour requiring complete mission context. Research-viewer approximations are inspection aids, not proof of native gameplay behaviour.

The developer probe streams decoded resources to the reference checker over a pipe. Nothing is extracted into the installation or copied into the repository.

## Reproducing the analytical checks

```sh
python3 tools/check_native.py --build build --data-dir /path/to/TFX
python3 tools/check_shapes.py --build build --research ../tfx-reverse
python3 tools/check_world.py --build build --research ../tfx-reverse
```

`check_native.py` needs Unicorn and the original reference executable. It executes bounded original routines in isolated x86 memory with controlled stack/register/global inputs; DOS, game startup and installation files are not modified. The shape/world comparisons additionally need the research tree and Node.js, and explicitly distinguish inspection comparisons from native execution.

# Original flight-recording format

The retail 2.05 Alt+V recorder stores model submissions rather than rendered
pixels or simulation inputs. Original C5AC0 opens the file, C5BEC appends a
frame, C5B3C closes it and patches its header, and C5DAC writes the resource
dictionary. C5FF0 reads a frame and C6178 remaps model handles for playback.
These are executable file offsets in the September 1994 reference.

The standalone codec is implemented in `src/recording/file.*`. Live capture,
recording controls and the original post-flight replay interface are being
connected separately; the codec comparisons do not establish that integration.

All numeric fields use little-endian byte order. The ten-byte file header is:

| Field | Type | Meaning |
| --- | --- | --- |
| Frame count | u16 | Number of complete recorded frames |
| File length | u32 | Final file size, patched on close |
| Dictionary offset | u32 | End of frame data/start of the resource dictionary |

Each frame contains the following fields, in this order. Arrays are stored
by field, rather than as interleaved model structures. `N` is limited to the
original 348 model slots.

| Field | Stored form |
| --- | --- |
| Reserved state | Eight bytes copied from DATA AC9C; no retail producer identified |
| View angles | Three u16 words from CODE 47C20/22/24 |
| Model count | u16 |
| Queue priorities | N signed words |
| Queue payload slots | N u16 words |
| Drawing path | N bytes: 40 unrotated, 44 rotated, 48 ground shadow |
| Initial shape state | N bytes, compressed with fill byte 0 |
| Colour-remap row | N bytes |
| Retained scale | N bytes, compressed with fill byte 1 |
| Resource handles | N u16 words |
| Model Euler angles | Three arrays of N words; each compressed with fill byte 0 |
| Camera-space model origins | Three arrays of N signed dwords |
| Animation parameters | Eight bytes per slot, compressed with fill byte 0 |

C5958 compresses a field as pairs of one-byte fill-run and literal-run lengths,
followed by the literal bytes. Each run stops at 255. A trailing fill-only run
still writes its zero literal count. Each compressed field starts with its
u16 encoded byte count; an empty field writes a zero length. Both original
codec directions use a 2 KiB temporary buffer. The C++ reader bounds every run
and field, and rejects overlong, truncated or inconsistent files.

The dictionary stores a u16 entry count, that many original u16 handles, a u32
total name-byte count, then NUL-terminated names for entries 2 onwards. The
original reader allocates room for 1,000 entries. Entries 0 and 1 have no stored
name; playback supplies `badshape.3` for entry 1. Handle lookup searches the
table backwards. Resource names and handles are distinct from archive hashes
or the SSINFO model-name index.

`tools/check_recording.py` hosts only DOS file operations in memory. It executes
the original writer, compressor, dictionary builder, length patching and
decompressor. Forty-eight complete files/96 frames agree byte for byte,
including empty/full queues, signed priorities, all three model paths,
255-byte run boundaries, sparse animation parameters, all retained scale
values, and dictionaries of up to 1,000 entries. The original frame reader
also restores every supplied queue field. No original installation is written.

```sh
python3 tools/check_recording.py --research ../tfx-reverse --build build
ctest --test-dir build --output-on-failure -R '^recording\.'
```

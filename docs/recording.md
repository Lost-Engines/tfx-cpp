# Original flight-recording format

The retail 2.05 Alt+V recorder stores model submissions rather than rendered
pixels or simulation inputs. Original C5AC0 opens the file, C5BEC appends a
frame, C5B3C closes it and patches its header, and C5DAC writes the resource
dictionary. C5FF0 reads a frame and C6178 remaps model handles for playback.
These are executable file offsets in the September 1994 reference.

The standalone codec is implemented in `src/recording/file.*`. Alt+V now starts
and stops live capture to `video.rec` in the selected installation directory.
`recording::recorder` streams each frame and retains only its bounded resource
dictionary. Starting again replaces the previous recording, as in the original.
The post-flight replay interface is being connected separately.

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

## Live capture and the designator's two world passes

`tools/check_recording_session.py` runs the actual original recorder and actual
C++ window loop. DOS file operations are hosted in capture-owned memory; host
input is supplied only at the declared device/timer boundary. The native and
C++ resource managers allocate independently, so saved handles are resolved to
model names before comparing the recorded frames. Every other recorded field,
including unsorted priority/slot order and retained constructor metadata, is
compared directly.

A 12-frame mission-501 run records eight complete scene queues while changing
camera and weapon selection. A 16-frame mission-601 run records eleven queues
across designator entry, zoom, designation and clearing. All saved fields and
all rendered pixels agree. A further 22-frame Realistic designator sequence
retains exact state/pixel agreement after the integration. Independent queue
comparisons still cover 512 sequences/180,751 allocations/149,241 draws, and
32 mixed constructor/delivery sequences cover another 11,872 submissions.

The recording comparison exposed a caller-order detail that the earlier
single-pass designator integration missed. Native 0x92144 leaves the installed
camera unchanged for viewport 19. The ordinary world pass draws and records
with that inherited camera, then the 0x92C24 callback installs the new gimbal
and paints a second world. This is not simply a previous recorded frame:
current actor/effect state still participates in the first pass. Sky, ordinary
transients, precipitation and seeker updates belong to that primary pass;
the secondary designator pass retains the original animation gate. The host
now follows both passes and retains the last installed world camera, including
MFD camera submissions.

The native recording marker uses its own fixed eight-column/six-row driver
font at CODE 509E5; substituting presentation font 2 or the proportional HUD
font produces different pixels. The marker is loaded from the original
executable and paints its original shadow and ink.

The streaming writer closes cleanly at 65,535 frames instead of allowing the
original word counter to wrap into an unplayable zero-frame file. I/O errors
are reported without aborting flight. These are explicit host protections.

```sh
python3 tools/check_recording_session.py --research ../tfx-reverse --build build
```

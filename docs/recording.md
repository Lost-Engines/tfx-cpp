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
After a completed mission, the original WNN/press-room introduction precedes
automatic playback. Any new key press leaves the recorded flight.

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

## Streaming playback and the post-flight wrapper

`recording::playback` reads the resource dictionary once and decodes one frame
at a time through a bounded buffer. It validates the file length, dictionary,
compressed fields and end of the frame stream. Resource names are normalised
to model basenames, as by native C93BC. Asset-free tests cover actual file
creation, full queues, successive frames, replacement, RAII finalisation,
missing directories and malformed/truncated streams.

Native 7B2F4 first plays `anim/wwn.256` and `anim/prtv2.256`, each once with a
40-retrace fade-in and a one-BIOS-tick frame delay. These introductions do not
poll keyboard input. It then restores the full-screen 3D viewport, uploads the
environment's infrared palette, clears pending make codes and reads the film.
Recorded frames run at four PIT ticks each (about 13.65 frames/second), with
the shadowed PLAY caption alternating each frame. Its driver font has eight
drawn columns and a nine-pixel advance, unlike the presentation fonts.

The recording stores view angles and camera-space model submissions, but not
camera height, scrolling ground phase, drawing seed, status/detail flags or
carried-model bindings. Original playback inherits these from the flight.
The live viewer accordingly retains the actual flight scene, renderer and
attachments; it runs no mission rules, aircraft AI or flight dynamics during
replay. Immediate scratch submissions are not recorded by the original and
are not invented during playback.

`tools/check_recording_playback.py` executes the original file reader, resource
remapping, horizon, queue flush and blinking caption in a retained original
flight context. Eight ordinary-camera and eleven designator-camera frames,
plus their infrared palettes, agree pixel for pixel. Animation prefaces,
display flips and real-time waiting are explicit boundaries of that pixel
comparison. The separate native animation codec/clock/fade comparisons cover
their implementation. A private-window campaign check uses normal controls to
record and complete Hop 1, observes both introductions and replay, then checks
debriefing and Hop 2's inherited campaign and flight state.

```sh
python3 tools/check_recording_playback.py --case camera
python3 tools/check_recording_playback.py --case designator
python3 tools/check_training_engagement.py --campaign --recording
```

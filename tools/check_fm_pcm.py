#!/usr/bin/env python3
"""Preserve reference FM PCM through the DBOPL offset/arithmetic cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args()
sys.path.insert(0,str(a.research/'did-unpack'))
from did_unpack import Archive
installation=a.research/'installs/cd_1994_09/TFX'
archive=Archive.read(installation/'DID.DAT')
entries={entry.identifier:entry for entry in archive.entries}
fixtures=json.loads((Path(__file__).resolve().parent.parent/'tests/reference/fm_pcm.json').read_text())['resources']
with tempfile.TemporaryDirectory(prefix='tfx-fm-pcm-') as temporary:
 root=Path(temporary)
 for row in fixtures:
  source=archive.unpack(entries[int(row['id'],16)])
  assert hashlib.sha256(source).hexdigest()==row['source_sha256'],('source',row['id'])
  (root/'source.osl').write_bytes(source)
  result=subprocess.run([str((a.build/'music_render').resolve()),str(installation/'START.EXE'),str(root/'source.osl'),str(root/'pcm'),'.','adl','256','include'],text=True,capture_output=True,check=True)
  trace=json.loads(result.stdout.removeprefix('TFX_RENDER '))
  assert trace['frames']==row['frames'] and trace['state_trace_fnv64']==row['state_trace_fnv64'],('trace',row['id'])
  assert hashlib.sha256((root/'pcm').read_bytes()).hexdigest()==row['pcm_sha256'],('PCM',row['id'])
print(f"{len(fixtures)} real FM resources retain bit-identical pre-cleanup PCM and sequencer traces")

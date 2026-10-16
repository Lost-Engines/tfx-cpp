#!/usr/bin/env python3
"""Compare executable-backed fonts with complete native VGA rendering.

Glyphs and short strings execute the original character renderer, width and
line-spacing routines. Every pixel and written-black coverage bit is compared.
Unsupported original glyph pointers are excluded using the external research
inventory, never replaced with another font. Text formatting/reveal timing are
separate consumers. Layout consumes the native low-word width, not stale upper
register bits left by some original helpers.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();executable=args.research/'installs/cd_1994_09/TFX/TFX.DAT';capture=json.loads((args.research/'analysis/presentations/fonts.json').read_text());native=NativeReference(executable);cpu=native.cpu;cpu.mem_map(0x300000,0x10000);native.write(0x1ad04,'<I',0x300000)
video=VgaCapture(native)
widths={0:0xd2e50,3:0xd27dc,4:0xd2a44,5:0xd295c,6:0xd2afc,7:0xd2c14,8:0xd2cd8,9:0xd2d94}
rows=[];cases=[];glyphs=strings=0
for font in capture['fonts']:
    style=font['style'];available={g['code'] for g in font['glyphs'] if 'pixels' in g};texts=[bytes([code]) for code in sorted(available)]
    glyphs+=len(texts)
    extra=[b'TFX 2.05',b'INDIGO',b'AIA I AM',b'abcdef',b'       ',b'HI I I',b'GUNS 123']
    extra=[text for text in extra if all(code in available for code in text)];strings+=len(extra)
    cases_here=[(text,20,20) for text in texts+extra]
    if style==1:
        cases_here.extend((text,20+phase,20) for text in extra for phase in (1,2,3));strings+=len(extra)*3
    if style not in (1,2):
        clipped=[(b'TFX 2.05',x,y) for x,y in ((-2,-2),(-2,197),(317,-2),(317,197))];cases_here.extend(clipped);strings+=len(clipped)
    cases_here.append((b'',20,20));strings+=1
    for index,(text,x,y) in enumerate(cases_here):
        colour=0 if index%11==0 else 127
        cpu.mem_write(0x300008,bytes([style]));height=native.call(0xb12e4);cpu.mem_write(0x300100,text+bytes(1))
        width=native.call(widths[style],eax=0x300100)&65535 if style in widths else len(text)*(8 if style==1 else 6)
        video.reset()
        native.call(0xb19c8,eax=x,edx=y,ebx=colour,ecx=0x300100,limit=500000)
        pixels=video.pixels();mask=video.coverage()
        rows.append(f'{style} {x} {y} {colour} {text.hex() or '-'}\n');cases.append((style,text,struct.pack('<2I',width,height)+pixels+mask))
result=subprocess.run([str(args.build/'font_probe'),str(executable)],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr.decode()
at=0;failures=[]
for style,text,expected in cases:
    actual=bytearray(result.stdout[at:at+len(expected)]);actual[:4]=struct.pack('<I',struct.unpack_from('<I',actual)[0]&65535)
    if actual!=expected:failures.append((style,text,next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None),actual[:8].hex(),expected[:8].hex()))
    at+=len(expected)
assert at==len(result.stdout)
assert not failures,(len(failures),failures[:16])
print(glyphs,'native glyphs and',strings,'complete strings match in ink, written coverage, width and line height across all ten fonts')

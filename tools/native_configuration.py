"""Read effective settings through the original configuration-file reader."""
from pathlib import Path
from native_reference import NativeReference,r


def read_configuration(directory):
    directory=Path(directory)
    source=directory/'TFX.CFG'
    if not source.exists():source=directory/'tfx.cfg'
    content=source.read_bytes() if source.exists() else b''
    image=NativeReference(directory/'TFX.DAT');image.call(0xde851);image.call(0xde547)
    image.intercept(0xc9c24,'Supply configuration file length',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,len(content)),im.return_from()))
    image.intercept(0xc9d4c,'Supply configuration file content',lambda im:(im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EDX),content),im.return_from()))
    for address in (0xc4f0c,0xa5ce0,0xa6424,0xa6458,0xa629c):image.intercept(address,'DOS audio-device and resistance-calibration setup is outside the requested portable settings',lambda im:im.return_from())
    image.call(0xa664c,limit=300000)
    return {name:image.read(offset,kind)[0] for name,offset,kind in (
        ('hud_green',0xa4ec,'<H'),('control',0x13478,'<B'),('model',0x1347a,'<B'),('detail',0x8864,'<B'),
    )}

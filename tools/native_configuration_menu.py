"""Controlled original configuration dialogs; only host/device boundaries supplied."""
import struct
from native_reference import NativeReference, r
from native_vga import VgaCapture


def menu_image(path, values, page=0, audio=None, *, image_type=NativeReference, interactive=False):
    image = image_type(path, data_base=0x100000)
    image.call(0xde851)
    image.call(0xde547)
    vga = VgaCapture(image)
    image.cpu.mem_map(0x300000,0x30000)
    image.write(0x24176,'<H',240)
    image.write(0x240f4,'<I',image.data+0xf988)
    image.write(0xad84,'<B',1)
    fields=[(0x1347a,'<B'),(0x13478,'<B'),(0x8864,'<B'),(0xac68,'<I'),(0xa4ec,'<H')]+[(f,'<B') for f in (0x5954,0x8f31,0x8e22,0x8e23,0x8e25,0x8f30,0x8867)]
    for (offset,fmt),value in zip(fields,values): image.write(offset,fmt,value)
    image.write(0x8865,'<b',-1)
    image.write(0x8866,'<b',-1)
    if audio is not None:
        available_sound,available_music,sound,music=audio
        image.write(0x8865,'<b',sound if available_sound else -1)
        image.write(0x8866,'<b',music if available_music else -1)
    image.write(0x13aed,'<B',values[1])
    if not interactive:
        image.intercept(0xd07b4,'Supply no new keyboard/mouse event between declared option selections',lambda im:im.return_from())
    image.intercept(0xce4b0,'Hide hardware cursor outside captured dialog pixels',lambda im:im.return_from())
    image.intercept(0xce4c0,'Restore hardware cursor outside captured dialog pixels',lambda im:im.return_from())
    image.intercept(0xca566,'Keep the supplied VGA capture page selected instead of switching physical video pages',lambda im:im.return_from())
    image.intercept(0xc9240,'Supply available capture heap size',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x200000),im.return_from()))
    image.intercept(0xc91a0,'Supply capture allocation for backing up the window area',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
    start,stop=(0x93f7c,0x94020) if page==2 else (0x9407c,0x942ef) if page==1 else (0x94448,0x947fc)
    image.cpu.mem_write(image.STACK,struct.pack('<I',image.RETURN))
    image.cpu.reg_write(r.UC_X86_REG_ESP,image.STACK)
    try: image.cpu.emu_start(image.native(start),image.native(stop),count=3000000)
    except Exception as error:
        raise RuntimeError(f"dialog construction failed at file {image.cpu.reg_read(r.UC_X86_REG_EIP)-0x10000+0x70aa4:#x}") from error
    assert image.cpu.reg_read(r.UC_X86_REG_EIP)==image.native(stop)
    pointers=[]
    root=image.read(0x2416c,'<I')[0]
    pointer=struct.unpack('<I',image.cpu.mem_read(root+32,4))[0]
    while pointer:
        pointers.append(pointer)
        assert len(pointers)<=32
        pointer=struct.unpack('<I',image.cpu.mem_read(pointer,4))[0]
    return image,vga,pointers

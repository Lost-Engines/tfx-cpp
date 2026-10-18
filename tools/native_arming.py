#!/usr/bin/env python3
"""Original arming UI with supplied DOS I/O and optional complete 3D previews.

The default capture isolates widgets. previews=True loads and executes the real
SSD/shape renderer with the original DPMI divide-exception recovery installed.
"""
import struct
from unicorn import x86_const as r
from native_planner import NativePlanner
from native_dpmi import DpmiReference
from native_reference import NativeReference


class NativeArming(NativePlanner):
    def __init__(self,data_dir,research,*,previews=False):
        super().__init__(data_dir,research,aperture=0xa0000,image_type=DpmiReference if previews else NativeReference)
        self.position=(100,75)
        self.movement=(0,0)
        self.buttons=0
        self.events=[]
        self.palettes=[]
        p=self;im=self.image;cpu=self.cpu
        for address in (0x74614,0x8c43c,0x74508,0x7dde4,0xa4dfc,0xa4edc,0xa6068):im.intercept(address,'Host input, timer and output notifications outside this fixed arming UI capture.',lambda im:im.return_from())
        im.intercept(0xb52d4,'Observe SSD event notifications; preview objects are hosted only in the widget-only capture.',lambda im:(self.events.append((cpu.reg_read(r.UC_X86_REG_EAX),cpu.reg_read(r.UC_X86_REG_EDX))),None if previews else im.return_from()))
        im.intercept(0x744e4,'Supply no DOS mouse driver during original player initialization.',lambda im:(cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
        handles={}

        def model(im):
         address=cpu.reg_read(r.UC_X86_REG_EAX)
         name=p.text(address) if address else '<unset player>'
         if name not in handles:handles[name]=len(handles)+1
         cpu.reg_write(r.UC_X86_REG_EAX,handles[name]);im.return_from()
        for address in (() if previews else (0xb4d98,0xc93bc)):im.intercept(address,'Supply stable model handles; 3D preview drawing is excluded from this widget-only capture.',model)
        for address in (() if previews else (0xb4ff0,0xb6ea4,0xc488d,0xc48e1)):im.intercept(address,'3D preview placement/rendering is outside this widget-only capture.',lambda im:im.return_from())
        def mouse(im):
         for offset,value in ((4,self.position[0]),(8,self.position[1]),(12,self.buttons)):
          pointer,=struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+offset,4));cpu.mem_write(pointer,struct.pack('<H',value))
         im.return_from()
        im.intercept(0xc72ff,'Supply selected absolute mouse coordinates and buttons.',mouse)
        im.intercept(0xb47b9,'Report original fatal diagnostics without entering DOS exit.',lambda im:(_ for _ in ()).throw(RuntimeError(p.text(cpu.reg_read(r.UC_X86_REG_EAX)))))
        def bitmap(im):
         name=p.text(cpu.reg_read(r.UC_X86_REG_EAX));raw=p.read('iff/raw/'+name);assert len(raw)==64772
         for plane,out in enumerate(p.video.page(p.video.get(0x55907))):out[:]=raw[772+plane::4]
         cpu.mem_write(im.data+0x20ce0,raw[4:772]);cpu.mem_write(im.data+0x21000,raw[4:772]);cpu.reg_write(r.UC_X86_REG_EAX,1);im.return_from()
        im.intercept(0xc6f64,'Supply independently decoded external screen artwork at the original image-driver boundary.',bitmap)
        def palette(im):
            pointer,=struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+4,4))
            self.palettes.append(bytes(cpu.mem_read(pointer,768)))
        im.intercept(0xde454,'Observe native hardware palette transfers without replacing their output.',palette)
        im.call(0xde547) # Original Watcom startup installs the floating printf handlers.
        if previews:
            im.write(0x1b234,'<I',0x7f0200)
            for address in (0xb41e4,0xb43b4):
                im.intercept(address,'Keyboard input is supplied through the capture-owned transport instead of DOS IRQ installation.',lambda im:im.return_from())
            im.call(0xde851)
            im.call(0xde81e)
            configuration=b'CONTROL=0\r\nMODEL=0\r\nSOUNDFX=0\r\nMUSIC=0\r\n'
            im.intercept(0xc9c24,'Supply the length of the explicit silent capture configuration.',lambda im:(cpu.reg_write(r.UC_X86_REG_EAX,len(configuration)),im.return_from()))
            im.intercept(0xc9d4c,'Supply the explicit silent capture configuration at the filesystem boundary.',lambda im:(cpu.mem_write(cpu.reg_read(r.UC_X86_REG_EDX),configuration),im.return_from()))
            im.intercept(0xc71b4,'Supply an empty DOS resource root for the original archive loader.',lambda im:(cpu.mem_write(cpu.reg_read(r.UC_X86_REG_EAX),b'\0'),im.return_from()))
            for address in (0xc4f0c,0xa5ce0,0xa6424,0xa6458,0xa629c,0xa4ddc):
                im.intercept(address,'External DOS audio devices and analogue calibration are outside this silent preview capture.',lambda im:im.return_from())
            im.intercept(0xb3f2c,'Host DOS real-mode interrupt transport without installing physical vectors.',lambda im:im.return_from())
            im.call(0xc86b4,limit=2000000)
            im.call(0xc756c,limit=2000000)
        if not previews:
            # Original scan conversion startup, stopping before its external display-driver call.
            cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
            cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=5000)
            assert cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0xb9133)

    def motion(self, im):
        for offset, value in zip((4,8),self.movement):
            pointer, = struct.unpack('<I',self.cpu.mem_read(self.cpu.reg_read(r.UC_X86_REG_ESP)+offset,4))
            self.cpu.mem_write(pointer,struct.pack('<i',value))
        im.return_from()

    def initialise_aircraft(self,aircraft):
        self.image.write(0x119a0,'<I',self.image.read(0x5c00+aircraft*4,'<I')[0])
        self.image.write(0x11b2a,'<H',aircraft)
        for address in (0x8c184,0x8c318,0x8b248,0x8a6c0,0x8a740,0x8a768,0x8a7b0):
            self.image.call(address,limit=10000000)
        self.image.write(0x132fc,'<I',self.image.native(0x89590))

    def open_screen(self,*,incomplete=False):
        im=self.image
        self.events.clear();self.palettes.clear()
        im.write(0x11b3d,'<B',0)
        if incomplete:
            # Execute the service wrapper's actual prefix, up to its call of
            # the shared arming screen. This installs the incomplete callback.
            im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
            im.cpu.emu_start(im.native(0x8b5e0),im.native(0x8b47c),count=100)
            assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8b47c)
        im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
        im.cpu.emu_start(im.native(0x8b47c),im.native(0x8b502),count=10000000)
        assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8b502)
        assert self.events[-1]==(im.read(0x7f24,'<H')[0],5)
        source=self.read('iff/raw/armscr2.lbm')[4:772]
        assert self.palettes==[bytes(value*level//40 for value in source) for level in range(1,41)]
        return list(self.palettes)

    def inventory(self,stores):
        for slot,weapon in enumerate(stores):
            self.image.write(0x13374+slot*2,'<2B',255 if weapon<0 else weapon,int(weapon>=0))
            handle=65535 if weapon<0 else self.image.read(0x132a8+weapon*2,'<H')[0]
            self.cpu.mem_write(self.image.native(0x70aa4+0x47c94+slot*2),struct.pack('<H',handle))

    def frame(self,first,selected,stores,previous_drag=0):
        self.inventory(stores)
        self.image.write(0x7f2c,'<H',first)
        self.image.write(0x1330e,'<h',selected)
        self.image.write(0x14358,'<d',previous_drag)
        if selected>=first:self.image.call(0x8b1cc,eax=selected-first)
        # Execute the outer loop's actual right-button dispatch before its draw.
        self.cpu.reg_write(r.UC_X86_REG_ESP,self.image.STACK)
        self.cpu.emu_start(self.image.native(0x8b591),self.image.native(0x8b5a4),count=1000)
        assert self.cpu.reg_read(r.UC_X86_REG_EIP)==self.image.native(0x8b5a4)
        self.image.call(0x8a7d0)
        self.image.call(0x8b184,limit=20000000)
        return self.displayed

#!/usr/bin/env python3
"""Original arming widgets/controller with supplied host I/O and excluded 3D previews."""
import struct
from unicorn import x86_const as r
from native_planner import NativePlanner


class NativeArming(NativePlanner):
    def __init__(self,data_dir,research):
        super().__init__(data_dir,research)
        self.position=(100,75)
        self.buttons=0
        self.events=[]
        p=self;im=self.image;cpu=self.cpu
        for address in (0x74614,0x8c43c,0x74508,0x7dde4,0xa4dfc,0xa4edc,0xa6068):im.intercept(address,'Host input, timer and output notifications outside this fixed arming UI capture.',lambda im:im.return_from())
        im.intercept(0xb52d4,'Record SSD event notifications; actual preview objects are supplied in this 2D capture.',lambda im:(self.events.append((cpu.reg_read(r.UC_X86_REG_EAX),cpu.reg_read(r.UC_X86_REG_EDX))),im.return_from()))
        im.intercept(0x744e4,'Supply no DOS mouse driver during original player initialization.',lambda im:(cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
        handles={}

        def model(im):
         address=cpu.reg_read(r.UC_X86_REG_EAX)
         name=p.text(address) if address else '<unset player>'
         if name not in handles:handles[name]=len(handles)+1
         cpu.reg_write(r.UC_X86_REG_EAX,handles[name]);im.return_from()
        for address in (0xb4d98,0xc93bc):im.intercept(address,'Supply stable model handles; 3D preview drawing is excluded from this widget-only capture.',model)
        for address in (0xb4ff0,0xb6ea4,0xc488d,0xc48e1):im.intercept(address,'3D preview placement/rendering is outside this widget-only capture.',lambda im:im.return_from())
        def mouse(im):
         for offset,value in ((4,self.position[0]),(8,self.position[1]),(12,self.buttons)):
          pointer,=struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+offset,4));cpu.mem_write(pointer,struct.pack('<I',value))
         im.return_from()
        im.intercept(0xc72ff,'Supply selected absolute mouse coordinates and buttons.',mouse)
        im.intercept(0xb47b9,'Report original fatal diagnostics without entering DOS exit.',lambda im:(_ for _ in ()).throw(RuntimeError(p.text(cpu.reg_read(r.UC_X86_REG_EAX)))))
        def bitmap(im):
         name=p.text(cpu.reg_read(r.UC_X86_REG_EAX));raw=p.read('iff/raw/'+name);assert len(raw)==64772
         for plane,out in enumerate(p.video.page(p.video.get(0x55907))):out[:]=raw[772+plane::4]
         cpu.mem_write(im.data+0x20ce0,raw[4:772]);cpu.mem_write(im.data+0x21000,raw[4:772]);cpu.reg_write(r.UC_X86_REG_EAX,1);im.return_from()
        im.intercept(0xc6f64,'Supply independently decoded external screen artwork at the original image-driver boundary.',bitmap)
        im.call(0xde547) # Original Watcom startup installs the floating printf handlers.

    def initialise_aircraft(self,aircraft):
        self.image.write(0x119a0,'<I',self.image.read(0x5c00+aircraft*4,'<I')[0])
        self.image.write(0x11b2a,'<H',aircraft)
        for address in (0x8c184,0x8c318,0x8b248,0x8a6c0,0x8a740,0x8a768,0x8a7b0):
            self.image.call(address,limit=10000000)
        self.image.write(0x132fc,'<I',self.image.native(0x89590))

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
        self.image.call(0x8a7d0)
        self.image.call(0x8b184,limit=20000000)
        return self.displayed

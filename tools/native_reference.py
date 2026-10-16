#!/usr/bin/env python3
"""Relocated, bounded execution of the September 1994 reference executable.

Requires Unicorn; never writes to an installation. This is a verification tool,
not an emulator used by the game. Every intercepted dependency needs a reason.
"""
import hashlib
from pathlib import Path
import re
import struct

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn import x86_const as r

REFERENCE_SHA256 = '2cc41a39fa95a2c9fd883c4220d7bdd9cca00c543c89b019eb270763f59d1d9a'


def load_le(data):
    # DOS/4G is prepended. LE data-page offsets use the embedded MZ origin;
    # table offsets use the LE origin, 0x60 bytes further into this file.
    candidates=[m.start() for m in re.finditer(b'MZ',data)]
    for mz in candidates:
        if mz+64>len(data):continue
        le=mz+struct.unpack_from('<I',data,mz+0x3c)[0]
        if data[le:le+2]==b'LE':break
    else:raise ValueError('No embedded MZ/LE executable')
    u32=lambda at:struct.unpack_from('<I',data,at)[0]
    page_size=u32(le+0x28);page_count=u32(le+0x14);last_size=u32(le+0x2c)
    object_table=le+u32(le+0x40);page_table=le+u32(le+0x48)
    pages=[];objects=[]
    for i in range(page_count):
        at=page_table+i*4;physical=int.from_bytes(data[at:at+3],'big');flags=data[at+3]
        if flags!=0 or not physical:raise ValueError('Unsupported nonphysical LE page')
        offset=mz+u32(le+0x80)+(physical-1)*page_size
        length=last_size if physical==page_count else page_size
        if offset+length>len(data):raise ValueError('LE page exceeds executable')
        pages.append({'physical':physical,'file':offset,'length':length})
    page_owners={}
    for i in range(u32(le+0x44)):
        size,base,flags,first,count,reserved=struct.unpack_from('<6I',data,object_table+i*24)
        obj={'number':i+1,'virtual_size':size,'preferred_base':base,'flags':flags,'first_page':first,'page_count':count,'file':pages[first-1]['file'] if count else None,'initialised_bytes':min(size,sum(p['length'] for p in pages[first-1:first-1+count]))}
        objects.append(obj)
        for j in range(count):page_owners[first-1+j]=(obj,j*page_size)
    def file_at(obj,offset):
        if not 0<=offset<obj['initialised_bytes']:return None
        page=pages[obj['first_page']-1+offset//page_size]
        return page['file']+offset%page_size
    fixup_pages=le+u32(le+0x68);fixup_records=le+u32(le+0x6c)
    fixups=[];record_count=0
    for page in range(page_count):
        at=fixup_records+u32(fixup_pages+page*4);end=fixup_records+u32(fixup_pages+(page+1)*4)
        owner,base=page_owners[page]
        while at<end:
            record=at;source,flags=data[at:at+2];at+=2
            if flags&0x0b:raise ValueError(f'Unsupported LE target at {record:#x}')
            count=data[at] if source&0x20 else 1
            offsets=[]
            if source&0x20:at+=1
            else:offsets=[struct.unpack_from('<h',data,at)[0]];at+=2
            width=2 if flags&0x40 else 1
            target_obj=int.from_bytes(data[at:at+width],'little');at+=width
            target_offset=0
            if source&15!=2:
                width=4 if flags&0x10 else 2
                target_offset=int.from_bytes(data[at:at+width],'little');at+=width
            if flags&4:
                width=4 if flags&0x20 else 2;at+=width
                raise ValueError('Additive relocation needs explicit handling')
            if source&0x20:offsets=list(struct.unpack_from(f'<{count}h',data,at));at+=count*2
            if not 1<=target_obj<=len(objects):raise ValueError('Invalid target object')
            target=objects[target_obj-1]
            # Linker expressions can be biased outside the nominal object.
            # Keep their raw value and leave their file target unresolved.
            for offset in offsets:
                source_offset=base+offset
                if source_offset<0:raise ValueError('Negative object-relative fixup')
                fixups.append({'record':record,'source_type':source&15,'source_object':owner['number'],'source_offset':source_offset,'source_file':file_at(owner,source_offset),'target_object':target_obj,'target_offset':target_offset,'target_file':file_at(target,target_offset)})
            record_count+=1
        if at!=end:raise ValueError('Fixup page record length mismatch')
    # Cross-page records can describe the same source twice.
    unique={(f['source_object'],f['source_offset'],f['target_object'],f['target_offset']):f for f in fixups}
    return {'mz':mz,'le':le,'page_size':page_size,'pages':pages,'objects':objects,'entry_object':u32(le+0x18),'entry_offset':u32(le+0x1c),'fixup_records':record_count,'fixups':list(unique.values())}



class NativeReference:
    RETURN = 0x200000
    STACK = 0x380000

    def __init__(self, filename, *, data_base=None):
        executable = Path(filename).read_bytes()
        if hashlib.sha256(executable).hexdigest() != REFERENCE_SHA256:
            raise ValueError('native capture requires September 1994 TFX 2.05')
        self.executable = executable
        self.layout = load_le(executable)
        # Keep the actual A0000 VGA aperture available when a capture needs
        # native raster loops with embedded hardware addresses. All data
        # references still use the executable's own LE relocation records.
        if data_base is not None:self.layout['objects'][2]['preferred_base']=data_base
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_32)
        for obj in self.layout['objects']:
            size = (obj['virtual_size'] + 4095) & ~4095
            self.cpu.mem_map(obj['preferred_base'], size)
            for index in range(obj['page_count']):
                page = self.layout['pages'][obj['first_page'] - 1 + index]
                length = min(page['length'], obj['virtual_size'] - index * self.layout['page_size'])
                self.cpu.mem_write(obj['preferred_base'] + index * self.layout['page_size'], executable[page['file']:page['file'] + length])
        for fixup in self.layout['fixups']:
            if fixup['source_type'] != 7:
                raise ValueError('native capture only supports 32-bit offset fixups')
            source = self.layout['objects'][fixup['source_object'] - 1]['preferred_base'] + fixup['source_offset']
            target = self.layout['objects'][fixup['target_object'] - 1]['preferred_base'] + fixup['target_offset']
            self.cpu.mem_write(source, struct.pack('<I', target & 0xffffffff))
        self.data = self.layout['objects'][2]['preferred_base']
        self.cpu.mem_map(self.RETURN, 4096)
        self.cpu.mem_map(0x350000, 4096)
        self.cpu.mem_map(0x370000, 0x20000)
        self.cpu.mem_write(0x350000, struct.pack('<3Q', 0, 0x00cf9a000000ffff, 0x00cf92000000ffff))
        self.cpu.reg_write(r.UC_X86_REG_GDTR, (0, 0x350000, 23, 0))
        for register, selector in [(r.UC_X86_REG_CS, 8), (r.UC_X86_REG_DS, 16), (r.UC_X86_REG_ES, 16), (r.UC_X86_REG_SS, 16)]:
            self.cpu.reg_write(register, selector)
        # Controlled x87 environment; captures must state when DOS startup's
        # actual control word has not yet been established independently.
        self.cpu.reg_write(r.UC_X86_REG_FPCW, 0x037f)
        self.dependencies = {}
        self.trace = []
        self.cpu.hook_add(UC_HOOK_INTR, self._interrupt)

    def native(self, file):
        code = self.layout['objects'][0]
        offset = file - code['file']
        if not 0 <= offset < code['initialised_bytes']:
            raise ValueError(f'not a reference code address: {file:#x}')
        return code['preferred_base'] + offset

    def read(self, offset, format):
        return struct.unpack(format, self.cpu.mem_read(self.data + offset, struct.calcsize(format)))

    def write(self, offset, format, *values):
        self.cpu.mem_write(self.data + offset, struct.pack(format, *values))

    def intercept(self, file, reason, callback):
        if not reason or file in self.dependencies:
            raise ValueError('an intercepted dependency needs a unique address and an explicit reason')
        self.dependencies[file] = reason

        def hook(cpu, address, size, unused):
            self.trace.append(file)
            callback(self)

        address = self.native(file)
        self.cpu.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)

    def return_from(self, stack_bytes=0):
        stack = self.cpu.reg_read(r.UC_X86_REG_ESP)
        destination, = struct.unpack('<I', self.cpu.mem_read(stack, 4))
        self.cpu.reg_write(r.UC_X86_REG_ESP, stack + 4 + stack_bytes)
        self.cpu.reg_write(r.UC_X86_REG_EIP, destination)

    def call(self, file, *, eax=0, edx=0, ebx=0, ecx=0, stack=(), limit=200000):
        self.cpu.mem_write(self.STACK, struct.pack('<' + 'I' * (len(stack) + 1), self.RETURN, *stack))
        for register, value in [(r.UC_X86_REG_ESP, self.STACK), (r.UC_X86_REG_EAX, eax), (r.UC_X86_REG_EDX, edx), (r.UC_X86_REG_EBX, ebx), (r.UC_X86_REG_ECX, ecx), (r.UC_X86_REG_EFLAGS, 0x202)]:
            self.cpu.reg_write(register, value)
        try:
            self.cpu.emu_start(self.native(file), self.RETURN, count=limit)
        except UcError as error:
            raise RuntimeError(f'native {file:#x} failed at {self.cpu.reg_read(r.UC_X86_REG_EIP):#x}: {error}') from error
        if self.cpu.reg_read(r.UC_X86_REG_EIP) != self.RETURN:
            raise RuntimeError(f'native {file:#x} did not return within {limit} instructions')
        return self.cpu.reg_read(r.UC_X86_REG_EAX)

    @staticmethod
    def _interrupt(cpu, number, unused):
        raise RuntimeError(f'undeclared native interrupt {number:#x}')

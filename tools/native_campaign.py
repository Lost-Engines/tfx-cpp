"""Original retail parser control and save handlers, with explicit host boundaries.

Media, menus and flights are yielded to the caller. Branch/assignment/return
handlers and save serialization execute original instructions. No user files
are read or written; original file I/O is redirected to memory.
"""
import struct
from native_reference import NativeReference,r


class NativeCampaign:
    def __init__(self,directory,program):
        self.program=program
        self.image=im=NativeReference(directory/'TFX.DAT')
        im.cpu.mem_map(0x300000,0x40000)
        self.variables=program['variables'];self.functions=program['functions']
        self.ordinals={v['name']:i for i,v in enumerate(self.variables)}
        im.write(0xab41,'<B',1);im.write(0x1afee,'<H',len(self.variables))
        im.cpu.mem_write(im.data+0x1ad44,bytes(int(v['string_value']) for v in self.variables)+bytes(30-len(self.variables)))
        descriptors=[]
        for index,variable in enumerate(self.variables):
            name=variable['name'].encode()+b'\0'
            im.cpu.mem_write(im.data+0x1ad62+index*21,name)
            pointer=0x300000+index*64
            im.cpu.mem_write(pointer,bytes(9)+name);descriptors.append(pointer)
        nodes=[(fi,ni) for fi,f in enumerate(self.functions) for ni in range(len(f['nodes']))]
        self.addresses={node:0x310000+index*64 for index,node in enumerate(nodes)}
        assert max(self.addresses.values())+64<0x32d000
        self.locations={pointer:node for node,pointer in self.addresses.items()}
        for (fi,ni),pointer in self.addresses.items():
            node=self.functions[fi]['nodes'][ni]
            successor=self.addresses.get((fi,ni+1),0)
            im.cpu.mem_write(pointer,struct.pack('<B3I',node['type'],successor,self.addresses.get((fi,ni-1),0),pointer+16))
            if node['type'] in (3,10):
                raw=bytearray.fromhex(node['payload_hex']);at=1 if node['type']==3 else 0
                ordinal=struct.unpack_from('<I',raw,at)[0]
                struct.pack_into('<I',raw,at,descriptors[ordinal] if ordinal<len(descriptors) else 0)
                if node['type']==3:struct.pack_into('<I',raw,13,self.addresses[(raw[11],raw[12])])
                im.cpu.mem_write(pointer+16,bytes(raw))
        for fi,function in enumerate(self.functions):
            pointer=0x32e000+fi*25
            im.cpu.mem_write(pointer,struct.pack('<3IH',pointer+25 if fi+1<len(self.functions) else 0,pointer-25 if fi else 0,self.addresses[(fi,0)],len(function['nodes'])))
        im.write(0x1ad3c,'<I',0x32e000);im.write(0x1afea,'<H',len(self.functions))
        self.input=b'';self.read_at=0;self.output=bytearray()
        im.intercept(0xcc434,'Save transport: retain original write bytes in memory',self._write)
        im.intercept(0xcc41c,'Save transport: supply original read bytes from memory',self._read)
        im.intercept(0xb0eb0,'Treat native parser/save fatal diagnostics as comparison failures',self._fail)
        self.cursor=0

    def _write(self,im):
        pointer=im.cpu.reg_read(r.UC_X86_REG_EAX);length=im.cpu.reg_read(r.UC_X86_REG_EDX)
        self.output.extend(im.cpu.mem_read(pointer,length));im.cpu.reg_write(r.UC_X86_REG_EAX,length);im.return_from()

    def _read(self,im):
        pointer=im.cpu.reg_read(r.UC_X86_REG_EAX);length=im.cpu.reg_read(r.UC_X86_REG_EDX)
        data=self.input[self.read_at:self.read_at+length];assert len(data)==length
        im.cpu.mem_write(pointer,data);self.read_at+=length;im.cpu.reg_write(r.UC_X86_REG_EAX,length);im.return_from()

    def _fail(self,im):
        raise RuntimeError('original parser/save rejected its state')

    def set(self,name,value):
        self.image.write(0x1a400+self.ordinals[name]*4,'<I',value&0xffffffff)

    def values(self):
        return {v['name']:self.image.read(0x1a400+i*4,'<I')[0] for i,v in enumerate(self.variables) if not v['string_value']}

    def reset(self,entry,values):
        im=self.image
        for index,variable in enumerate(self.variables):
            if variable['string_value']:
                pointer=0x303000+index*32
                im.cpu.mem_write(pointer,b'TEST'+bytes(17));im.write(0x1a400+index*4,'<I',pointer)
            else:self.set(variable['name'],values.get(variable['name'],0))
        for index in range(len(self.variables),30):im.write(0x1a400+index*4,'<I',0)
        im.write(0x1afdc,'<H',0)
        self.cursor=self.addresses[entry]

    def run(self):
        im=self.image
        for _ in range(65536):
            if not self.cursor:return None
            fi,ni=self.locations[self.cursor];kind=self.functions[fi]['nodes'][ni]['type']
            successor=self.addresses.get((fi,ni+1),0)
            im.write(0x1ad1c,'<I',self.cursor);im.write(0x1ad14,'<I',successor)
            if kind in (3,10):
                im.call(0xb22d8 if kind==3 else 0xb28b8,eax=self.cursor+16)
                self.cursor=im.read(0x1ad14,'<I')[0]
            elif kind==4:
                assert im.read(0x1afdc,'<H')[0],'return without caller'
                im.call(0xb2574);resumed=self.locations[im.read(0x1ad1c,'<I')[0]]
                self.cursor=self.addresses.get((resumed[0],resumed[1]+1),0)
            else:return fi,ni,kind
        raise RuntimeError('original campaign control did not yield')

    def complete(self):
        fi,ni=self.locations[self.cursor]
        self.cursor=self.addresses.get((fi,ni+1),0)

    def row(self,action):
        if action is None:return [-1]
        depth=self.image.read(0x1afdc,'<H')[0]
        result=[*action,*self.values().values(),depth]
        for index in range(depth):result.extend(self.locations[self.image.read(0x1ab68+index*4,'<I')[0]])
        return result

    def save(self,mode):
        self.image.write(0x1ad1c,'<I',self.cursor)
        self.output.clear();self.image.call(0xb3aa8,eax=7,edx=mode,limit=1000000)
        return bytes(self.output)

    def restore(self,raw):
        self.input=raw;self.read_at=0
        self.image.write(0x1ad1c,'<I',self.cursor)
        self.image.call(0xb3c14,eax=7,limit=1000000)
        assert self.read_at==len(raw)
        self.cursor=self.image.read(0x1ad1c,'<I')[0]

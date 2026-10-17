"""Controlled original 16-bit OSL master/device execution for audio comparisons."""
import hashlib
import struct
from unicorn import Uc,UC_ARCH_X86,UC_MODE_16,UC_HOOK_CODE,UC_HOOK_INSN,UC_HOOK_INTR
from unicorn import x86_const as r


class NativeOSL:
    def __init__(self, launcher, mode='rld'):
        assert hashlib.sha256(launcher).hexdigest()=='c5a60c7791c971a872aaed1e19ef2638aab0b21eb1e039907b8d64eb8f8980d6'
        self.cpu=c=Uc(UC_ARCH_X86,UC_MODE_16)
        c.mem_map(0,0x100000)
        c.mem_write(0x10000,launcher[0x3730:0x57b0])
        start,end={'adl':(0x57b0,0x6890),'scc':(0x6890,0x7120),'rld':(0x7120,0x7670)}[mode]
        c.mem_write(0x20000,launcher[start:end])
        c.mem_write(0x40000,struct.pack('<4H',0x2000,0,0xffff,0))
        c.mem_write(0x60000,b"\xcf") # supplied previous BIOS timer: IRET only
        self.pit=[]
        self.events=[]
        self.mode=mode
        self.opl_address=0
        self.opl_timer=False
        c.hook_add(UC_HOOK_INSN,self._read,None,1,0,r.UC_X86_INS_IN)
        c.hook_add(UC_HOOK_INSN,self._write,None,1,0,r.UC_X86_INS_OUT)
        c.hook_add(UC_HOOK_INTR,self._interrupt)
        if mode=='rld':c.hook_add(UC_HOOK_CODE,self._skip_delay,None,0x20173,0x20173)
        elif mode=='scc':c.hook_add(UC_HOOK_CODE,self._skip_delay,None,0x20272,0x20272)

    def _read(self,c,port,size,user):
        if port==0x330:return 0xfe
        if port==0x388:return 0xc0 if self.opl_timer else 0
        return 0

    def _write(self,c,port,size,value,user):
        if port==0x40:self.pit.append(value&255)
        if port==0x330:self.events.append(value&255)
        if port==0x388:self.opl_address=value&255
        if port==0x389:
            if self.opl_address==4:self.opl_timer=bool(value&1) and not bool(value&128)
            self.events.extend([self.opl_address,value&255])

    def _interrupt(self,c,intno,user):
        if intno==0x21:
            ax=c.reg_read(r.UC_X86_REG_AX)
            if ax==0x3508:c.reg_write(r.UC_X86_REG_ES,0x6000);c.reg_write(r.UC_X86_REG_BX,0)
            elif ax!=0x2508:raise RuntimeError(f'unsupported DOS interrupt {ax:x}')
        elif intno==0x60:
            sp=(c.reg_read(r.UC_X86_REG_SP)-6)&65535;ss=c.reg_read(r.UC_X86_REG_SS)
            ip=c.reg_read(r.UC_X86_REG_IP);cs=c.reg_read(r.UC_X86_REG_CS);flags=c.reg_read(r.UC_X86_REG_EFLAGS)
            c.mem_write(ss*16+sp,struct.pack('<HHH',ip,cs,flags&65535));c.reg_write(r.UC_X86_REG_SP,sp)
            offset,segment=struct.unpack('<HH',c.mem_read(intno*4,4));c.reg_write(r.UC_X86_REG_CS,segment);c.reg_write(r.UC_X86_REG_IP,offset)
        else:raise RuntimeError(f'unsupported interrupt {intno:x}')

    def _skip_delay(self,c,address,size,user):
        sp=c.reg_read(r.UC_X86_REG_SP);ss=c.reg_read(r.UC_X86_REG_SS)
        ip=int.from_bytes(c.mem_read(ss*16+sp,2),'little')
        c.reg_write(r.UC_X86_REG_SP,(sp+2)&65535);c.reg_write(r.UC_X86_REG_IP,ip)

    def call(self,ip,kind='near',**registers):
        c=self.cpu
        for name,value in [('CS',0x1000),('DS',0x1000),('ES',0x1000),('SS',0x5000),('SP',0xfff0),('AX',0),('BX',0),('CX',0),('DX',0),('DI',0),('SI',0),('BP',0),('EFLAGS',0x202)]:c.reg_write(getattr(r,'UC_X86_REG_'+name),value)
        for name,value in registers.items():c.reg_write(getattr(r,'UC_X86_REG_'+name),value)
        stack=struct.pack('<H',0xff00)
        if kind in ('far','iret'):stack+=struct.pack('<H',0x1000)
        if kind=='iret':stack+=struct.pack('<H',0x202)
        c.mem_write(0x5fff0,stack);c.emu_start(0x10000+ip,0x1ff00,count=10000000)
        assert c.reg_read(r.UC_X86_REG_IP)==0xff00,(hex(c.reg_read(r.UC_X86_REG_CS)),hex(c.reg_read(r.UC_X86_REG_IP)))
        return c.reg_read(r.UC_X86_REG_AX),bool(c.reg_read(r.UC_X86_REG_EFLAGS)&1)

    def initialise(self):return self.call(0x7b6,'far',AX=0x60,BX=1,ES=0x4000)
    def load(self,song):
        self.cpu.mem_write(0x30000,song)
        return self.call(0x9b4,'iret',AX=0x0200,BX=0x3000)
    def play(self,volume=75):return self.call(0x9b4,'iret',AX=0x0400,BX=0,CX=0,DX=volume)
    def tick(self):return self.call(0x1026)
    def shared_timer(self):
        self.call(0x9b4,'iret',AX=0x1500)
        self.call(0x9b4,'iret',AX=0x1700)
    def host_tick(self):return self.call(0x1e03,'iret')
    def channels(self):return bytes(self.cpu.mem_read(0x103c9,32*21))
    def state(self):
        data=bytes(self.cpu.mem_read(0x10037,0x39))
        u16=lambda at:struct.unpack_from('<H',data,at)[0]
        return [data[0],data[1],data[2],u16(3),data[5],data[6],data[7],data[9],u16(10),u16(12),data[14],*data[15:18],u16(22),int.from_bytes(self.cpu.mem_read(0x1071c,2),'little')]

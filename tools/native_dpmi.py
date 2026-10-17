"""DPMI 0.9 exception transport for original-code verification.

The host supplies vector storage and the documented 32-bit exception stack.
The installed game handler executes unchanged and chooses the resumed EIP.
https://www.delorie.com/djgpp/doc/dpmi/ch4.5.html
"""
import struct
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference, r


class DpmiReference(NativeReference):
    EXCEPTION_STACK = 0x390000
    EXCEPTION_RETURN = NativeReference.RETURN + 0x100
    ARCHITECTURE = ('GDTR', 'IDTR', 'LDTR', 'TR', 'CR0', 'CR2', 'CR3', 'CR4',
                    'CS', 'DS', 'ES', 'FS', 'GS', 'SS',
                    'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'EBP', 'ESP', 'EIP',
                    *('DR' + str(index) for index in range(8)),
                    *('FP' + str(index) for index in range(8)),
                    'FPCW', 'FPSW', 'FPTAG', 'FIP', 'FCS', 'FDP', 'FDS', 'FOP',
                    *('XMM' + str(index) for index in range(8)), 'MXCSR', 'EFLAGS')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exception_vectors = {}
        self.exception_frames = []
        self.processor_exceptions = []
        self.cpu.mem_map(self.EXCEPTION_STACK, 4096)
        self.idle_context = self.cpu.context_save()
        self.cpu.hook_add(UC_HOOK_CODE, self._exception_return,
                          begin=self.EXCEPTION_RETURN, end=self.EXCEPTION_RETURN)

    def _interrupt(self, cpu, interrupt, unused):
        operation = cpu.reg_read(r.UC_X86_REG_EAX) & 65535
        if interrupt == 0x31 and operation in (0x202, 0x203):
            vector = cpu.reg_read(r.UC_X86_REG_EBX) & 255
            if operation == 0x202:
                selector, offset = self.exception_vectors.get(vector, (0, 0))
                cpu.reg_write(r.UC_X86_REG_ECX, selector)
                cpu.reg_write(r.UC_X86_REG_EDX, offset)
            else:
                self.exception_vectors[vector] = (cpu.reg_read(r.UC_X86_REG_ECX) & 65535,
                                                  cpu.reg_read(r.UC_X86_REG_EDX))
            cpu.reg_write(r.UC_X86_REG_EFLAGS, cpu.reg_read(r.UC_X86_REG_EFLAGS) & ~1)
            return
        selector, handler = self.exception_vectors.get(interrupt, (0, 0))
        if interrupt < 32 and selector and handler:
            if self.exception_frames:
                raise RuntimeError('nested native exception exceeds the declared capture host')
            original = {name: cpu.reg_read(getattr(r, 'UC_X86_REG_' + name))
                        for name in ('EIP', 'CS', 'EFLAGS', 'ESP', 'SS')}
            # Unicorn's interrupt hook bypasses QEMU's normal delivery, which
            # clears old_exception. Restore a clean internal context while
            # preserving the complete 32-bit client's architectural registers.
            # Otherwise a second handled divide is mistaken for a double fault.
            registers = [(getattr(r, 'UC_X86_REG_' + name),
                          cpu.reg_read(getattr(r, 'UC_X86_REG_' + name)))
                         for name in self.ARCHITECTURE]
            cpu.context_restore(self.idle_context)
            for register, value in registers:
                cpu.reg_write(register, value)
            frame = self.EXCEPTION_STACK + 4096 - 32
            # Return EIP/CS, undefined error code, fault EIP/CS/EFLAGS/ESP/SS.
            cpu.mem_write(frame, struct.pack('<8I', self.EXCEPTION_RETURN, original['CS'], 0,
                                             *[original[name] for name in ('EIP', 'CS', 'EFLAGS', 'ESP', 'SS')]))
            self.exception_frames.append((frame, interrupt, original['EIP']))
            cpu.reg_write(r.UC_X86_REG_ESP, frame)
            cpu.reg_write(r.UC_X86_REG_EFLAGS, original['EFLAGS'] & ~0x300)
            cpu.reg_write(r.UC_X86_REG_CS, selector)
            cpu.reg_write(r.UC_X86_REG_EIP, handler)
            return
        super()._interrupt(cpu, interrupt, unused)

    def _exception_return(self, cpu, address, size, unused):
        if not self.exception_frames:
            raise RuntimeError('native exception returned without a host frame')
        frame, vector, fault = self.exception_frames.pop()
        if cpu.reg_read(r.UC_X86_REG_ESP) != frame + 8:
            raise RuntimeError('native exception handler did not preserve its return stack')
        eip, cs, flags, esp, ss = struct.unpack('<5I', cpu.mem_read(frame + 12, 20))
        self.processor_exceptions.append({'vector': vector, 'fault': fault, 'resume': eip})
        cpu.reg_write(r.UC_X86_REG_SS, ss)
        cpu.reg_write(r.UC_X86_REG_ESP, esp)
        cpu.reg_write(r.UC_X86_REG_CS, cs)
        cpu.reg_write(r.UC_X86_REG_EFLAGS, flags)
        cpu.reg_write(r.UC_X86_REG_EIP, eip)

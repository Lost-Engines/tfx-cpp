#!/usr/bin/env python3
"""Exercise the original renderer's four divide-fault recovery branches.

Executes the actual vector-installation prefix, faulting IDIV and game exception
handler. The host supplies DPMI delivery/return only. Stops on the continuation
chosen by the game, before unrelated renderer state is consumed.
"""
import argparse
from pathlib import Path
from unicorn import UC_HOOK_CODE
from native_dpmi import DpmiReference
from native_reference import r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    args = parser.parse_args()
    image = DpmiReference(args.research / 'installs/cd_1994_09/TFX/TFX.DAT', data_base=0x100000)
    cpu = image.cpu
    cpu.reg_write(r.UC_X86_REG_ESP, image.STACK - 256)
    image.cpu.emu_start(image.native(0xb90de), image.native(0xb9110), count=1000)
    assert image.exception_vectors[0] == (8, image.native(0xb91ac)), image.exception_vectors
    stop = [0]

    def continuation(cpu, address, size, unused):
        if address == stop[0]:
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_CODE, continuation)
    code = image.layout['objects'][0]
    file_address = lambda address: code['file'] + address - code['preferred_base']
    cases = [(file_address(fault), file_address(resume))
             for fault, resume in ((0x589d3, 0x588df), (0x589e8, 0x588df),
                                   (0x591a9, 0x591dc), (0x591d1, 0x591dc))]
    count = 0
    for fault, resume in cases:
        for divisor in (0, 1):
            for index in range(8):
                cpu.reg_write(getattr(r, 'UC_X86_REG_FP' + str(index)),
                              (0x8000000000000000 + index * 0x100000000000000, 0x3fff + index))
                cpu.reg_write(getattr(r, 'UC_X86_REG_XMM' + str(index)), (index + 1) * 0x11112222333344445555666677778888)
            for name, value in dict(FPCW=0x127f, FPSW=(count % 8) << 11, FPTAG=0,
                                    FIP=0x123456, FDP=0x234567, FOP=0x123, MXCSR=0x1f80).items():
                cpu.reg_write(getattr(r, 'UC_X86_REG_' + name), value)
            registers = dict(EAX=0, EDX=1, EBX=divisor, ECX=divisor,
                             ESI=0x12345678, EDI=0x23456789, EBP=0x3456789a,
                             ESP=image.STACK - 256, EFLAGS=0x202)
            for name, value in registers.items():
                cpu.reg_write(getattr(r, 'UC_X86_REG_' + name), value)
            architecture = {name: cpu.reg_read(getattr(r, 'UC_X86_REG_' + name))
                            for name in image.ARCHITECTURE if name != 'EIP'}
            stop[0] = image.native(resume)
            cpu.emu_start(image.native(fault), image.RETURN, count=1000)
            assert cpu.reg_read(r.UC_X86_REG_EIP) == stop[0], (hex(fault), hex(cpu.reg_read(r.UC_X86_REG_EIP)))
            assert image.processor_exceptions[-1] == {'vector': 0, 'fault': image.native(fault), 'resume': stop[0]}
            for name, value in architecture.items():
                assert cpu.reg_read(getattr(r, 'UC_X86_REG_' + name)) == value, (hex(fault), name)
            assert not image.exception_frames
            count += 1
    assert len(image.processor_exceptions) == count
    print(f'{count} original renderer divide faults execute their installed handler and resume at the native continuation with integer, segment, x87, SSE, control/debug registers, flags and stack preserved')


if __name__ == '__main__':
    main()

"""Original filename-widget input through hosted DOS mouse/keyboard devices."""
from pathlib import Path
from native_configuration_menu import menu_image
from native_reference import NativeReference, r


class NameReference(NativeReference):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cpu.mem_map(0x330000, 0x10000)
        self.write(0x1b238, '<I', 0x330000)
        self.write(0x1b23c, '<I', 0x331000)
        self.mouse = 0
        self.point = (160, 140)

    def _interrupt(self, cpu, number, unused):
        if number != 0x33:
            raise RuntimeError(f'undeclared filename-widget interrupt {number:#x}')
        operation = cpu.reg_read(r.UC_X86_REG_EAX) & 65535
        if operation == 11:
            cpu.reg_write(r.UC_X86_REG_ECX, 0)
            cpu.reg_write(r.UC_X86_REG_EDX, 0)
            return
        if operation not in (3, 5):
            raise RuntimeError(f'undeclared filename-widget mouse operation {operation}')
        cpu.reg_write(r.UC_X86_REG_EAX, self.mouse)
        cpu.reg_write(r.UC_X86_REG_EBX, self.mouse if operation == 5 else 0)
        cpu.reg_write(r.UC_X86_REG_ECX, self.point[0])
        cpu.reg_write(r.UC_X86_REG_EDX, self.point[1])


class RecordingName:
    def __init__(self, executable):
        self.image, self.video, _ = menu_image(Path(executable),
            [0, 2, 2, 0x44000000, 125, 0, 0, 1, 1, 0, 0, 0],
            image_type=NameReference, interactive=True)
        # Construction deliberately yields inside the original menu caller.
        # Retain its stack-backed widgets while making subsequent input calls.
        self.image.STACK -= 0x1000
        for address in (0xdf94b, 0xdf9c8, 0xdf9a9):
            self.image.intercept(address, 'PC-speaker tone, wall-clock wait and tone stop on a full filename are outside widget state/pixel comparison.', lambda image: image.return_from())

    def click(self, x=160, y=140):
        image = self.image
        image.point = (x, y)
        image.write(0xadfc, '<2H', x, y)
        image.mouse = 1
        image.call(0xd07b4, limit=3000000)
        image.mouse = 0
        image.call(0xd07b4, limit=3000000)

    def press(self, scan, shift=False):
        image = self.image
        image.cpu.mem_write(0x330000, bytes([scan]))
        image.cpu.mem_write(0x331000 + 42, bytes([bool(shift)]))
        image.call(0xd07b4, limit=3000000)

    def value(self):
        image = self.image
        editing = bool(image.read(0x240fc, '<I')[0])
        value = bytes(image.cpu.mem_read(image.data + 0x8868, 64)).split(b'\0', 1)[0]
        if editing:
            cursor = image.read(0x13768 + 0x19, '<H')[0]
            value = bytes(image.cpu.mem_read(image.data + 0x8868, cursor)).split(b'\0', 1)[0]
        return value, editing

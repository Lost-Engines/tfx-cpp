"""Original TFX sample loader/scheduler and real-mode callback on original GUS.COM.

Only DOS/DPMI transport and sample file reads are supplied. The actual game
sorts the bank, allocates RAM, schedules requests and patches its own 144-byte
IRQ callback, which executes unchanged when the GF1 ends a voice. Intended for
one-MiB resident-bank comparisons; not used by the C++ game or desktop audio.
"""
from pathlib import Path
import struct
from native_reference import NativeReference, r
from native_gus_device import GusDeviceReference


class GusSamplesReference:
    QUEUE = 0x91000
    QUEUE_BYTES = 1604
    DESCRIPTORS = 0x9860

    def __init__(self, directory, samples, build=Path('build'), synthetic=False):
        self.device = GusDeviceReference(directory / 'GUS.COM', build)
        self.device.boot()
        if synthetic:
            # Explicit test-authored coefficient inputs, not patched instructions.
            for index in range(257):
                self.device.word(self.device.data + 0x32f + index * 2, (index * 13 + 17) & 4095)
        self.image = image = NativeReference(directory / 'TFX.DAT')
        self.samples = samples
        self.selected = None
        image.cpu.mem_map(self.QUEUE, 0x1000)
        image.cpu.mem_map(0x300000, 0x20000)
        image.cpu.mem_write(0x310000, bytes(self.device.cpu.mem_read(self.device.data + 0xdac, 8)))
        image.write(0xe07c, '<I', 0x310000)
        image.write(0x2606c, '<I', self.device.data + 0xdb4)
        image.write(0x20c74, '<I', 0x300000)

        def allocate_callback(current):
            assert current.cpu.reg_read(r.UC_X86_REG_EDX) == self.QUEUE_BYTES
            current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EAX), struct.pack('<H', self.QUEUE // 16))
            current.cpu.reg_write(r.UC_X86_REG_EAX, self.QUEUE)
            current.return_from()

        def install(current):
            self._to_device()
            self.device.command(6, current.cpu.reg_read(r.UC_X86_REG_EAX))
            current.return_from()

        def transport(command, registers, result=False):
            def call(current):
                self._to_device()
                values = self.device.command(command, *(current.cpu.reg_read(register) for register in registers))
                if result:
                    current.cpu.reg_write(r.UC_X86_REG_EAX, values[1])
                current.return_from()
            return call

        image.intercept(0xd5a64, 'Supply private DOS memory for the original real-mode IRQ client.', allocate_callback)
        image.intercept(0xe6b94, 'Install the original patched IRQ client in the actual GUS.COM.', install)
        image.intercept(0xe6b3c, 'Transport stopped query to original GUS.COM.', transport(4, (r.UC_X86_REG_EAX,), True))
        image.intercept(0xe6be4, 'Transport stop request to original GUS.COM.', transport(9, (r.UC_X86_REG_EAX,)))
        image.intercept(0xe6adc, 'Transport resident playback to original GUS.COM.', transport(1,
            (r.UC_X86_REG_EAX, r.UC_X86_REG_EDX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX)))
        image.intercept(0xe6b00, 'Transport voice volume to original GUS.COM.', transport(2,
            (r.UC_X86_REG_EAX, r.UC_X86_REG_EDX)))
        image.intercept(0xe6b68, 'Transport sample allocation to original GUS.COM.', transport(5, (r.UC_X86_REG_EAX,), True))
        image.intercept(0xd5da0, 'Supply sufficient caller stack for the original sort arrays.',
            lambda current: (current.cpu.reg_write(r.UC_X86_REG_EAX, 0x100000), current.return_from()))

        def filename(current):
            self.selected = (current.cpu.reg_read(r.UC_X86_REG_EAX) - image.data - self.DESCRIPTORS) // 26
            assert 0 <= self.selected < len(samples)
            current.cpu.reg_write(r.UC_X86_REG_EAX, 0x310100)
            current.return_from()

        def file_read(current):
            pcm = samples[self.selected][2]
            if pcm:
                current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EDX), pcm)
            current.return_from()

        def upload(current):
            size = current.cpu.reg_read(r.UC_X86_REG_EBX)
            pcm = bytes(current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_EDX), size))
            self.device.cpu.mem_write(0x70000, pcm)
            self.device.command(0, current.cpu.reg_read(r.UC_X86_REG_EAX), 0x70000000, size)
            current.return_from()

        def free(current):
            assert current.cpu.reg_read(r.UC_X86_REG_EAX) == 0, 'resident-bank reference does not supply a streaming heap'
            current.return_from()

        image.intercept(0xc5214, 'Supply a filename for the selected test-authored sample.', filename)
        image.intercept(0xc8cf0, 'Supply declared PCM at the filesystem-read boundary.', file_read)
        image.intercept(0xe6ab8, 'Transport PCM to the original real-mode upload command.', upload)
        image.intercept(0xd3820, 'Observe the null streaming-buffer release for a resident bank.', free)
        image.call(0xddf68, limit=1000000)
        for index, (rate, delay, pcm) in enumerate(samples):
            at = self.DESCRIPTORS + index * 26
            image.write(at, '<IHHIhIIHH', image.data + 0x3874, rate, delay & 65535, 0, 0, len(pcm), 0, 0, 0)
        image.cpu.mem_write(image.data + self.DESCRIPTORS + len(samples) * 26, bytes(26))
        image.call(0xc52d0, eax=image.data + self.DESCRIPTORS, limit=5000000)
        image.call(0xc4f5c, eax=image.data + self.DESCRIPTORS, edx=image.native(0xdde2c), limit=5000000)
        image.call(0xc4f9c, eax=image.data + self.DESCRIPTORS, limit=5000000)
        for index, (_, _, pcm) in enumerate(samples):
            assert not pcm or image.read(self.DESCRIPTORS + index * 26 + 24, '<H')[0] & 7 == 7
        image.call(0xdde74, eax=256)
        image.write(0xac85, '<B', 1)
        self._to_device()

    def _to_device(self):
        self.device.cpu.mem_write(self.QUEUE, bytes(self.image.cpu.mem_read(self.QUEUE, self.QUEUE_BYTES)))

    def close(self):
        self.device.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def enable(self, enabled):
        self.image.write(0xac85, '<B', bool(enabled))

    def advance(self, ticks):
        self.image.call(0xc513c, eax=self.image.data + self.DESCRIPTORS, edx=ticks)

    def submit(self, priority, sequence):
        self.image.call(0xdda88, stack=(priority,
            *(self.image.data + self.DESCRIPTORS + index * 26 for index in sequence), 0), limit=1000000)

    def sample(self):
        before = self.device.irq_count
        result = self.device.sample()
        if before != self.device.irq_count:
            self.image.cpu.mem_write(self.QUEUE, bytes(self.device.cpu.mem_read(self.QUEUE, self.QUEUE_BYTES)))
        return result

    def state(self):
        queued = struct.unpack('<8H', self.image.cpu.mem_read(self.QUEUE + 4, 16))
        return [self.image.read(0xac85, '<B')[0], *self.image.read(0xdfc0, '<2B'),
                *queued[:4], *(offset // 12 for offset in queued[4:]),
                *(self.image.read(self.DESCRIPTORS + index * 26 + 12, '<h')[0] for index in range(len(self.samples)))]

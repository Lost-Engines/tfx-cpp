"""Capture-owned DOS files and an independent reader for native REC snapshots.

The DOS host keeps every byte in memory; it never opens a host filesystem path.
The reader normalises resource handles to names for comparing independently
allocated native/C++ resource registries.
"""
import struct
from native_reference import r


class MemoryFiles:
    def __init__(self, image):
        self.files = {}
        self.handles = {}
        self.next_handle = 7
        for address, method in ((0xcc3f8, self.create), (0xcc3e4, self.open),
                                (0xc8ff0, self.write), (0xc8f6c, self.read),
                                (0xcc44c, self.seek), (0xcc410, self.close)):
            image.intercept(address, 'Host capture-owned memory files at the DOS boundary; no installation is written.', method)

    def name(self, image):
        address = image.cpu.reg_read(r.UC_X86_REG_EAX)
        return bytes(image.cpu.mem_read(address, 256)).split(b'\0', 1)[0].decode('cp437').replace('\\', '/').lower()

    def result(self, image, value):
        image.cpu.reg_write(r.UC_X86_REG_EAX, value & 0xffffffff)
        image.return_from()

    def handle(self, image, name):
        handle = self.next_handle
        self.next_handle += 1
        self.handles[handle] = [name, 0]
        self.result(image, handle)

    def create(self, image):
        name = self.name(image)
        self.files[name] = bytearray()
        self.handle(image, name)

    def open(self, image):
        name = self.name(image)
        if name not in self.files:
            self.result(image, -1)
        else:
            self.handle(image, name)

    def write(self, image):
        handle = self.handles[image.cpu.reg_read(r.UC_X86_REG_EBX)]
        data = self.files[handle[0]]
        count = image.cpu.reg_read(r.UC_X86_REG_EDX)
        raw = bytes(image.cpu.mem_read(image.cpu.reg_read(r.UC_X86_REG_EAX), count))
        if handle[1] + count > len(data):
            data.extend(bytes(handle[1] + count - len(data)))
        data[handle[1]:handle[1] + count] = raw
        handle[1] += count
        self.result(image, count)

    def read(self, image):
        handle = self.handles[image.cpu.reg_read(r.UC_X86_REG_EBX)]
        count = image.cpu.reg_read(r.UC_X86_REG_EDX)
        raw = bytes(self.files[handle[0]][handle[1]:handle[1] + count])
        if raw:
            image.cpu.mem_write(image.cpu.reg_read(r.UC_X86_REG_EAX), raw)
        handle[1] += len(raw)
        self.result(image, len(raw))

    def seek(self, image):
        handle = self.handles[image.cpu.reg_read(r.UC_X86_REG_EBX)]
        offset = struct.unpack('<i', struct.pack('<I', image.cpu.reg_read(r.UC_X86_REG_EAX)))[0]
        origin = image.cpu.reg_read(r.UC_X86_REG_EDX)
        at = (0, handle[1], len(self.files[handle[0]]))[origin] + offset
        if at >= 0:
            handle[1] = at
        self.result(image, at)

    def close(self, image):
        self.handles.pop(image.cpu.reg_read(r.UC_X86_REG_EAX))
        self.result(image, 0)


def decode_recording(data):
    class Reader:
        def __init__(self, raw):
            self.data = raw
            self.at = 0

        def raw(self, count):
            if count < 0 or count > len(self.data) - self.at:
                raise ValueError('recording field exceeds file')
            result = self.data[self.at:self.at + count]
            self.at += count
            return result

        def values(self, kind, count=1):
            return list(struct.unpack(f'<{count}{kind}', self.raw(struct.calcsize(kind) * count)))

        def packed(self, count, fill):
            block = Reader(self.raw(self.values('H')[0]))
            output = bytearray()
            while len(output) < count:
                run, literals = block.values('B', 2)
                if run + literals > count - len(output):
                    raise ValueError('recording run exceeds field')
                output.extend(bytes([fill]) * run)
                output.extend(block.raw(literals))
            if block.at != len(block.data):
                raise ValueError('recording field has trailing compressed bytes')
            return output

    header = Reader(data)
    count = header.values('H')[0]
    size, trailer = header.values('I', 2)
    if size != len(data) or not 10 <= trailer <= size:
        raise ValueError('recording file offsets differ')
    dictionary = Reader(data[trailer:])
    resources = dictionary.values('H')[0]
    if not 2 <= resources <= 1000:
        raise ValueError('recording dictionary exceeds original table')
    handles = dictionary.values('H', resources)
    names = dictionary.raw(dictionary.values('I')[0]).split(b'\0')
    if len(names) != resources - 1 or names[-1] or dictionary.at != len(dictionary.data):
        raise ValueError('recording dictionary name count differs')
    # Native C5FC4 searches backwards; later duplicate handles take priority.
    names = ['', 'badshape.3', *[name.decode('cp437') for name in names[:-1]]]
    names = {handle: name.replace('\\', '/').rsplit('/', 1)[-1].lower().removesuffix('.3') for handle, name in zip(handles, names)}
    body = Reader(data[10:trailer])
    frames = []
    for _ in range(count):
        reserved = body.values('B', 8)
        angles = body.values('H', 3)
        models = body.values('H')[0]
        if models > 348:
            raise ValueError('recording exceeds original model queue')
        order = list(map(list, zip(body.values('h', models), body.values('H', models))))
        kinds = body.values('B', models)
        states = body.packed(models, 0)
        colours = body.values('B', models)
        scales = body.packed(models, 1)
        resources = body.values('H', models)
        rotations = [struct.unpack(f'<{models}H', body.packed(models * 2, 0)) for _ in range(3)]
        positions = [body.values('i', models) for _ in range(3)]
        parameters = body.packed(models * 8, 0)
        records = [[names.get(resources[i], 'badshape'), kinds[i], states[i], colours[i], scales[i],
                    *[axis[i] for axis in rotations], *[axis[i] for axis in positions],
                    *parameters[i * 8:i * 8 + 8]] for i in range(models)]
        frames.append({'reserved': reserved, 'angles': angles, 'order': order, 'models': records})
    if body.at != len(body.data):
        raise ValueError('recording has trailing frame data')
    return frames

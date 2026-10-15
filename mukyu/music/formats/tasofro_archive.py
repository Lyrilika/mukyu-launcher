
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

MASK = 0xffffffff
MODULI = (
    'c79a9e9bfbc20cb0c3e7ae274967628a78bbd12cb24df487c70935f701f82ee5493b836b8426aa429ae1ccee08a2151c42e748b19cce7ad9401a4dd436375c89',
    'ff657274616952202d2d20696f6b6e616c46207373656c4220646f472079614d088bf4755d78b1c8937f40ea34a585c11b8d631775982da817453131514f6e8d',
    'c643e09d355e981dbe636d3a5f840f49b8e853f54206373b3625cb65cedd688cf75d720ac047bdfa3b104cd22cfe7203104dd885153555a35aafc34a3bf3e237',
    'c44d6a2f05782c0fd75c8297176091dd6f836181d14e069b9437d2984de47bbf4260a78f88d6fdfee1f56a0b29cf0bed66f0ac4ed7ef96068bfa8e3348a3027d',
)


def name_hash(name, version):
    if version != 2:
        name = name.lower().replace('/', '\\')
    value = 0x811c9dc5
    for b in name.encode('cp932'):
        value = ((value * 0x1000193) ^ b) & MASK if version == 0 else ((value ^ b) * 0x1000193) & MASK
    return -value & MASK if version == 1 else value


def _exact(f, size):
    data = f.read(size)
    if len(data) != size:
        raise ValueError('Truncated music archive')
    return data


def _xor(a, b):
    return (int.from_bytes(a, 'little') ^ int.from_bytes(b, 'little')).to_bytes(len(a), 'little')


def _cga_decode(data, size, offset, start=0):

    out = bytearray(len(data))
    unpack = struct.Struct('<I').unpack_from
    pack = struct.Struct('<I').pack_into
    complete = len(data) - len(data) % 4
    seed = (size ^ offset) + start // 4
    for pos in range(0, len(data), 4):
        k = (seed + pos // 4) & MASK
        word = 0
        for _ in range(4):
            a = k * 0x5e4789c9
            b = (a >> 46) + (a >> 63)
            k = ((k - b * 0xadc8) * 0xbc8f + b * 0xfffff2b9) & MASK
            if k == 0 or k >= 0x80000000:
                k = (k + 0x7fffffff) & MASK
            word = ((word << 8) | (k & 255)) & MASK
        if pos < complete:
            pack(out, pos, unpack(data, pos)[0] ^ word)
        else:
            chunk = data[pos:]
            out[pos:] = (int.from_bytes(chunk, 'little') ^ (word & ((1 << (8 * len(chunk))) - 1))).to_bytes(len(chunk), 'little')
    return bytes(out)


@dataclass(frozen=True)
class Member:
    archive: str
    offset: int
    size: int
    version: int
    key: bytes = b''

    def read(self, start=0, length=None):
        if start < 0 or start > self.size:
            raise ValueError('Invalid archive member range')
        length = self.size - start if length is None else min(length, self.size - start)
        if length < 0:
            raise ValueError('Invalid archive member length')
        aligned = start - start % 16
        with open(self.archive, 'rb') as f:

            preceding = aligned - 4 if self.version == 1 and aligned else aligned
            f.seek(self.offset + preceding)
            raw = _exact(f, start + length - preceding)
        if self.version == 2:
            plain = _cga_decode(raw, self.size, self.offset, aligned)
        else:
            data = raw[aligned - preceding:]
            key = (self.key * ((len(data) + 15) // 16))[:len(data)]
            plain = _xor(data, key)
            if self.version == 1:
                feedback = (raw[:4] if aligned else self.key[:4]) + data
                plain = _xor(plain, feedback[:len(data)])
        return plain[start - aligned:start - aligned + length]

    def extract_ogg(self, path):
        chunk_size = 1024 * 1024
        data = self.read(0, min(chunk_size, self.size))
        if not data.startswith(b'OggS'):
            raise ValueError('The selected archive member is not Ogg audio')
        with open(path, 'wb') as output:
            output.write(data)
            offset = len(data)
            while offset < self.size:
                data = self.read(offset, min(chunk_size, self.size - offset))
                if not data:
                    raise ValueError('The selected archive member ended unexpectedly')
                output.write(data)
                offset += len(data)


class _RSAReader:
    def __init__(self, f):
        self.f = f
        self.modulus = None

    def read(self, size):
        result = bytearray()
        while size:
            n = min(32, size)
            block = _exact(self.f, 64)
            if block[32:] == bytes(32):
                payload = block[:32]
            else:
                payload = None
                for modulus in ([self.modulus] if self.modulus else [int(s, 16) for s in MODULI]):
                    decoded = pow(int.from_bytes(block, 'big'), 65537, modulus).to_bytes(64, 'big')
                    pad = 2
                    while pad < 63 and decoded[pad] == 255:
                        pad += 1
                    if decoded[:2] == b'\0\1' and pad >= 31 and decoded[pad] == 0 and 63 - pad >= n:
                        self.modulus = modulus
                        payload = decoded[pad + 1:]
                        break
                if payload is None:
                    raise ValueError('Unsupported TFPK header key or damaged archive')
            result.extend(payload[:n])
            size -= n
        return bytes(result)


def read_tfpk(path):
    path = str(Path(path).resolve())
    archive_size = Path(path).stat().st_size
    with open(path, 'rb') as f:
        magic = _exact(f, 5)
        if magic[:4] != b'TFPK' or magic[4] not in (0, 1):
            raise ValueError('Unsupported TFPK archive')
        version = magic[4]
        rsa = _RSAReader(f)
        dirs, = struct.unpack('<I', rsa.read(4))
        if dirs > archive_size // 64:
            raise ValueError('Invalid TFPK directory count')
        for _ in range(dirs):
            rsa.read(8)
        names = {}
        if dirs:
            compressed, original, blocks = struct.unpack('<III', rsa.read(12))
            if blocks > archive_size // 64 or original > 16 * 1024 * 1024 or compressed > blocks * 32:
                raise ValueError('Invalid TFPK name table')
            raw = rsa.read(blocks * 32)
            decoded = zlib.decompressobj().decompress(raw[:compressed], original + 1)
            if len(decoded) != original:
                raise ValueError('Invalid TFPK name table size')
            for name in decoded.split(b'\0'):
                if name:
                    name = name.decode('cp932').replace('\\', '/')
                    names[name_hash(name, version)] = name
        count, = struct.unpack('<I', rsa.read(4))
        if count > archive_size // 192:
            raise ValueError('Invalid TFPK member count')
        records = []
        for _ in range(count):
            size, offset = struct.unpack('<II', rsa.read(8))
            hashed = struct.unpack('<I', rsa.read(4 if version == 0 else 8)[:4])[0]
            key = rsa.read(16)
            if version == 1:
                words = struct.unpack('<4I', key)
                size ^= words[0]
                offset ^= words[1]
                hashed ^= words[2]
                key = struct.pack('<4I', *(-v & MASK for v in words))
            records.append((hashed, offset, size, key))
        base = f.tell()
    members = {}
    for hashed, offset, size, key in records:
        if base + offset + size > archive_size:
            raise ValueError('TFPK member extends beyond archive')
        members[hashed] = Member(path, base + offset, size, version, key)
    return version, members, names


def read_cga(path):
    path = str(Path(path).resolve())
    size = Path(path).stat().st_size
    if size < 32:
        raise ValueError('Truncated CGA archive')
    with open(path, 'rb') as f:
        f.seek(size - 32)
        footer = struct.unpack('<8I', _cga_decode(_exact(f, 32), 32, size - 32))
        count = footer[6]
        if footer[5] != 24 or footer[7] != 32 or count > (size - 32) // 24:
            raise ValueError('Unsupported CGA archive')
        offset = size - 32 - count * 24
        f.seek(offset)
        table = _cga_decode(_exact(f, count * 24), count * 24, offset)
    members = {}
    for hashed, pos, length in struct.iter_unpack('<QQQ', table):
        if pos + length > offset:
            raise ValueError('CGA member extends beyond archive')
        members[hashed] = Member(path, pos, length, 2)
    return 2, members, {}


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 7:
        raise SystemExit('Expected archive, offset, size, version, key, and output path')
    member = Member(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), bytes.fromhex(sys.argv[5]))
    member.extract_ogg(sys.argv[6])

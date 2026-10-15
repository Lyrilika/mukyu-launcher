import struct
import mmap
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HdiEntry:
    path: str
    is_dir: bool
    size: int
    first_cluster: int


class HdiFilesystem:

    _PHYSICAL_SECTOR_SIZES = (128, 256, 512, 1024, 2048, 4096)
    _LOGICAL_SECTOR_SIZES = (128, 256, 512, 1024, 2048, 4096)
    _FAT_MEDIA = {0xF0, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF}
    _FAT_MARKERS = (b"FAT12", b"FAT16")

    def __init__(self, path, preferred_suffixes=()):
        self.path = Path(path)
        with self.path.open('rb') as source:
            if source.seek(0, 2) < 0x20:
                raise ValueError("HDI image is too small")
            self._data = mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            (
                self.header_size,
                self.data_size,
                self.physical_bps,
                self.sectors_per_track,
                self.heads,
                self.cylinders,
            ) = self._read_hdi_header()
            self._preferred_suffixes = tuple(s.lower() for s in preferred_suffixes)
            self._entries = None
            self._parse_fat()
        except Exception:
            self._data.close()
            raise

    def _read_hdi_header(self):
        reserved, hdd_type, header_size, data_size, bps, spt, heads, cylinders = struct.unpack_from(
            "<8I", self._data, 0
        )
        del reserved, hdd_type
        if header_size < 0x20 or header_size > len(self._data):
            raise ValueError("Invalid HDI header size")
        if data_size <= 0 or header_size + data_size > len(self._data):
            raise ValueError("Invalid HDI data size")
        if bps not in self._PHYSICAL_SECTOR_SIZES:
            raise ValueError("Unsupported HDI physical sector size")
        if not (0 < spt <= 255 and 0 < heads <= 255 and 0 < cylinders <= 0xFFFF):
            raise ValueError("Invalid HDI geometry")
        return header_size, data_size, bps, spt, heads, cylinders

    @property
    def _disk_start(self):
        return self.header_size

    @property
    def _disk_end(self):
        return self.header_size + self.data_size

    def _read_disk_bytes(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.data_size:
            raise ValueError("HDI read outside disk data")
        start = self._disk_start + offset
        return self._data[start:start + length]

    def _read_absolute_bytes(self, offset, length):
        if offset < self._disk_start or length < 0 or offset + length > self._disk_end:
            raise ValueError("HDI read outside image")
        return self._data[offset:offset + length]

    def _pc98_partition_offsets(self):
        result = []
        if self.data_size < self.physical_bps * 2:
            return result


        table_length = min(max(512, self.physical_bps), self.data_size - self.physical_bps)
        table = self._read_disk_bytes(self.physical_bps, table_length)
        spt = self.sectors_per_track
        heads = self.heads
        total_sectors = self.data_size // self.physical_bps

        for index in range(min(16, len(table) // 32)):
            entry = table[index * 32:(index + 1) * 32]
            if not entry or all(b == 0 for b in entry):
                continue
            sys_id = entry[1]
            start_head = entry[8]
            start_sec = entry[9]
            start_cyl = struct.unpack_from("<H", entry, 10)[0]
            end_head = entry[12]
            end_sec = entry[13]
            end_cyl = struct.unpack_from("<H", entry, 14)[0]

            if start_head >= heads or end_head >= heads:
                continue
            if start_sec >= spt or end_sec >= spt:
                continue
            if end_cyl < start_cyl:
                continue

            start_lba = start_cyl * heads * spt + start_head * spt + start_sec
            end_lba = end_cyl * heads * spt + end_head * spt + end_sec
            if start_lba < 0 or start_lba >= total_sectors or end_lba < start_lba:
                continue

            result.append((start_lba * self.physical_bps, sys_id))
        return result

    @staticmethod
    def _parse_bpb(boot):
        if len(boot) < 0x24:
            return None
        bps = struct.unpack_from("<H", boot, 0x0B)[0]
        spc = boot[0x0D]
        reserved = struct.unpack_from("<H", boot, 0x0E)[0]
        fats = boot[0x10]
        root_entries = struct.unpack_from("<H", boot, 0x11)[0]
        total16 = struct.unpack_from("<H", boot, 0x13)[0]
        media = boot[0x15]
        spf = struct.unpack_from("<H", boot, 0x16)[0]
        total32 = struct.unpack_from("<I", boot, 0x20)[0]
        total = total16 or total32
        return {
            "bps": bps,
            "spc": spc,
            "reserved": reserved,
            "fats": fats,
            "root_entries": root_entries,
            "media": media,
            "spf": spf,
            "total": total,
        }

    @classmethod
    def _bpb_sane(cls, f, available_bytes):
        if not f:
            return False
        bps = f["bps"]
        spc = f["spc"]
        reserved = f["reserved"]
        fats = f["fats"]
        root_entries = f["root_entries"]
        spf = f["spf"]
        total = f["total"]
        if bps not in cls._LOGICAL_SECTOR_SIZES:
            return False
        if spc == 0 or spc > 128 or (spc & (spc - 1)) != 0:
            return False
        if reserved == 0 or reserved > 128:
            return False
        if fats == 0 or fats > 4:
            return False
        if root_entries == 0 or root_entries > 4096:
            return False
        if spf == 0 or spf > 512:
            return False
        if total <= 0:
            return False
        root_sectors = (root_entries * 32 + bps - 1) // bps
        first_data = reserved + fats * spf + root_sectors
        if first_data >= total:
            return False
        volume_bytes = total * bps
        if volume_bytes > available_bytes:
            return False
        if volume_bytes < first_data * bps:
            return False
        return True

    def _candidate_offsets(self):
        candidates = []
        seen = set()

        def add(offset, source):
            if self._disk_start <= self._disk_start + offset < self._disk_end:
                absolute = self._disk_start + offset
                if absolute not in seen:
                    seen.add(absolute)
                    candidates.append((absolute, source))

        add(0, "disk-start")

        for offset, sys_id in self._pc98_partition_offsets():
            add(offset, f"pc98-partition:0x{sys_id:02X}")

        cyl1 = self.sectors_per_track * self.heads * self.physical_bps
        if 0 < cyl1 < self.data_size:
            add(cyl1, "cylinder-1")

        for marker in self._FAT_MARKERS:
            pos = self._data.find(marker, self._disk_start, self._disk_end)
            while pos >= 0:
                if pos >= self._disk_start + 0x36:
                    add(pos - self._disk_start - 0x36, f"marker:{marker.decode()}")
                pos = self._data.find(marker, pos + 1, self._disk_end)

        return candidates

    def _score_candidate(self, absolute_offset, source):
        available = self._disk_end - absolute_offset
        if available < 512:
            return None
        boot = self._read_absolute_bytes(absolute_offset, min(4096, available))
        f = self._parse_bpb(boot)
        if not self._bpb_sane(f, available):
            return None

        bps = f["bps"]
        root_sectors = (f["root_entries"] * 32 + bps - 1) // bps
        fat_offset = absolute_offset + f["reserved"] * bps
        root_offset = fat_offset + f["fats"] * f["spf"] * bps
        data_offset = root_offset + root_sectors * bps
        volume_end = absolute_offset + f["total"] * bps
        if not (fat_offset < root_offset < data_offset <= volume_end <= self._disk_end):
            return None

        fat0 = self._read_absolute_bytes(fat_offset, min(bps, 64))
        media_score = 2 if fat0 and fat0[0] in self._FAT_MEDIA else 0

        root_raw = self._read_absolute_bytes(root_offset, root_sectors * bps)
        root_score = 0
        preferred_score = 0
        for pos in range(0, len(root_raw) - 31, 32):
            entry = root_raw[pos:pos + 32]
            first = entry[0]
            if first == 0x00:
                break
            if first == 0xE5:
                continue
            attr = entry[11]
            if attr == 0x0F or (attr & 0x08):
                continue
            if first < 0x20 and first != 0x05:
                continue
            base = entry[0:8].rstrip(b" ")
            ext = entry[8:11].rstrip(b" ")
            if not base:
                continue
            root_score += 1
            if self._preferred_suffixes:
                try:
                    ext_text = ext.decode("ascii", errors="ignore").lower()
                except Exception:
                    ext_text = ""
                if ext_text and any(ext_text == s.lstrip(".") for s in self._preferred_suffixes):
                    preferred_score += 1

        marker = boot[0x36:0x3B] if len(boot) >= 0x3B else b""
        marker_score = 3 if marker in self._FAT_MARKERS else 0
        signature_score = 1 if len(boot) >= 512 and boot[0x1FE:0x200] == b"\x55\xAA" else 0

        score = (
            preferred_score,
            root_score,
            media_score,
            marker_score,
            signature_score,
            -absolute_offset,
        )
        return {
            "score": score,
            "absolute_offset": absolute_offset,
            "source": source,
            "bps": bps,
            "spc": f["spc"],
            "reserved": f["reserved"],
            "fats": f["fats"],
            "root_entries": f["root_entries"],
            "spf": f["spf"],
            "total": f["total"],
            "fat_offset": fat_offset,
            "root_offset": root_offset,
            "root_sectors": root_sectors,
            "data_offset": data_offset,
            "volume_end": volume_end,
        }

    def _parse_fat(self):
        scored = []
        for absolute_offset, source in self._candidate_offsets():
            candidate = self._score_candidate(absolute_offset, source)
            if candidate is not None:
                scored.append(candidate)

        if not scored:
            raise ValueError("No readable FAT12/FAT16 filesystem found inside the PC-98 HDI image")

        found = max(scored, key=lambda c: c["score"])
        self.boot_offset = found["absolute_offset"]
        self.boot_source = found["source"]
        self.volume_bps = found["bps"]
        self.sectors_per_cluster = found["spc"]
        self.reserved_sectors = found["reserved"]
        self.fat_count = found["fats"]
        self.root_entries = found["root_entries"]
        self.sectors_per_fat = found["spf"]
        self.total_sectors = found["total"]
        self.fat_offset = found["fat_offset"]
        self.root_offset = found["root_offset"]
        self.root_sectors = found["root_sectors"]
        self.data_offset = found["data_offset"]
        self.volume_end = found["volume_end"]

        cluster_count = (self.volume_end - self.data_offset) // (
            self.sectors_per_cluster * self.volume_bps
        )
        if cluster_count < 4085:
            self.fat_type = 12
        elif cluster_count < 65525:
            self.fat_type = 16
        else:
            raise ValueError("PC-98 FAT volume is FAT32-sized; Touhou PC-98 media should be FAT12/FAT16")

    def _read_fat_entry(self, cluster):
        if self.fat_type == 16:
            pos = self.fat_offset + cluster * 2
            if pos + 2 > self.root_offset:
                return 0xFFFF
            return struct.unpack_from("<H", self._data, pos)[0]

        pos = self.fat_offset + (cluster * 3) // 2
        if pos + 2 > self.root_offset:
            return 0xFFF
        value = struct.unpack_from("<H", self._data, pos)[0]
        return (value >> 4) if (cluster & 1) else (value & 0x0FFF)

    def _cluster_chain(self, first_cluster):
        if first_cluster < 2:
            return []
        result = []
        seen = set()
        max_clusters = max(1, (self.volume_end - self.data_offset) // (
            self.sectors_per_cluster * self.volume_bps
        ))
        current = first_cluster
        while 2 <= current < 0xFFF8 and current not in seen and len(result) < max_clusters:
            seen.add(current)
            result.append(current)
            nxt = self._read_fat_entry(current)
            if self.fat_type == 12:
                if nxt >= 0xFF8:
                    break
            elif nxt >= 0xFFF8:
                break
            if nxt in (0, 1) or nxt == 0xFF7:
                break
            current = nxt
        return result

    @staticmethod
    def _decode_name(raw):
        raw = raw.rstrip(b" ")
        if not raw:
            return ""
        return raw.decode("cp932", errors="replace")

    def _dir_entries(self, raw, prefix=""):
        entries = []
        for pos in range(0, len(raw) - 31, 32):
            entry = raw[pos:pos + 32]
            first = entry[0]
            if first == 0x00:
                break
            if first == 0xE5:
                continue
            attr = entry[11]
            if attr == 0x0F or (attr & 0x08):
                continue
            if first < 0x20 and first != 0x05:
                continue

            base_raw = bytearray(entry[0:8])
            if base_raw and base_raw[0] == 0x05:
                base_raw[0] = 0xE5
            base = self._decode_name(bytes(base_raw))
            ext = self._decode_name(entry[8:11])
            if not base or base in (".", ".."):
                continue

            name = base if not ext else f"{base}.{ext}"
            cluster = struct.unpack_from("<H", entry, 26)[0]
            size = struct.unpack_from("<I", entry, 28)[0]
            is_dir = bool(attr & 0x10)
            path = f"{prefix}/{name}" if prefix else name
            entries.append(HdiEntry(path, is_dir, size, cluster))
        return entries

    def _read_directory(self, entry=None):
        if entry is None:
            raw = self._data[self.root_offset:self.root_offset + self.root_sectors * self.volume_bps]
            return self._dir_entries(raw)

        chunks = []
        cluster_size = self.sectors_per_cluster * self.volume_bps
        for cluster in self._cluster_chain(entry.first_cluster):
            pos = self.data_offset + (cluster - 2) * cluster_size
            chunks.append(self._data[pos:pos + cluster_size])
        return self._dir_entries(b"".join(chunks), entry.path)

    def entries(self):
        if self._entries is not None:
            return list(self._entries)
        result = []
        queue = [None]
        while queue:
            parent = queue.pop(0)
            for entry in self._read_directory(parent):
                result.append(entry)
                if entry.is_dir:
                    queue.append(entry)
        self._entries = result
        return list(result)

    def find(self, suffixes=()):
        wanted = {s.lower().lstrip(".") for s in suffixes}
        result = []
        for entry in self.entries():
            if entry.is_dir:
                continue
            if not wanted:
                result.append(entry)
                continue
            suffix = Path(entry.path).suffix.lower().lstrip(".")
            if suffix in wanted:
                result.append(entry)
        return result

    def read_file(self, path):
        target = path.replace("\\", "/").lstrip("/").lower()
        entry = next((e for e in self.entries() if e.path.lower() == target), None)
        if entry is None or entry.is_dir:
            raise FileNotFoundError(path)
        if entry.size == 0:
            return b""

        output = bytearray()
        remaining = entry.size
        cluster_size = self.sectors_per_cluster * self.volume_bps
        for cluster in self._cluster_chain(entry.first_cluster):
            pos = self.data_offset + (cluster - 2) * cluster_size
            chunk = self._data[pos:pos + cluster_size]
            if not chunk:
                break
            take = min(remaining, len(chunk))
            output.extend(chunk[:take])
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise IOError(f"Unexpected end of file while reading {path}")
        return bytes(output)

    def extract(self, path, destination):
        data = self.read_file(path)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

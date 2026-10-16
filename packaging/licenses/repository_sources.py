import argparse
import concurrent.futures
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "third_party/manifest.json"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def relative_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError(f"Path escapes its directory: {name}")
    return path


def source_files(record):
    path = relative_path(ROOT / "third_party", record["path"])
    if path.is_file():
        return [path]
    parts = sorted(path.parent.glob(path.name + ".part*"))
    expected = [path.with_name(f"{path.name}.part{index:03d}") for index in range(len(parts))]
    if not parts or parts != expected or any(not part.is_file() for part in parts):
        raise RuntimeError(f"Missing source archive or incomplete numbered parts: {path}")
    return [relative_path(ROOT / "third_party", str(part.relative_to(ROOT / "third_party"))) for part in parts]


def verify_source(record):
    paths = source_files(record)
    size = 0
    checksum = hashlib.sha256()
    for path in paths:
        if path.stat().st_size >= 100 * 1024 * 1024:
            raise RuntimeError(f"Source file exceeds GitHub's regular-file limit: {path}")
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(block)
                checksum.update(block)
    if size != record["size"] or checksum.hexdigest() != record["sha256"]:
        raise RuntimeError(f"Missing or changed dependency source: {record['path']}")


def catalog():
    data = json.loads(CATALOG.read_text())
    if data.get("schema") != 1:
        raise RuntimeError("Unsupported dependency source manifest")
    return data


def verify(platform):
    data = catalog()
    sources = {item["id"]: item for item in data["sources"]}
    selected = data["platforms"][platform]
    required = set(selected["sources"]) | set(data["common_sources"])
    for package in selected["packages"]:
        if package["source_required"]:
            key = f"{platform}/{package['source']}/{package['source_version']}"
            if key not in required:
                raise RuntimeError(f"No matching repository source for {package['name']} {package['version']}")
    for key in sorted(required):
        if key not in sources or not sources[key]["files"]:
            raise RuntimeError(f"Missing source record: {key}")
        for record in sources[key]["files"]:
            verify_source(record)
    if platform == "linux":
        for item in (data["appimage_runtime"], data["umu"]):
            path = relative_path(ROOT, item["path"])
            if not path.is_file() or digest(path) != item["sha256"]:
                raise RuntimeError(f"Bundled binary differs from its source manifest: {path}")
    print(f"Verified {len(required)} repository source records for {platform}")
    return data


def download_one(package, output):
    filename = package["filename"]
    if Path(filename).name != filename:
        raise RuntimeError(f"Invalid package filename: {filename}")
    target = output / filename
    if target.is_file() and digest(target) == package["sha256"]:
        return target
    url = package["url"]
    if not url.startswith("https://"):
        raise RuntimeError(f"Package URL must use HTTPS: {url}")
    for attempt in range(3):
        temporary = target.with_suffix(target.suffix + ".part")
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            if digest(temporary) != package["sha256"]:
                raise RuntimeError(f"Package checksum mismatch: {filename}")
            temporary.replace(target)
            return target
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2)


def fetch(platform, output):
    data = verify(platform)
    output.mkdir(parents=True, exist_ok=True)
    packages = data["platforms"][platform]["packages"]
    expected = {item["filename"] for item in packages}
    for path in output.iterdir():
        if path.is_file() and path.name not in expected:
            raise RuntimeError(f"Use an empty package directory; unexpected file: {path}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item: download_one(item, output), packages))
    print(f"Downloaded and verified {len(packages)} pinned {platform} packages")


def check_windows(database):
    expected = {item["name"]: item["version"] for item in verify("windows")["platforms"]["windows"]["packages"]}
    actual = {}
    for path in database.glob("*/desc"):
        fields = {}
        for block in path.read_text().split("\n\n"):
            lines = block.splitlines()
            if lines and lines[0].startswith("%"):
                fields[lines[0].strip("%")] = lines[1:]
        name = fields.get("NAME", [""])[0]
        if name.startswith("mingw-w64-x86_64-"):
            actual[name] = fields["VERSION"][0]
    if actual != expected:
        changed = sorted(name for name in actual.keys() | expected.keys() if actual.get(name) != expected.get(name))
        raise RuntimeError("Installed Windows packages differ from the repository source lock: " + ", ".join(changed))
    print("Installed Windows runtime matches the repository source lock")


def restore(output):
    data = catalog()
    for platform in data["platforms"]:
        verify(platform)
    for source in data["sources"]:
        groups = {}
        for item in source["files"]:
            groups.setdefault(item["original"], []).append(item)
        for name, parts in groups.items():
            target = relative_path(output, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as stream:
                for part in sorted(parts, key=lambda item: item.get("part", 0)):
                    for path in source_files(part):
                        with path.open("rb") as chunk:
                            shutil.copyfileobj(chunk, stream)
    print(f"Restored source archives and recipes to {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["verify", "fetch", "check-windows", "restore"])
    parser.add_argument("--platform", choices=["linux", "windows"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database", type=Path, default=Path("/var/lib/pacman/local"))
    args = parser.parse_args()
    if args.operation in ("verify", "fetch") and not args.platform:
        parser.error("--platform is required")
    if args.operation in ("fetch", "restore") and not args.output:
        parser.error("--output is required")
    if args.operation == "verify":
        verify(args.platform)
    elif args.operation == "fetch":
        fetch(args.platform, args.output)
    elif args.operation == "check-windows":
        check_windows(args.database)
    else:
        restore(args.output)


if __name__ == "__main__":
    main()

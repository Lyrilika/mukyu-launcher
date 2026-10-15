import argparse
import email
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url, destination, expected=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Mukyu-source-bundler"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    if expected and digest(temporary) != expected:
        temporary.unlink()
        raise RuntimeError(f"Source checksum mismatch: {url}")
    temporary.replace(destination)
    return {"url": url, "file": destination.name, "sha256": digest(destination)}


def pypi_source(name, version, output):
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=60) as response:
        metadata = json.load(response)
    candidates = [item for item in metadata["urls"] if item["packagetype"] == "sdist"]
    if not candidates:
        raise RuntimeError(f"No source distribution for {name} {version}")
    item = candidates[0]
    return download(item["url"], output / Path(item["filename"]).name, item["digests"]["sha256"])


def repository_source(url, revision, output, name):
    with tempfile.TemporaryDirectory(prefix="mukyu-source-") as temporary:
        repo = Path(temporary) / name
        run("git", "init", "-q", str(repo))
        run("git", "-C", str(repo), "remote", "add", "origin", url)
        run("git", "-C", str(repo), "fetch", "-q", "--depth", "1", "origin", revision)
        run("git", "-C", str(repo), "checkout", "-q", "--detach", "FETCH_HEAD")
        run("git", "-C", str(repo), "submodule", "update", "--init", "--recursive", "--depth", "1")
        commit = run("git", "-C", str(repo), "rev-parse", "HEAD")
        archive = output / f"{name}-{commit}.tar.gz"
        with tarfile.open(archive, "w:gz") as target:
            target.add(repo, arcname=name, filter=lambda item: None if ".git" in Path(item.name).parts else item)
    return {"repository": url, "revision": commit, "file": archive.name, "sha256": digest(archive)}


def common(output, platform):
    records = []
    own = output / f"mukyu-{platform}-source.tar.gz"
    entries = ["LICENSE", "README.md", "requirements.txt", "main.py", ".github", "mukyu", "assets", "scripts", "packaging", "tools/licenses", "tools/pc98/src", "tools/windows"]
    with tarfile.open(own, "w:gz") as archive:
        for entry in entries:
            path = ROOT / entry
            if path.exists():
                archive.add(path, arcname="mukyu-launcher/" + entry,
                            filter=lambda item: None if "__pycache__" in Path(item.name).parts or item.name.endswith((".pyc", ".dll", ".exe")) else item)
    records.append({"file": own.name, "sha256": digest(own)})
    for location in [ROOT / "build/dependency-sources", ROOT / "win-tools/build/dependency-sources"]:
        if location.exists():
            for source in location.iterdir():
                if source.is_file():
                    target = output / source.name
                    if source.resolve() != target.resolve():
                        if target.exists() and digest(target) != digest(source):
                            raise RuntimeError(f"Conflicting source files: {source.name}")
                        shutil.copy2(source, target)
    if not list(output.glob("98fmplayer-*.tar.gz")) or not list(output.glob("libx86emu-*.tar.gz")):
        raise RuntimeError("Build PC-98 helpers before collecting their matching sources")
    if platform == "linux":
        with zipfile.ZipFile(ROOT / "tools/umu/umu-run") as archive:
            packages = []
            for name in archive.namelist():
                if name.endswith(".dist-info/METADATA"):
                    metadata = email.message_from_bytes(archive.read(name))
                    packages.append((metadata["Name"], metadata["Version"]))
        for name, version in packages:
            if name.lower().replace("_", "-") == "umu-launcher":
                records.append(repository_source("https://github.com/Open-Wine-Components/umu-launcher.git", version, output, "umu-launcher"))
            else:
                records.append(pypi_source(name, version, output))
    (output / f"{platform}-launcher-sources.json").write_text(json.dumps(records, indent=2) + "\n")


def debian(debs, output):
    records = []
    sources = set()
    for deb in sorted(debs.glob("*.deb")):
        package = run("dpkg-deb", "-f", str(deb), "Package")
        version = run("dpkg-deb", "-f", str(deb), "Version")
        source = run("dpkg-deb", "-f", str(deb), "Source") or package
        match = re.fullmatch(r"([^ ]+)(?: \(([^)]+)\))?", source)
        if not match:
            raise RuntimeError(f"Unrecognized Debian Source field: {source}")
        source_name, source_version = match.group(1), match.group(2) or version
        sources.add((source_name, source_version))
        records.append({"package": package, "version": version, "source": source_name, "source_version": source_version, "binary_sha256": digest(deb)})
    if not records:
        raise RuntimeError("No binary Debian packages were supplied")
    for name, version in sorted(sources):
        subprocess.run(["apt-get", "source", "--download-only", "--only-source", f"{name}={version}"], cwd=output, check=True)
    (output / "linux-packages.json").write_text(json.dumps(records, indent=2) + "\n")


def msys(database, output, label):
    records = []
    sources = set()
    for path in sorted(database.glob("*/desc")):
        fields = {}
        for block in path.read_text().split("\n\n"):
            lines = block.splitlines()
            if lines and lines[0].startswith("%"):
                fields[lines[0].strip("%")] = lines[1:]
        name = fields.get("NAME", [""])[0]
        if not name.startswith("mingw-w64-x86_64-"):
            continue
        version = fields["VERSION"][0]
        base = fields.get("BASE", [name.replace("mingw-w64-x86_64-", "mingw-w64-", 1)])[0]
        sources.add((base, version.split(":", 1)[-1]))
        records.append({"package": name, "version": version, "source_base": base, "licenses": fields.get("LICENSE", [])})
    if not records:
        raise RuntimeError("No MINGW64 package records were found")
    with urllib.request.urlopen("https://repo.msys2.org/mingw/sources/", timeout=120) as response:
        available = set(re.findall(r'href="([^"/]+)"', response.read().decode()))
    for base, version in sorted(sources):
        stem = f"{base}-{version}.src.tar."
        matches = [name for name in available if name.startswith(stem) and name.endswith((".zst", ".gz", ".xz"))]
        if len(matches) != 1:
            raise RuntimeError(f"Matching MSYS2 source archive unavailable: {base} {version}")
        name = matches[0]
        if not (output / name).is_file():
            download("https://repo.msys2.org/mingw/sources/" + urllib.parse.quote(name), output / name)
    (output / f"windows-{label}-packages.json").write_text(json.dumps(records, indent=2) + "\n")


def appimage_runtime(output, binary, notices):
    with urllib.request.urlopen("https://api.github.com/repos/AppImage/type2-runtime/releases/latest", timeout=60) as response:
        release = json.load(response)
    commit = release["target_commitish"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("AppImage runtime release does not identify an exact source commit")
    asset = next(item for item in release["assets"] if item["name"] == "runtime-x86_64")
    checksum = asset.get("digest", "")
    if not checksum.startswith("sha256:"):
        raise RuntimeError("AppImage runtime release is missing its checksum")
    records = [download(asset["browser_download_url"], binary, checksum.split(":", 1)[1])]
    binary.chmod(0o755)
    if commit[:7] not in subprocess.check_output([str(binary.resolve()), "--appimage-version"], text=True, stderr=subprocess.STDOUT):
        raise RuntimeError("AppImage runtime binary and source revision do not match")
    records.append(repository_source("https://github.com/AppImage/type2-runtime.git", commit, output, "type2-runtime"))
    base = f"https://raw.githubusercontent.com/AppImage/type2-runtime/{commit}/"
    with urllib.request.urlopen(base + "scripts/common/install-dependencies.sh", timeout=60) as response:
        recipe = response.read().decode()
    dependencies = [
        ("https://github.com/libfuse/libfuse/releases/download/fuse-3.15.0/fuse-3.15.0.tar.xz", "70589cfd5e1cff7ccd6ac91c86c01be340b227285c5e200baa284e401eea2ca0"),
        ("https://github.com/vasi/squashfuse/archive/0.5.2.tar.gz", "db0238c5981dabbd80ee09ae15387f390091668ca060a7bc38047912491443d3"),
    ]
    for url, sha in dependencies:
        if url not in recipe or sha not in recipe:
            raise RuntimeError("AppImage runtime dependency recipe changed; update source collection before release")
        filename = "squashfuse-0.5.2.tar.gz" if url.endswith("0.5.2.tar.gz") else "fuse-3.15.0.tar.xz"
        records.append(download(url, output / filename, sha))
    texts = {
        "type2-runtime-LICENSE": base + "LICENSE",
        "libfuse-LGPL2.txt": "https://raw.githubusercontent.com/libfuse/libfuse/fuse-3.15.0/LGPL2.txt",
        "squashfuse-LICENSE": "https://raw.githubusercontent.com/vasi/squashfuse/0.5.2/LICENSE",
        "musl-COPYRIGHT": "https://git.musl-libc.org/cgit/musl/plain/COPYRIGHT?h=v1.2.5",
        "zstd-LICENSE": "https://raw.githubusercontent.com/facebook/zstd/v1.5.6/LICENSE",
        "zlib-LICENSE": "https://raw.githubusercontent.com/madler/zlib/v1.3.1/LICENSE",
        "mimalloc-LICENSE": "https://raw.githubusercontent.com/microsoft/mimalloc/v2.1.7/LICENSE",
    }
    for name, url in texts.items():
        records.append(download(url, notices / name))
    (output / "linux-appimage-runtime.json").write_text(json.dumps(records, indent=2) + "\n")


def pack(sources, destination, platform):
    destination.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in sources.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    if not files:
        raise RuntimeError("No corresponding source files were collected")
    (sources / "SHA256SUMS").write_text("".join(f"{digest(path)}  {path.name}\n" for path in files))
    basename = f"Mukyu-{platform}-sources.tar"
    for previous in destination.glob(basename + ".part*"):
        previous.unlink()
    with tempfile.TemporaryFile() as stream:
        with tarfile.open(fileobj=stream, mode="w|") as archive:
            archive.add(sources, arcname="sources")
        stream.seek(0)
        index = 0
        while True:
            data = stream.read(16 * 1024 * 1024)
            if not data:
                break
            part = destination / f"{basename}.part{index:03d}"
            with part.open("wb") as output:
                output.write(data)
                remaining = 1800 * 1024 * 1024 - len(data)
                while remaining:
                    block = stream.read(min(remaining, 16 * 1024 * 1024))
                    if not block:
                        break
                    output.write(block)
                    remaining -= len(block)
            index += 1
    parts = sorted(destination.glob(basename + ".part*"))
    (destination / f"Mukyu-{platform}-sources-SHA256SUMS.txt").write_text("".join(f"{digest(path)}  {path.name}\n" for path in parts))
    (destination / f"Mukyu-{platform}-sources-README.txt").write_text(
        "These source parts accompany the binary from the same workflow run/release.\n"
        "Download every numbered part and verify the SHA256SUMS file.\n"
        f"Linux/MSYS2: cat {basename}.part* > {basename}\n"
        f"Then: tar -xf {basename}\n"
        "The archive contains launcher code, build recipes, dependency sources,\n"
        "package version records and per-file checksums. Licenses remain with\n"
        "their respective sources. Use the included .github workflows to rebuild.\n"
        "Debian .dsc files describe complete upstream archives and packaging patches;\n"
        "MSYS2 .src.tar archives include PKGBUILD recipes and upstream sources.\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["common", "debian", "msys", "runtime", "pack"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform", choices=["linux", "windows"], default="linux")
    parser.add_argument("--debs", type=Path)
    parser.add_argument("--database", type=Path, default=Path("/var/lib/pacman/local"))
    parser.add_argument("--label", default="runtime")
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--notices", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.operation == "common": common(args.output, args.platform)
    elif args.operation == "debian": debian(args.debs, args.output)
    elif args.operation == "msys": msys(args.database, args.output, args.label)
    elif args.operation == "runtime": appimage_runtime(args.output, args.binary, args.notices)
    else: pack(args.sources, args.output, args.platform)


if __name__ == "__main__":
    main()

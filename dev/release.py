"""Builds the Smooth Brain release zip and uploads it to CurseForge.

    python SmoothBrain/dev/release.py build     tests, then dev/dist/SmoothBrain-<version>.zip
    python SmoothBrain/dev/release.py check     build, then show what an upload would send
    python SmoothBrain/dev/release.py upload    build, then send the zip to CurseForge

The zip holds one folder, SmoothBrain, with everything but dev/. The version
and the game version come from SmoothBrain.toc, the changelog from the section
of CHANGELOG.md for that version, the project from "## X-Curse-Project-ID".

check and upload need a CurseForge API token (authors.curseforge.com,
Settings, API tokens): in the environment as CF_API_KEY, or in
dev/curseforge.env as a line CF_API_KEY=... (dev/ never goes in the zip).
The token is never printed.

Options: --type release|beta|alpha (release), --yes (upload without asking),
--no-tests, --game-version-id N (when CurseForge's list can't be matched).
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile

DEV = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(DEV)
NAME = os.path.basename(ADDON)
DIST = os.path.join(DEV, "dist")
API = "https://wow.curseforge.com/api"
AGENT = "SmoothBrain-release/1.0"
LEFT_OUT = (".bak", ".zip", ".pyc")


def read_toc():
    """The "## Field: value" lines and the files the game loads."""
    fields, files = {}, []
    with open(os.path.join(ADDON, NAME + ".toc"), encoding="utf-8") as toc:
        for line in toc:
            line = line.strip()
            field = re.match(r"##\s*([^:]+?)\s*:\s*(.*)", line)
            if field:
                fields[field.group(1)] = field.group(2)
            elif line and not line.startswith("#"):
                files.append(line.replace("\\", "/"))
    return fields, files


def game_version_names(fields):
    """Interface 16001 is game version 1.60.1."""
    numbers = [int(number) for number in re.findall(r"\d+", fields.get("Interface", ""))]
    return [f"{n // 10000}.{n // 100 % 100}.{n % 100}" for n in numbers]


def changelog_for(version):
    path = os.path.join(ADDON, "CHANGELOG.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as log:
        section = re.search(r"^##\s+v?" + re.escape(version) + r"(?![\w.])[^\n]*\n(.*?)(?=^##\s|\Z)", log.read(), re.S | re.M)
    return section.group(1).strip() if section else None


def shipped_files():
    """Every file of the addon, as a path inside it, except dev/ and hidden or scratch files."""
    found = []
    for folder, folders, names in os.walk(ADDON):
        inside = os.path.relpath(folder, ADDON).replace("\\", "/")
        folders[:] = sorted(f for f in folders if not f.startswith(".") and not (inside == "." and f == "dev"))
        for name in sorted(names):
            if not name.startswith(".") and not name.lower().endswith(LEFT_OUT):
                found.append(name if inside == "." else inside + "/" + name)
    return found


def shipped_bytes(inside):
    with open(os.path.join(ADDON, inside), "rb") as source:
        data = source.read()
    if inside == "README.md":       # the tests live in dev/, which isn't shipped
        text = re.sub(r"\r?\n## Tests\r?\n.*?(?=\r?\n## |\Z)", "\n", data.decode("utf-8"), flags=re.S)
        data = text.rstrip().encode("utf-8") + b"\n"
    return data


def run_tests():
    result = subprocess.run([sys.executable, os.path.join(DEV, "test.py")], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        tail = "\n".join((result.stdout + "\n" + result.stderr).strip().splitlines()[-15:])
        sys.exit(f"The tests did not pass, so no zip was built:\n{tail}\n"
                 "(They need Python with lupa. --no-tests builds without them.)")
    print("tests:", result.stdout.strip().splitlines()[-1])


def build(tests=True):
    fields, loaded = read_toc()
    version = fields.get("Version") or sys.exit("SmoothBrain.toc has no ## Version")
    if tests:
        run_tests()
    files = shipped_files()
    missing = [name for name in loaded if name not in files]
    if missing:
        sys.exit("The .toc loads files that aren't there: " + ", ".join(missing))
    os.makedirs(DIST, exist_ok=True)
    path = os.path.join(DIST, f"{NAME}-{version}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for inside in files:
            stamp = time.localtime(os.path.getmtime(os.path.join(ADDON, inside)))[:6]
            entry = zipfile.ZipInfo(f"{NAME}/{inside}", date_time=stamp)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, shipped_bytes(inside))
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            sys.exit("The zip that was written doesn't read back.")
        print(f"{path}  ({os.path.getsize(path):,} bytes)")
        for entry in archive.infolist():
            print(f"    {entry.filename}  {entry.file_size:,}")
    return path, fields


def token():
    value = os.environ.get("CF_API_KEY", "").strip()
    path = os.path.join(DEV, "curseforge.env")
    if not value and os.path.exists(path):
        with open(path, encoding="utf-8-sig") as env:
            for line in env:
                found = re.match(r"\s*CF_API_KEY\s*=\s*(\S+)", line)
                if found:
                    value = found.group(1).strip("\"'")
    return value


def call(path, key, body=None, content_type=None):
    request = urllib.request.Request(API + path, data=body, headers={
        "X-Api-Token": key, "User-Agent": AGENT, "Accept": "application/json"})
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=180) as reply:
            return json.loads(reply.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        said = error.read().decode("utf-8", "replace").strip()[:600]
        hint = "  (403 usually means the token is wrong or isn't for this project's owner.)" if error.code == 403 else ""
        sys.exit(f"CurseForge answered {error.code} for {path}: {said}{hint}")
    except urllib.error.URLError as error:
        sys.exit(f"Could not reach CurseForge: {error.reason}")


def game_version_ids(key, names):
    known = call("/game/versions", key)
    ids = []
    for name in names:
        same = [version for version in known if version.get("name") == name]
        if len(same) != 1:
            near = sorted({version["name"] for version in known if version.get("name", "").startswith(name.rsplit(".", 1)[0])})
            sys.exit(f"CurseForge lists {len(same)} game versions called {name}"
                     + (f"; close ones: {', '.join(near)}" if near else "")
                     + ". Pass --game-version-id with the right one.")
        ids.append(same[0]["id"])
    return ids


def form(metadata, zip_path):
    edge = uuid.uuid4().hex
    with open(zip_path, "rb") as archive:
        packed = archive.read()
    body = b"".join([
        f'--{edge}\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n'.encode(),
        json.dumps(metadata).encode("utf-8"), b"\r\n",
        f'--{edge}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(zip_path)}"\r\n'
        f"Content-Type: application/zip\r\n\r\n".encode(),
        packed, b"\r\n", f"--{edge}--\r\n".encode()])
    return body, "multipart/form-data; boundary=" + edge


def option(name):
    if name in sys.argv:
        at = sys.argv.index(name)
        if at + 1 < len(sys.argv):
            return sys.argv[at + 1]
        sys.exit(f"{name} needs a value")
    return None


def release(send):
    path, fields = build(tests="--no-tests" not in sys.argv)
    version = fields["Version"]
    kind = option("--type") or "release"
    if kind not in ("release", "beta", "alpha"):
        sys.exit("--type is release, beta or alpha")
    project = fields.get("X-Curse-Project-ID")
    notes = changelog_for(version)
    names = game_version_names(fields)
    key = token()
    print(f"\nproject:       {project or 'none yet: add ## X-Curse-Project-ID to the .toc'}")
    print(f"file:          {os.path.basename(path)} as a {kind}")
    print(f"game version:  {', '.join(names)}")
    print("changelog:     " + (notes.replace("\n", "\n               ") if notes else f"none: CHANGELOG.md has no section for {version}"))
    print(f"token:         {'found' if key else 'none: set CF_API_KEY, or put CF_API_KEY=... in dev/curseforge.env'}")
    ready = bool(project and notes and key)
    forced = option("--game-version-id")
    ids = [int(forced)] if forced else (game_version_ids(key, names) if key else [])
    if ids:
        print(f"version ids:   {', '.join(map(str, ids))}")
    if not send:
        print("\nReady to upload." if ready else "\nNot ready to upload yet.")
        return
    if not ready:
        sys.exit("\nNot uploaded: see the lines above.")
    if "--yes" not in sys.argv and input(f"\nUpload {NAME} {version} to CurseForge project {project}? Type yes: ").strip().lower() != "yes":
        sys.exit("Not uploaded.")
    metadata = {"changelog": notes, "changelogType": "markdown", "displayName": f"{NAME}-{version}",
                "gameVersions": ids, "releaseType": kind}
    body, content_type = form(metadata, path)
    reply = call(f"/projects/{project}/upload-file", key, body, content_type)
    print(f"\nUploaded: CurseForge file {reply.get('id', reply)}. It appears on the project page once CurseForge has checked it.")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    if step == "build":
        build(tests="--no-tests" not in sys.argv)
    elif step in ("check", "upload"):
        release(send=step == "upload")
    else:
        print(__doc__)

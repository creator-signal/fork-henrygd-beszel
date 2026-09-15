#!/usr/bin/env python3
"""Validate the only Forgejo artifact allowed to feed a Beszel release."""
import argparse, hashlib, json, pathlib, re, sys, tarfile, zipfile

RUN = re.compile(r"[1-9][0-9]*\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
CHECKSUM = re.compile(r"[0-9a-f]{64}\Z")
FILES = {"beszel-agent-linux-amd64-qualification.tar.gz"}

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def safe_extract(archive, destination):
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        if names != FILES or any(name.startswith(("/", "\\")) or ".." in pathlib.PurePosixPath(name).parts for name in names):
            raise ValueError("Forgejo artifact has an unsafe or unexpected ZIP inventory")
        info = bundle.getinfo("beszel-agent-linux-amd64-qualification.tar.gz")
        if info.file_size > 64 * 1024 * 1024 or info.compress_size > 64 * 1024 * 1024:
            raise ValueError("Forgejo artifact exceeds the bounded release bundle limit")
        bundle.extract(info, destination)

def safe_extract_tar(archive, destination):
    allowed={"beszel-agent_linux_amd64.tar.gz","beszel-agent_linux_amd64.spdx.json","qualification.json","SHA256SUMS"}
    with tarfile.open(archive, "r:gz") as bundle:
        members=bundle.getmembers()
        if {m.name for m in members} != allowed or any(not m.isfile() or m.size > 64 * 1024 * 1024 or m.name.startswith('/') or '..' in pathlib.PurePosixPath(m.name).parts for m in members):
            raise ValueError("qualification tar has an unsafe or unexpected inventory")
        bundle.extractall(destination, members=members, filter='data')

def main(args):
    if not RUN.fullmatch(args.run_id): raise ValueError("Forgejo run ID is invalid")
    if not SHA.fullmatch(args.source_revision): raise ValueError("source revision is invalid")
    if not CHECKSUM.fullmatch(args.zip_sha256): raise ValueError("artifact checksum is invalid")
    if digest(args.archive) != args.zip_sha256: raise ValueError("Forgejo artifact ZIP checksum differs")
    output = pathlib.Path(args.output); output.mkdir(parents=True, exist_ok=True)
    safe_extract(args.archive, output)
    safe_extract_tar(output / "beszel-agent-linux-amd64-qualification.tar.gz", output)
    print(json.dumps({"runId": args.run_id, "bundle": "beszel-agent-linux-amd64-qualification.tar.gz"}))

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--run-id", required=True); p.add_argument("--source-revision", required=True); p.add_argument("--zip-sha256", required=True); p.add_argument("--archive", required=True); p.add_argument("--output", required=True)
    try: main(p.parse_args())
    except (OSError, ValueError, zipfile.BadZipFile) as e: print(f"Forgejo bundle rejected: {e}", file=sys.stderr); sys.exit(1)

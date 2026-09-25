#!/usr/bin/env python3
"""Fail-closed validation for Creator Signal Beszel Agent release manifests."""
import argparse
import hashlib
import json
import pathlib
import re
import sys

REQUIRED = {"schema", "releaseTag", "sourceRevision", "upstream", "artifacts", "provenance", "sbom", "qualification"}
CHECKSUM = re.compile(r"[0-9a-f]{64}\Z")
RUN = re.compile(r"[1-9][0-9]*\Z")

def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def validate(policy_path, manifest_path=None, directory=None):
    policy = json.loads(pathlib.Path(policy_path).read_text(encoding="utf-8"))
    if policy["manifestSchema"] != "creator-signal.beszel-agent-release/v1":
        raise ValueError("unexpected manifest schema")
    if policy["artifact"] != {"os": "linux", "arch": "amd64", "name": "beszel-agent_linux_amd64.tar.gz", "binaryPath": "beszel-agent"}:
        raise ValueError("release may contain only the Atlas Linux amd64 agent artifact")
    if manifest_path is None:
        return
    manifest = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    missing = REQUIRED.difference(manifest)
    if missing:
        raise ValueError("manifest is missing: " + ", ".join(sorted(missing)))
    if manifest["schema"] != policy["manifestSchema"]:
        raise ValueError("manifest schema mismatch")
    if not re.fullmatch(policy["downstreamTagPattern"], manifest["releaseTag"]):
        raise ValueError("release tag is not an explicit immutable downstream identity")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest["sourceRevision"]):
        raise ValueError("source revision must be an exact downstream commit SHA")
    if manifest["upstream"] != policy["upstream"]:
        raise ValueError("source identity does not match the governed upstream tag")
    if set(manifest["artifacts"]) != {"linux-amd64"}:
        raise ValueError("release must contain exactly one Linux amd64 artifact")
    artifact = manifest["artifacts"].get("linux-amd64")
    if not isinstance(artifact, dict) or artifact.get("name") != policy["artifact"]["name"]:
        raise ValueError("linux-amd64 artifact contract mismatch")
    if not CHECKSUM.fullmatch(artifact.get("sha256", "")) or not CHECKSUM.fullmatch(artifact.get("binarySha256", "")):
        raise ValueError("artifact checksum is invalid")
    if not isinstance(artifact.get("size"), int) or artifact["size"] <= 0:
        raise ValueError("artifact size is invalid")
    if manifest["provenance"] != {"type": policy["supplyChain"]["provenance"]}:
        raise ValueError("provenance contract mismatch")
    sbom = manifest["sbom"]
    if not isinstance(sbom, dict) or sbom.get("format") != policy["supplyChain"]["sbomFormat"] or sbom.get("name") != "beszel-agent_linux_amd64.spdx.json" or not CHECKSUM.fullmatch(sbom.get("sha256", "")):
        raise ValueError("SBOM contract mismatch")
    qualification = manifest["qualification"]
    required_qualification = {"sourceRevision": manifest["sourceRevision"], "runnerLabel": "native-linux-amd64", "nativeAgentSmoke": "pass", "hubHandshake": "pass", "metrics": "pass", "hubTag": policy["qualification"]["hubTag"], "hubRevision": policy["qualification"]["hubRevision"]}
    if not isinstance(qualification, dict) or any(qualification.get(key) != value for key, value in required_qualification.items()) or not RUN.fullmatch(str(qualification.get("forgejoRunId", ""))):
        raise ValueError("qualification contract mismatch")
    if directory:
        file = pathlib.Path(directory) / artifact["name"]
        if not file.is_file() or sha256(file) != artifact["sha256"]:
            raise ValueError("published artifact checksum mismatch")
        if file.stat().st_size != artifact["size"]:
            raise ValueError("published artifact size mismatch")
        sbom_file = pathlib.Path(directory) / sbom["name"]
        if not sbom_file.is_file() or sha256(sbom_file) != sbom["sha256"]:
            raise ValueError("published SBOM checksum mismatch")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="creator-signal/beszel-agent-release-policy.json")
    parser.add_argument("--manifest")
    parser.add_argument("--directory")
    args = parser.parse_args()
    try:
        validate(args.policy, args.manifest, args.directory)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"release control failed: {error}", file=sys.stderr)
        sys.exit(1)

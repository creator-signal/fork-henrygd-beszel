#!/usr/bin/env python3
"""Fail-closed validation for Creator Signal Beszel OCI release manifests."""
import argparse
import json
import pathlib
import re
import sys

CHECKSUM = re.compile(r"[0-9a-f]{64}\Z")


def validate(policy_path, manifest_path=None):
    policy = json.loads(pathlib.Path(policy_path).read_text(encoding="utf-8"))
    if policy["manifestSchema"] != "creator-signal.beszel-image-release/v1":
        raise ValueError("unexpected image manifest schema")
    if set(policy["images"]) != {"hub", "agent"}:
        raise ValueError("image policy must govern Hub and Agent only")
    if policy["platforms"] != ["linux/amd64", "linux/arm64"]:
        raise ValueError("image platform contract mismatch")
    if manifest_path is None:
        return
    manifest = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    required = {"schema", "releaseTag", "sourceRevision", "upstream", "images", "supplyChain"}
    missing = required.difference(manifest)
    if missing:
        raise ValueError("image manifest is missing: " + ", ".join(sorted(missing)))
    if manifest["schema"] != policy["manifestSchema"] or manifest["upstream"] != policy["upstream"]:
        raise ValueError("image source identity mismatch")
    if not re.fullmatch(policy["downstreamTagPattern"], manifest["releaseTag"]):
        raise ValueError("image release tag is not immutable")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest["sourceRevision"]):
        raise ValueError("image source revision must be a SHA")
    if manifest["supplyChain"] != {"provenance": policy["supplyChain"]["provenance"], "sbomFormat": policy["supplyChain"]["sbomFormat"]}:
        raise ValueError("image supply-chain contract mismatch")
    if set(manifest["images"]) != set(policy["images"]):
        raise ValueError("image manifest has an unexpected image set")
    for name, image in manifest["images"].items():
        expected = policy["images"][name]["repository"]
        if not isinstance(image, dict) or image.get("repository") != expected:
            raise ValueError(f"{name} repository mismatch")
        if not CHECKSUM.fullmatch(image.get("digest", "")):
            raise ValueError(f"{name} digest is invalid")
        if image.get("platforms") != policy["platforms"]:
            raise ValueError(f"{name} platform set mismatch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="creator-signal/beszel-image-release-policy.json")
    parser.add_argument("--manifest")
    args = parser.parse_args()
    try:
        validate(args.policy, args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"image release control failed: {error}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Assemble the governed Creator Signal Beszel agent release manifest.

The Forgejo native qualification job produces the agent archive, the SPDX
document and qualification.json. This script binds those outputs to the
reviewed upstream policy and emits creator-signal-beszel-agent-release.json.
It never downloads, selects or retags a release: the release tag, upstream
identity and qualification identity are explicit inputs or policy values.
"""
import argparse
import json
import pathlib
import re
import sys

import beszel_release_control

SHA = re.compile(r"[0-9a-f]{40}\Z")
RUN = re.compile(r"[1-9][0-9]*\Z")
SBOM_NAME = "beszel-agent_linux_amd64.spdx.json"


def assemble(policy, qualification, release_tag, forgejo_run_id, qualification_dir):
    if not re.fullmatch(policy["downstreamTagPattern"], release_tag):
        raise ValueError("release tag does not match the governed downstream pattern")
    if not RUN.fullmatch(str(forgejo_run_id)):
        raise ValueError("Forgejo run ID is invalid")

    source = qualification.get("sourceRevision", "")
    if not SHA.fullmatch(source):
        raise ValueError("qualification source revision is invalid")
    if qualification.get("runnerLabel") != "native-linux-amd64":
        raise ValueError("qualification runner label mismatch")
    for field in ("nativeAgentSmoke", "hubHandshake", "metrics"):
        if qualification.get(field) != "pass":
            raise ValueError(f"qualification {field} did not pass")

    directory = pathlib.Path(qualification_dir)
    archive = directory / policy["artifact"]["name"]
    if not archive.is_file() or archive.is_symlink():
        raise ValueError("qualification agent archive is missing")
    archive_sha256 = beszel_release_control.sha256(archive)
    if archive_sha256 != qualification.get("archiveSha256"):
        raise ValueError("archive checksum does not match qualification.json")

    sbom = directory / SBOM_NAME
    if not sbom.is_file() or sbom.is_symlink():
        raise ValueError("qualification SBOM is missing")
    sbom_sha256 = beszel_release_control.sha256(sbom)
    if sbom_sha256 != qualification.get("sbomSha256"):
        raise ValueError("SBOM checksum does not match qualification.json")

    binary_sha256 = qualification.get("binarySha256", "")
    if not beszel_release_control.CHECKSUM.fullmatch(binary_sha256):
        raise ValueError("qualification binary checksum is invalid")

    return {
        "schema": policy["manifestSchema"],
        "releaseTag": release_tag,
        "sourceRevision": source,
        "upstream": policy["upstream"],
        "artifacts": {
            "linux-amd64": {
                "name": policy["artifact"]["name"],
                "sha256": archive_sha256,
                "size": archive.stat().st_size,
                "binarySha256": binary_sha256,
            }
        },
        "provenance": {"type": policy["supplyChain"]["provenance"]},
        "sbom": {
            "format": policy["supplyChain"]["sbomFormat"],
            "name": SBOM_NAME,
            "sha256": sbom_sha256,
        },
        "qualification": {
            "sourceRevision": source,
            "runnerLabel": qualification["runnerLabel"],
            "nativeAgentSmoke": "pass",
            "hubHandshake": "pass",
            "metrics": "pass",
            "hubTag": policy["qualification"]["hubTag"],
            "hubRevision": policy["qualification"]["hubRevision"],
            "forgejoRunId": str(forgejo_run_id),
        },
    }


def main(args):
    policy = json.loads(pathlib.Path(args.policy).read_text(encoding="utf-8"))
    qualification = json.loads(
        (pathlib.Path(args.qualification_dir) / "qualification.json").read_text(encoding="utf-8")
    )
    manifest = assemble(
        policy,
        qualification,
        args.release_tag,
        args.forgejo_run_id,
        args.qualification_dir,
    )
    output = pathlib.Path(args.output)
    output.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    beszel_release_control.validate(args.policy, output, args.qualification_dir)
    print(json.dumps({"manifest": str(output), "releaseTag": manifest["releaseTag"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="creator-signal/beszel-agent-release-policy.json")
    parser.add_argument("--qualification-dir", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--forgejo-run-id", required=True)
    parser.add_argument("--output", required=True)
    try:
        main(parser.parse_args())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"agent release assembly failed: {error}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Sign the assembled Creator Signal Beszel agent release manifest.

Emits creator-signal-beszel-agent-release.signature.json with the exact
contract the downstream host promotion verifier expects: an Ed25519 signature
over the raw manifest bytes plus the SPKI DER SHA-256 of the signing public
key. The private key is a PKCS#8 PEM Ed25519 key supplied only by a protected
release secret; it is never read from the repository.
"""
import argparse
import base64
import hashlib
import json
import pathlib
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_private_key,
)


def build_signature(manifest_bytes, private_key):
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("release signing key must be Ed25519")
    public_der = private_key.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )
    manifest = json.loads(manifest_bytes)
    source_revision = manifest.get("sourceRevision", "")
    if not isinstance(source_revision, str) or len(source_revision) != 40:
        raise ValueError("manifest source revision is invalid")
    return {
        "algorithm": "Ed25519",
        "publicKeySha256": hashlib.sha256(public_der).hexdigest(),
        "manifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "signature": base64.b64encode(private_key.sign(manifest_bytes)).decode("ascii"),
        "sourceRevision": source_revision,
    }


def main(args):
    manifest_bytes = pathlib.Path(args.manifest).read_bytes()
    private_key = load_pem_private_key(
        pathlib.Path(args.private_key).read_bytes(), password=None
    )
    signature = build_signature(manifest_bytes, private_key)
    pathlib.Path(args.output).write_text(
        json.dumps(signature, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print(json.dumps({"signature": str(args.output), "publicKeySha256": signature["publicKeySha256"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--output", required=True)
    try:
        main(parser.parse_args())
    except (OSError, ValueError, TypeError) as error:
        print(f"agent release signing failed: {error}", file=sys.stderr)
        sys.exit(1)

import base64
import hashlib
import io
import json
import pathlib
import tarfile
import tempfile
import unittest

import beszel_release_control
from assemble_agent_release import assemble
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from sign_agent_release import build_signature

ROOT = pathlib.Path(__file__).parents[2]
POLICY = ROOT / "creator-signal/beszel-agent-release-policy.json"


def build_qualification(directory):
    directory = pathlib.Path(directory)
    archive = directory / "beszel-agent_linux_amd64.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo("beszel-agent")
        info.size = 4
        info.mode = 0o755
        bundle.addfile(info, io.BytesIO(b"agent"))
    sbom = directory / "beszel-agent_linux_amd64.spdx.json"
    sbom.write_text('{"spdxVersion":"SPDX-2.3"}\n', encoding="utf8")
    qualification = {
        "sourceRevision": "a" * 40,
        "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "binarySha256": "b" * 64,
        "sbomSha256": hashlib.sha256(sbom.read_bytes()).hexdigest(),
        "nativeAgentSmoke": "pass",
        "hubHandshake": "pass",
        "metrics": "pass",
        "runnerLabel": "native-linux-amd64",
    }
    (directory / "qualification.json").write_text(
        json.dumps(qualification) + "\n", encoding="utf8"
    )
    return qualification


class AgentReleaseTest(unittest.TestCase):
    def policy(self):
        return json.loads(POLICY.read_text(encoding="utf-8"))

    def test_assembles_and_validates_governed_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            qualification = build_qualification(directory)
            manifest = assemble(self.policy(), qualification, "v0.20.0-cs.1", "7", directory)
            output = pathlib.Path(directory) / "creator-signal-beszel-agent-release.json"
            output.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf8")
            beszel_release_control.validate(str(POLICY), output, directory)
            self.assertEqual(manifest["releaseTag"], "v0.20.0-cs.1")
            self.assertEqual(manifest["upstream"]["tag"], "v0.20.0")
            self.assertEqual(manifest["qualification"]["forgejoRunId"], "7")
            self.assertEqual(manifest["artifacts"]["linux-amd64"]["name"], "beszel-agent_linux_amd64.tar.gz")

    def test_rejects_wrong_release_tag_and_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            qualification = build_qualification(directory)
            with self.assertRaises(ValueError):
                assemble(self.policy(), qualification, "v0.18.7-cs.1", "7", directory)
            with self.assertRaises(ValueError):
                assemble(self.policy(), qualification, "v0.20.0-cs.1", "0", directory)

    def test_rejects_tampered_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            qualification = build_qualification(directory)
            qualification["archiveSha256"] = "0" * 64
            with self.assertRaises(ValueError):
                assemble(self.policy(), qualification, "v0.20.0-cs.1", "7", directory)

    def test_signature_matches_downstream_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            qualification = build_qualification(directory)
            manifest = assemble(self.policy(), qualification, "v0.20.0-cs.1", "7", directory)
            manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
            private_key = Ed25519PrivateKey.generate()
            signature = build_signature(manifest_bytes, private_key)
            self.assertEqual(signature["algorithm"], "Ed25519")
            self.assertEqual(signature["sourceRevision"], manifest["sourceRevision"])
            self.assertEqual(signature["manifestSha256"], hashlib.sha256(manifest_bytes).hexdigest())
            public_der = private_key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
            self.assertEqual(signature["publicKeySha256"], hashlib.sha256(public_der).hexdigest())
            private_key.public_key().verify(base64.b64decode(signature["signature"]), manifest_bytes)
            with self.assertRaises(Exception):
                private_key.public_key().verify(
                    base64.b64decode(signature["signature"]), manifest_bytes + b" "
                )

    def test_signature_rejects_non_ed25519_key(self):
        with tempfile.TemporaryDirectory() as directory:
            qualification = build_qualification(directory)
            manifest = assemble(self.policy(), qualification, "v0.20.0-cs.1", "7", directory)
            manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
            from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
            with self.assertRaises(ValueError):
                build_signature(manifest_bytes, generate_private_key(public_exponent=65537, key_size=2048))


if __name__ == "__main__":
    unittest.main()

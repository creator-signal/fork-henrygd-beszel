import json
import pathlib
import tempfile
import unittest
from beszel_release_control import validate

ROOT = pathlib.Path(__file__).parents[2]
POLICY = ROOT / "creator-signal/beszel-agent-release-policy.json"

class ReleaseControlTest(unittest.TestCase):
    def manifest(self):
        return {"schema":"creator-signal.beszel-agent-release/v1","releaseTag":"v0.18.7-cs.1","sourceRevision":"6e3fd90834309213aca32f2ff5fb0b027661c39a","upstream":{"repository":"https://github.com/henrygd/beszel.git","tag":"v0.18.7","revision":"6e3fd90834309213aca32f2ff5fb0b027661c39a"},"artifacts":{"linux-amd64":{"name":"beszel-agent_linux_amd64.tar.gz","sha256":"x","size":1,"binarySha256":"y"}},"provenance":{"type":"github-artifact-attestation"},"sbom":{"format":"spdx-json"},"qualification":{"hubTag":"v0.18.7"}}
    def test_policy_is_valid(self): validate(POLICY)
    def test_rejects_upstream_release_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "manifest.json"; data = self.manifest(); data["releaseTag"] = "v0.18.7"; path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): validate(POLICY, path)

if __name__ == "__main__": unittest.main()

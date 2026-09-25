import json
import pathlib
import tempfile
import unittest
from beszel_image_release_control import validate

ROOT = pathlib.Path(__file__).parents[2]
POLICY = ROOT / "creator-signal/beszel-image-release-policy.json"


class ImageReleaseControlTest(unittest.TestCase):
    def manifest(self):
        source = "41c5ccbb54cb9c58a6f6f428dded9418dd9c4307"
        image = lambda repository, digest: {"repository": repository, "digest": digest * 64, "platforms": ["linux/amd64", "linux/arm64"]}
        return {"schema": "creator-signal.beszel-image-release/v1", "releaseTag": "v0.18.7-cs.1", "sourceRevision": source, "upstream": {"repository": "henrygd/beszel", "tag": "v0.18.7", "revision": "6e3fd90834309213aca32f2ff5fb0b027661c39a"}, "images": {"hub": image("ghcr.io/creator-signal/beszel-hub", "a"), "agent": image("ghcr.io/creator-signal/beszel-agent", "b")}, "supplyChain": {"provenance": "slsa-buildkit", "sbomFormat": "spdx-json"}}

    def test_policy_is_valid(self):
        validate(POLICY)

    def test_rejects_mutable_release_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "manifest.json"
            data = self.manifest(); data["releaseTag"] = "latest"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): validate(POLICY, path)

    def test_rejects_single_platform_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "manifest.json"
            data = self.manifest(); data["images"]["agent"]["platforms"] = ["linux/amd64"]
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): validate(POLICY, path)


if __name__ == "__main__":
    unittest.main()

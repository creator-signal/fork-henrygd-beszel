import hashlib, io, pathlib, tarfile, tempfile, unittest, zipfile
from forgejo_bundle import main

class BundleTest(unittest.TestCase):
    def args(self, root, archive):
        return type('A',(),{'run_id':'7','source_revision':'a'*40,'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive':archive,'output':root/'out'})()
    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); archive=root/'bundle.zip'
            with zipfile.ZipFile(archive,'w') as z: z.writestr('../escape',b'x')
            with self.assertRaises(ValueError): main(self.args(root,archive))
    def test_rejects_extra_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); archive=root/'bundle.zip'
            with zipfile.ZipFile(archive,'w') as z: z.writestr('beszel-agent-linux-amd64-qualification.tar.gz',b'x'); z.writestr('extra',b'x')
            with self.assertRaises(ValueError): main(self.args(root,archive))
    def test_rejects_duplicate_zip_member(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); archive=root/'bundle.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('beszel-agent-linux-amd64-qualification.tar.gz',b'x')
                z.writestr('beszel-agent-linux-amd64-qualification.tar.gz',b'x')
            with self.assertRaises(ValueError): main(self.args(root,archive))
    def test_rejects_invalid_run_and_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); archive=root/'bundle.zip'
            with zipfile.ZipFile(archive,'w') as z: z.writestr('beszel-agent-linux-amd64-qualification.tar.gz',b'x')
            args=self.args(root,archive); args.run_id='0'
            with self.assertRaises(ValueError): main(args)
            args=self.args(root,archive); args.zip_sha256='0'*64
            with self.assertRaises(ValueError): main(args)
    def test_accepts_complete_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); agent=root/'agent.tar.gz'; inner=root/'inner.tar.gz'
            with tarfile.open(agent,'w:gz') as t:
                info=tarfile.TarInfo('beszel-agent'); info.size=1; info.mode=0o755; t.addfile(info,io.BytesIO(b'x'))
            with tarfile.open(inner,'w:gz') as t:
                for name in ('beszel-agent_linux_amd64.spdx.json','qualification.json','SHA256SUMS'):
                    info=tarfile.TarInfo(name); info.size=1; t.addfile(info,io.BytesIO(b'x'))
                t.add(agent,'beszel-agent_linux_amd64.tar.gz')
            outer=root/'bundle.zip'
            with zipfile.ZipFile(outer,'w') as z: z.write(inner,'beszel-agent-linux-amd64-qualification.tar.gz')
            main(self.args(root,outer)); self.assertTrue((root/'out'/'qualification.json').is_file())
    def test_rejects_duplicate_inner_tar_member(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); inner=root/'inner.tar.gz'; outer=root/'bundle.zip'
            with tarfile.open(inner,'w:gz') as t:
                for name in ('beszel-agent_linux_amd64.tar.gz','beszel-agent_linux_amd64.tar.gz','beszel-agent_linux_amd64.spdx.json','qualification.json','SHA256SUMS'):
                    info=tarfile.TarInfo(name); info.size=1; t.addfile(info,io.BytesIO(b'x'))
            with zipfile.ZipFile(outer,'w') as z: z.write(inner,'beszel-agent-linux-amd64-qualification.tar.gz')
            with self.assertRaises(ValueError): main(self.args(root,outer))

if __name__ == '__main__': unittest.main()

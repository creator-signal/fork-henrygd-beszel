import hashlib, pathlib, tempfile, unittest, zipfile, tarfile, io
from forgejo_bundle import main

class BundleTest(unittest.TestCase):
    def invoke(self, names):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); archive=root/'bundle.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for name in names: z.writestr(name,b'x')
            args=type('A',(),{'run_id':'1','source_revision':'a'*40,'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive':archive,'output':root/'out'})()
            return main,args
    def test_rejects_path_traversal(self):
        main,args=self.invoke(['../escape']);
        with self.assertRaises(ValueError): main(args)
    def test_rejects_extra_file(self):
        main,args=self.invoke(['beszel-agent-linux-amd64-qualification.tar.gz','extra']);
        with self.assertRaises(ValueError): main(args)
    def test_rejects_invalid_run_and_checksum(self):
        main,args=self.invoke(['beszel-agent-linux-amd64-qualification.tar.gz']); args.run_id='0'
        with self.assertRaises(ValueError): main(args)
    def test_accepts_complete_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); inner=root/'inner.tar.gz'
            with tarfile.open(inner,'w:gz') as t:
                for name in ('beszel-agent_linux_amd64.tar.gz','beszel-agent_linux_amd64.spdx.json','qualification.json','SHA256SUMS'):
                    info=tarfile.TarInfo(name); info.size=1; t.addfile(info,io.BytesIO(b'x'))
            outer=root/'bundle.zip'
            with zipfile.ZipFile(outer,'w') as z: z.write(inner,'beszel-agent-linux-amd64-qualification.tar.gz')
            args=type('A',(),{'run_id':'7','source_revision':'a'*40,'zip_sha256':hashlib.sha256(outer.read_bytes()).hexdigest(),'archive':outer,'output':root/'out'})()
            main(args); self.assertTrue((root/'out'/'qualification.json').is_file())
        main,args=self.invoke(['beszel-agent-linux-amd64-qualification.tar.gz']); args.zip_sha256='0'*64
        with self.assertRaises(ValueError): main(args)

if __name__ == '__main__': unittest.main()

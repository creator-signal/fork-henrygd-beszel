#!/usr/bin/env python3
"""Emit a deterministic SPDX 2.3 document using the pinned Go module graph."""
import argparse, hashlib, json, pathlib, subprocess

p=argparse.ArgumentParser(); p.add_argument('--binary',required=True); p.add_argument('--output',required=True); a=p.parse_args()
binary=pathlib.Path(a.binary); digest=hashlib.sha256(binary.read_bytes()).hexdigest()
modules=[]; decoder=json.JSONDecoder(); text=subprocess.check_output(['go','list','-m','-json','all'],text=True); index=0
while index < len(text):
    while index < len(text) and text[index].isspace(): index+=1
    if index >= len(text): break
    value,index=decoder.raw_decode(text,index); modules.append(value)
document={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'beszel-agent-linux-amd64','documentNamespace':f'https://github.com/creator-signal/fork-henrygd-beszel/releases/{digest}','creationInfo':{'creators':['Tool: creator-signal-generate-spdx'],'created':'2026-01-01T00:00:00Z'},'packages':[{'SPDXID':'SPDXRef-Package-'+str(i),'name':m['Path'],'versionInfo':m.get('Version','source'),'downloadLocation':'NOASSERTION','filesAnalyzed':False} for i,m in enumerate(modules)],'files':[{'SPDXID':'SPDXRef-File-agent','fileName':'beszel-agent','checksums':[{'algorithm':'SHA256','checksumValue':digest}]}]}
pathlib.Path(a.output).write_text(json.dumps(document,sort_keys=True,separators=(',',':'))+'\n',encoding='utf8')

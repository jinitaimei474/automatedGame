import json
import os
import subprocess
import sys
from pathlib import Path


def test_backend_protocol_is_utf8_even_with_windows_legacy_encoding(tmp_path):
    config=tmp_path/'config'/'settings.json'
    config.parent.mkdir()
    config.write_text('{"mockMode":true}',encoding='utf-8')
    repo=Path(__file__).resolve().parents[2]
    process=subprocess.run([sys.executable,'-m','automation.backend','--config',str(config)],
        cwd=repo,input=b'{"type":"get_manifest"}\n',capture_output=True,timeout=15,
        env={**os.environ,'PYTHONIOENCODING':'gbk','PYTHONUTF8':'0'})
    assert process.returncode==0,process.stderr
    events=[json.loads(line) for line in process.stdout.decode('utf-8').splitlines()]
    manifest=next(e['payload'] for e in events if e['type']=='manifest_updated')
    assert manifest['games'][0]['name']=='皇室战争'

"""Reproduce the synthetic-workflow/public-metadata demonstration."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from audit import Audit, fetch_public

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    workflow=root/'.github/workflows/demo.yml'
    workflow.parent.mkdir(parents=True)
    workflow.write_text('''jobs:
  demo:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v5
      - uses: anthropics/claude-code-action@v1.0.52
''',encoding='utf-8')
    audit=Audit(root,fetch_public)
    report=audit.scan()
    report['observed_at_utc']=datetime.now(timezone.utc).isoformat()
    report['sample_kind']='Synthetic workflow; real public metadata, no action executed'
    report['source_hashes']={url:hashlib.sha256(body.encode()).hexdigest() for url,body in audit.cache.items() if url.startswith('https://') and body is not None}
    Path(__file__).with_name('sample-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('workflows','review_count','unresolved_count','observed_at_utc')}))

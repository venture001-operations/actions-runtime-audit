"""Read-only Actions metadata inventory. Never imports or executes scanned code."""
import argparse
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

import yaml


class Audit:
    def __init__(self, root, fetch=None, max_depth=8, max_reads=80):
        self.root = Path(root).resolve()
        self.fetch = fetch
        self.max_depth = max_depth
        self.max_reads = max_reads
        self.cache = {}
        self.rows = []

    def row(self, chain, status, **details):
        self.rows.append(dict(chain=chain, status=status, **details))

    def read(self, location):
        if location in self.cache:
            return self.cache[location]
        if len(self.cache) >= self.max_reads:
            raise ValueError('read limit reached')
        self.cache[location] = None
        if location.startswith('https://'):
            if self.fetch is None:
                raise ValueError('public resolution disabled')
            value = self.fetch(location)
        else:
            path = Path(location).resolve()
            if not path.is_relative_to(self.root):
                raise ValueError('local path outside scanned root')
            if not path.is_file():
                return None
            if path.stat().st_size > 1_000_000:
                raise ValueError('file exceeds 1 MB')
            value = path.read_text(encoding='utf-8')
        self.cache[location] = value
        return value

    def reference(self, ref, chain, ancestors=()):
        chain = chain + [str(ref)]
        if not isinstance(ref, str) or '${{' in ref:
            self.row(chain, 'unresolved', reason='dynamic or non-string reference')
            return
        if ref in ancestors:
            self.row(chain, 'unresolved', reason='dependency cycle')
            return
        if len(ancestors) >= self.max_depth:
            self.row(chain, 'unresolved', reason='depth limit')
            return
        if ref.startswith('docker://'):
            self.row(chain, 'docker', reason='not a JavaScript action runtime')
            return
        if ref.startswith('./'):
            base = str((self.root / ref).resolve())
            candidates = [base] if ref.endswith(('.yml', '.yaml')) else [str(Path(base)/n) for n in ('action.yml','action.yaml')]
        else:
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(/[^@]*)?@([^\s]+)', ref)
            if not match or any(p in ('.', '..') for p in (match.group(3) or '').split('/')):
                self.row(chain, 'unresolved', reason='unsupported reference')
                return
            owner, repo, sub, revision = match.groups()
            path = (sub or '').strip('/')
            base = 'https://raw.githubusercontent.com/' + '/'.join(urllib.parse.quote(x, safe='') for x in (owner, repo, revision))
            suffixes = [path] if path.startswith('.github/workflows/') and path.endswith(('.yml','.yaml')) else [(path+'/' if path else '')+n for n in ('action.yml','action.yaml')]
            candidates = [base+'/'+urllib.parse.quote(s, safe='/') for s in suffixes]
        try:
            for location in candidates:
                source = self.read(location)
                if source is not None:
                    data = yaml.safe_load(source)
                    if not isinstance(data, dict):
                        raise ValueError('metadata is not a mapping')
                    self.document(data, chain, ancestors+(ref,), location)
                    return
            self.row(chain, 'unresolved', reason='metadata not found')
        except (ValueError, OSError, yaml.YAMLError, RecursionError):
            self.row(chain, 'unresolved', reason='read/parse/access limit; no runtime conclusion')

    def steps(self, steps, chain, ancestors):
        if not isinstance(steps, list):
            self.row(chain, 'unresolved', reason='steps is not a list')
            return
        for step in steps:
            if isinstance(step, dict) and 'uses' in step:
                self.reference(step['uses'], chain, ancestors)

    def document(self, data, chain, ancestors, source):
        runs = data.get('runs')
        if isinstance(runs, dict):
            runtime = runs.get('using')
            if runtime == 'composite':
                self.row(chain, 'composite', source=source)
                self.steps(runs.get('steps', []), chain, ancestors)
            elif runtime == 'docker':
                self.row(chain, 'docker', source=source)
            elif isinstance(runtime, str) and re.fullmatch(r'node\d+', runtime):
                self.row(chain, 'node24' if runtime == 'node24' else 'review_runtime', runtime=runtime, source=source)
            else:
                self.row(chain, 'unresolved', reason='unknown runs.using', source=source)
        elif isinstance(data.get('jobs'), dict):
            for name, job in data['jobs'].items():
                if not isinstance(job, dict):
                    self.row(chain+[str(name)], 'unresolved', reason='invalid job')
                    continue
                if 'uses' in job:
                    self.reference(job['uses'], chain+[str(name)], ancestors)
                else:
                    self.steps(job.get('steps', []), chain+[str(name)], ancestors)
        else:
            self.row(chain, 'unresolved', reason='neither action nor workflow metadata', source=source)

    def scan(self):
        directory = self.root / '.github/workflows'
        files = sorted(set(directory.glob('*.yml')) | set(directory.glob('*.yaml')))
        for file in files:
            chain = [file.relative_to(self.root).as_posix()]
            try:
                source = self.read(str(file))
                data = yaml.safe_load(source)
                if not isinstance(data, dict):
                    raise ValueError('workflow is not a mapping')
                self.document(data, chain, (), chain[0])
            except (ValueError, OSError, yaml.YAMLError, RecursionError):
                self.row(chain, 'unresolved', reason='workflow read/parse error')
        return dict(workflows=len(files), references=self.rows,
                    review_count=sum(x['status']=='review_runtime' for x in self.rows),
                    unresolved_count=sum(x['status']=='unresolved' for x in self.rows),
                    qualification='Declaration inventory only; does not prove failure, compatibility or complete runner readiness.')


def fetch_public(url):
    request = urllib.request.Request(url, headers={'User-Agent':'Venture-Actions-Runtime-Audit/0.1'})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if urllib.parse.urlparse(response.url).hostname != 'raw.githubusercontent.com':
                raise ValueError('unexpected redirect')
            content = response.read(1_000_001)
            if len(content)>1_000_000:
                raise ValueError('metadata exceeds 1 MB')
            return content.decode('utf-8')
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--resolve-public', action='store_true', help='Fetch public action metadata from raw.githubusercontent.com; sends action names/refs, no tokens')
    args = parser.parse_args()
    result = Audit(args.root, fetch_public if args.resolve_public else None).scan()
    print(json.dumps(result, indent=2))
    return 2 if not result['workflows'] or result['unresolved_count'] else 1 if result['review_count'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

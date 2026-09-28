import tempfile
import unittest
from pathlib import Path
from audit import Audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, value):
        target = self.root/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding='utf-8')

    def workflow(self, step):
        self.write('.github/workflows/ci.yml', 'jobs:\n  test:\n    steps:\n'+step)

    def test_application_node_is_not_action_runtime(self):
        self.workflow('      - uses: ./modern\n        with:\n          node-version: 20\n')
        self.write('modern/action.yml','runs:\n  using: node24\n')
        self.assertEqual(Audit(self.root).scan()['review_count'],0)

    def test_composite_nested_legacy(self):
        self.workflow('      - uses: ./wrapper\n')
        self.write('wrapper/action.yml','runs:\n  using: composite\n  steps:\n    - uses: ./legacy\n')
        self.write('legacy/action.yaml','runs:\n  using: node20\n')
        result=Audit(self.root).scan()
        self.assertEqual(result['review_count'],1)
        self.assertEqual(result['references'][-1]['chain'][-2:],['./wrapper','./legacy'])

    def test_remote_sha_and_reusable_workflow(self):
        self.write('.github/workflows/ci.yml','jobs:\n  reuse:\n    uses: org/repo/.github/workflows/reuse.yml@'+'a'*40+'\n')
        calls=[]
        def fetch(url):
            calls.append(url)
            if '/.github/workflows/' in url:
                return 'jobs:\n  build:\n    steps:\n      - uses: org/action@v1\n'
            return 'runs:\n  using: node20\n'
        result=Audit(self.root,fetch).scan()
        self.assertEqual(result['review_count'],1)
        self.assertIn('/'+'a'*40+'/',calls[0])

    def test_cycles_are_incomplete(self):
        self.workflow('      - uses: ./loop\n')
        self.write('loop/action.yml','runs:\n  using: composite\n  steps:\n    - uses: ./loop\n')
        self.assertEqual(Audit(self.root).scan()['unresolved_count'],1)

    def test_no_network_default_and_dynamic_ref(self):
        self.workflow('      - uses: org/action@v1\n      - uses: ${{ matrix.action }}\n')
        self.assertEqual(Audit(self.root).scan()['unresolved_count'],2)

    def test_path_escape_and_invalid_yaml(self):
        self.workflow('      - uses: ./../../outside\n')
        self.assertEqual(Audit(self.root).scan()['unresolved_count'],1)
        self.write('.github/workflows/ci.yml','jobs: [bad')
        self.assertEqual(Audit(self.root).scan()['unresolved_count'],1)

    def test_cache_and_read_bound(self):
        self.workflow('      - uses: org/action@v1\n      - uses: org/action@v1\n')
        calls=[]
        def fetch(url):
            calls.append(url)
            return 'runs:\n  using: node24\n'
        self.assertEqual(Audit(self.root,fetch).scan()['unresolved_count'],0)
        self.assertEqual(len(calls),1)
        self.assertEqual(Audit(self.root,fetch,max_reads=1).scan()['unresolved_count'],2)

    def test_comments_run_text_and_docker_not_false_positives(self):
        self.workflow('      # uses: org/old@v1\n      - run: |\n          echo "uses: org/old@v1"\n      - uses: docker://alpine:3\n')
        result=Audit(self.root).scan()
        self.assertEqual(len(result['references']),1)
        self.assertEqual(result['review_count'],0)


if __name__=='__main__':
    unittest.main()

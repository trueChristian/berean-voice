"""Keep archive CI read-only while the website owns source polling."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/archive-contract.yml'


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')
        self.steps = re.split(r'(?m)^      - name: ', self.text)[1:]

    def step(self, name):
        return next(step for step in self.steps if step.startswith(name + '\n'))

    def test_archive_checks_keep_read_only_event_checkout(self):
        self.assertRegex(self.text, r'(?m)^  pull_request:$')
        self.assertRegex(self.text, r'(?m)^  push:\n    branches: \[main\]$')
        self.assertRegex(self.text, r'(?m)^  workflow_dispatch:$')
        self.assertIn('permissions:\n  contents: read\n', self.text)
        self.assertNotIn('contents: write', self.text)
        self.assertNotIn('pull_request_target:', self.text)
        self.assertNotIn('workflow_run:', self.text)
        self.assertNotIn('secrets.', self.text)
        checkout = self.step('Check out the exact event revision')
        self.assertIn('fetch-depth: 0', checkout)
        self.assertIn('persist-credentials: false', checkout)
        self.assertNotIn('ref:', checkout)

    def test_validation_regressions_and_deterministic_checks_remain_required(self):
        required = {
            'Validate the entire source archive': 'python3 tools/archive.py validate',
            'Run contract regression tests': 'python3 -m unittest discover -s tests -v',
            'Verify deterministic build-only projections without changing source': 'git diff --exit-code',
        }
        for name, command in required.items():
            with self.subTest(name=name):
                step = self.step(name)
                self.assertIn(command, step)
                self.assertIn('set -euo pipefail', step)
                self.assertNotIn('continue-on-error:', step)
                self.assertNotRegex(step, r'(?m)^        if:')
        derive = self.step('Verify deterministic build-only projections without changing source')
        self.assertEqual(derive.count('python3 tools/archive.py derive'), 2)
        self.assertIn('cmp .build/derived/manifest.json', derive)
        self.assertIn('cmp .build/derived/navigation.json', derive)
        self.assertIn('git ls-files -- manifest.json navigation.json', derive)

    def test_both_display_export_contracts_and_evidence_remain(self):
        for name, command in (
            ('Verify the root-domain display export', 'export --output .build/root --base /'),
            ('Verify the GitHub Pages project-path display export', 'export --output .build/project --base /berean-voice/'),
        ):
            with self.subTest(name=name):
                step = self.step(name)
                self.assertIn('python3 tools/archive.py ' + command, step)
                self.assertIn('set -euo pipefail', step)
                self.assertNotRegex(step, r'(?m)^        if:')
                self.assertNotIn('continue-on-error:', step)
        evidence = self.step('Upload validation evidence only')
        self.assertIn('if: always()', evidence)
        self.assertIn('path: .build/validation/', evidence)

    def test_source_automation_does_not_notify_or_deploy_the_website(self):
        for path in (ROOT / '.github').rglob('*'):
            if path.suffix not in ('.yml', '.yaml', '.py'):
                continue
            text = path.read_text(encoding='utf-8')
            for obsolete in ('REMNANT_', 'remnant-content-updated', '.github/remnant',
                             'remnant-notif', 'remnant-export', 'repository-dispatch',
                             'repository_dispatch', '/dispatches', 'gh workflow run',
                             'actions/deploy-pages'):
                with self.subTest(path=path.relative_to(ROOT), obsolete=obsolete):
                    self.assertNotIn(obsolete, text)
        self.assertFalse((ROOT / '.github/remnant/dispatch.py').exists())
        self.assertFalse((ROOT / '.github/remnant/validate_event.py').exists())

    def test_website_setup_documentation_has_no_obsolete_prerequisites(self):
        self.assertFalse((ROOT / 'docs/remnant-notifications.md').exists())
        for path in [ROOT / 'README.md', *(ROOT / 'docs').rglob('*.md')]:
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('REMNANT_', text, str(path))
            self.assertNotIn('remnant-notifications.md', text, str(path))
        self.assertIn('hourly', (ROOT / 'README.md').read_text(encoding='utf-8'))

    def test_action_references_remain_immutable(self):
        for reference in re.findall(r'uses: (\S+)', self.text):
            self.assertRegex(reference, r'^[\w/-]+@[0-9a-f]{40}$')


if __name__ == '__main__':
    unittest.main()

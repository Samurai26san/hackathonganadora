"""Checks for deduplication, resource preservation, and safe repeat installs."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import agents


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / '.agents'
        self.sources = ('agents/current/skills', 'agents/older/skills')
        for source in self.sources:
            (self.root / source).mkdir(parents=True)
        (self.root / 'docs').mkdir()
        for name, value in [('ROOT', self.root), ('STATE', self.state), ('SOURCES', self.sources)]:
            patcher = patch.object(agents, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        graphify = self.root / 'agents/graphify-8/graphify'
        (graphify / 'skills/codex/references').mkdir(parents=True)
        (graphify / 'skill-codex.md').write_text(self.manifest('graphify'))

    @staticmethod
    def manifest(name, content='Workflow'):
        return f'---\nname: {name}\ndescription: Useful workflow.\n---\n\n{content}\n'

    def skill(self, source, name, content='Workflow'):
        folder = self.root / source / name
        folder.mkdir()
        (folder / 'SKILL.md').write_text(self.manifest(name, content))
        return folder

    def quiet_sync(self):
        with contextlib.redirect_stdout(io.StringIO()):
            agents.sync()

    def test_identical_packages_share_one_registration(self):
        self.skill(self.sources[0], 'sample')
        self.skill(self.sources[1], 'sample')
        records = agents.discover()
        self.assertEqual(len(records), 2)  # sample plus graphify
        self.assertEqual(len(next(r for r in records if r['name'] == 'sample')['duplicates']), 1)

    def test_resource_changes_keep_both_versions_and_repeat_safely(self):
        current = self.skill(self.sources[0], 'sample')
        older = self.skill(self.sources[1], 'sample')
        (current / 'reference.txt').write_text('new')
        (older / 'reference.txt').write_text('old')
        self.quiet_sync()
        self.quiet_sync()
        target = self.state / 'skills/sample-original'
        self.assertEqual(agents.metadata(target / 'SKILL.md')['name'], 'sample-original')
        self.assertEqual((target / 'reference.txt').read_text(), 'old')
        self.assertEqual(agents.metadata(older / 'SKILL.md')['name'], 'sample')
        with contextlib.redirect_stdout(io.StringIO()):
            agents.check()
        (target / 'SKILL.md').write_text(self.manifest('sample-original', 'corrupted'))
        with self.assertRaisesRegex(ValueError, 'Adaptador desactualizado'):
            agents.check()

    def test_existing_user_folder_is_preserved(self):
        self.skill(self.sources[0], 'sample')
        target = self.state / 'skills/sample'
        target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('user content')
        with self.assertRaisesRegex(ValueError, 'Destino ocupado'):
            self.quiet_sync()
        self.assertEqual((target / 'SKILL.md').read_text(), 'user content')

    def test_stale_catalog_is_detected(self):
        source = self.skill(self.sources[0], 'sample')
        self.quiet_sync()
        (source / 'SKILL.md').write_text(self.manifest('sample', 'changed'))
        with self.assertRaisesRegex(ValueError, 'Catálogo desactualizado'):
            agents.check()

    def test_mcp_config_preserves_unmanaged_settings_and_is_repeatable(self):
        config = self.root / '.codex/config.toml'
        config.parent.mkdir()
        config.write_text('model = "custom-model"\n')
        with contextlib.redirect_stdout(io.StringIO()):
            agents.configure_mcp()
            first = config.read_text()
            agents.configure_mcp()
        self.assertEqual(config.read_text(), first)
        self.assertTrue(first.startswith('model = "custom-model"\n'))
        self.assertEqual(first.count('[mcp_servers.'), 4)
        import tomllib
        self.assertEqual(len(tomllib.loads(first)['mcp_servers']), 4)

    def test_mcp_config_does_not_overwrite_existing_server(self):
        config = self.root / '.codex/config.toml'
        config.parent.mkdir()
        original = '[mcp_servers.graphify]\ncommand = "custom"\n'
        config.write_text(original)
        with self.assertRaisesRegex(ValueError, 'Ya existe configuración'):
            agents.configure_mcp()
        self.assertEqual(config.read_text(), original)

    def test_delegated_help_reaches_the_selected_tool(self):
        with patch('sys.argv', ['agents.py', 'ui', '--help']), patch.object(agents, 'run', return_value=0) as run:
            self.assertEqual(agents.main(), 0)
        self.assertEqual(run.call_args.args[0][-1], '--help')

    def test_graph_build_uses_local_extraction_and_excludes_collections(self):
        python = self.state / '.venv/bin/python'
        python.parent.mkdir(parents=True)
        python.touch()
        with patch('sys.argv', ['agents.py', 'graph-build']), patch.object(agents, 'run', return_value=0) as run:
            self.assertEqual(agents.main(), 0)
        command = run.call_args.args[0]
        self.assertEqual(command[1:4], ['extract', '.', '--code-only'])
        self.assertIn('agents/**', command)
        self.assertIn('.agents/**', command)


if __name__ == '__main__':
    unittest.main()

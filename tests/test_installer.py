import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).resolve().parents[1] / 'scripts/install.py')
i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)


class InstallerTests(unittest.TestCase):
    def test_config_migration_and_idempotence(self):
        original = 'require("default.hypr.omarchy")\nhl.plugin.load("/old/hyprtilekeeper.so")\n-- personal settings\n'
        result = i.managed_config(original, Path('/a path/plugin/hyprtilekeeper.so'))
        self.assertNotIn('/old/', result)
        self.assertIn('-- personal settings', result)
        self.assertEqual(result, i.managed_config(result, Path('/a path/plugin/hyprtilekeeper.so')))
        self.assertEqual(result.count(i.BEGIN), 1)

    def test_malformed_block(self):
        with self.assertRaises(RuntimeError):
            i.managed_config(i.BEGIN, Path('/plugin.so'))

    def install_fixture(self, fail=False, mismatch=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config/hypr/hyprland.lua'
            config.parent.mkdir(parents=True)
            original = '-- personal config\n'
            config.write_text(original)
            destination = root / 'data/hyprtilekeeper/hyprtilekeeper.so'
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b'old library')
            errors_calls = 0

            def run(*args):
                nonlocal errors_calls
                if args[0] == 'pkg-config':
                    return '-I/usr/include/hyprland'
                if args[0] == 'g++':
                    return '#define GIT_TAG "v0.56.2"\n#define GIT_COMMIT_HASH "test"'
                if args[-1] == 'version':
                    return json.dumps({'commit': 'different' if mismatch else 'test'})
                if args[-1] == 'configerrors':
                    errors_calls += 1
                    return 'bad config' if fail and errors_calls == 2 else ''
                if args[-1] == 'binds':
                    return '[]'
                return 'ok'

            def compile(args, **kwargs):
                Path(args[args.index('-o') + 1]).write_bytes(b'new library')

            with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data')}), patch.object(i.sys, 'argv', ['install.py']), patch.object(i, 'run', side_effect=run), patch.object(i.shutil, 'which', return_value='/usr/bin/tool'), patch.object(i.subprocess, 'run', side_effect=compile):
                if fail or mismatch:
                    with self.assertRaises(RuntimeError):
                        i.main()
                    self.assertEqual(config.read_text(), original)
                    self.assertEqual(destination.read_bytes(), b'old library')
                else:
                    i.main()
                    self.assertIn(i.BEGIN, config.read_text())
                    self.assertEqual(destination.read_bytes(), b'new library')
                    backups = list(config.parent.glob('tilekeeper-backup-*'))
                    self.assertEqual((backups[0] / 'hyprland.lua').read_text(), original)

    def test_install(self):
        self.install_fixture()

    def test_rollback(self):
        self.install_fixture(fail=True)

    def test_mismatched_headers_no_changes(self):
        self.install_fixture(mismatch=True)


if __name__ == '__main__':
    unittest.main()

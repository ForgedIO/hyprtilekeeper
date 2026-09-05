import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import install
import uninstall as u


class UninstallerTests(unittest.TestCase):
    def test_removal_preserves_user_edits(self):
        text = install.managed_config('-- original\n', Path('/plugin.so')) + '\n-- added later\n'
        cleaned = u.remove_block(text)
        self.assertIn('-- original', cleaned)
        self.assertIn('-- added later', cleaned)
        self.assertNotIn('hl.plugin', cleaned)
        self.assertEqual(u.remove_block(cleaned), cleaned)

    def test_malformed_markers_rejected(self):
        for text in (install.BEGIN, install.END, install.END + '\n' + install.BEGIN):
            with self.assertRaises(RuntimeError):
                u.remove_block(text)

    def fixture(self, offline=False, fail=False, manual=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / 'config/hypr/hyprland.lua'
            config.parent.mkdir(parents=True)
            plugin = root / 'data/hyprtilekeeper/hyprtilekeeper.so'
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b'library')
            (plugin.parent / 'unrelated.txt').write_text('keep')
            original = install.managed_config('-- personal\n', plugin) + '\n-- later change\n'
            config.write_text(original)
            if manual:
                (config.parent / 'bindings.lua').write_text('hl.plugin.tilekeeper.restore()\n')
            calls = []
            def run(*args):
                calls.append(args)
                if args[-2:] == ('plugin','list'):
                    return 'hyprtilekeeper' if len(calls) == 1 else 'no plugins loaded'
                if args[-1] == 'configerrors':
                    return 'configuration error' if fail else ''
                return 'ok'
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(root/'config'), 'XDG_DATA_HOME':str(root/'data'), 'HYPRLAND_INSTANCE_SIGNATURE':'test'}), patch.object(sys, 'argv', ['uninstall.py'] + (['--offline'] if offline else [])), patch.object(u, 'run', side_effect=run):
                if fail or manual:
                    with self.assertRaises(RuntimeError):
                        u.main()
                    self.assertEqual(config.read_text(), original)
                    self.assertTrue(plugin.exists())
                    if manual: self.assertEqual(calls, [])
                else:
                    u.main()
                    self.assertFalse(plugin.exists())
                    self.assertIn('-- later change', config.read_text())
                    self.assertTrue((plugin.parent/'unrelated.txt').exists())
                    if offline: self.assertEqual(calls, [])
                    else:
                        self.assertLess(calls.index(('hyprctl','eval','hl.config({general={layout="dwindle"}})')), calls.index(('hyprctl','plugin','unload',str(plugin))))
                    u.main()

    def test_live_order_and_repeat(self): self.fixture()
    def test_offline(self): self.fixture(offline=True)
    def test_validation_rollback(self): self.fixture(fail=True)
    def test_manual_config_refusal(self): self.fixture(manual=True)

if __name__ == '__main__': unittest.main()

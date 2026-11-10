"""Linux ion-dist.asar adapter tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "linux_frontend", ROOT / "scripts/patch_linux_frontend.py"
)
linux_frontend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linux_frontend)


LANGUAGE_MAP = (
    'var e={"en-US":{name:"English (United States)",'
    'localName:"English (United States)"},'
    '"id-ID":{name:"Indonesian (Indonesia)",'
    'localName:"Indonesia (Indonesia)"}};function t(t,n={}){}'
)


class LinuxFrontendTests(unittest.TestCase):
    def make_app(self, root: Path) -> tuple[Path, Path]:
        app = root / "Claude.app"
        assets = app / "Contents/Resources/ion-dist/assets/v1"
        assets.mkdir(parents=True)
        bundle = assets / "locale-map.js"
        bundle.write_text(LANGUAGE_MAP, encoding="utf-8")
        return app, bundle

    def test_adds_each_chinese_variant_to_language_picker(self):
        for language, names in linux_frontend.LANGUAGE_PICKER_NAMES.items():
            with self.subTest(language=language), tempfile.TemporaryDirectory() as tmp:
                app, bundle = self.make_app(Path(tmp))
                linux_frontend.patch_language_picker_metadata(app, language)
                text = bundle.read_text(encoding="utf-8")
                english_name, local_name = names
                marker = (
                    f'"{language}":{{name:"{english_name}",'
                    f'localName:"{local_name}"}}'
                )
                self.assertIn(marker, text)
                linux_frontend.patch_language_picker_metadata(app, language)
                self.assertEqual(bundle.read_text(encoding="utf-8").count(marker), 1)


if __name__ == "__main__":
    unittest.main()

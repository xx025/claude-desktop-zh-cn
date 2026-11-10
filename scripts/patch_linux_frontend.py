#!/usr/bin/env python3
"""Patch a Linux Claude Desktop ion-dist.asar working copy."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patch_claude_zh_cn as patcher  # noqa: E402


LANGUAGE_PICKER_NAMES = {
    "zh-CN": ("Chinese (Simplified, China)", "简体中文（中国）"),
    "zh-TW": ("Chinese (Traditional, Taiwan)", "繁體中文（台灣）"),
    "zh-HK": ("Chinese (Traditional, Hong Kong)", "繁體中文（香港）"),
}


def patch_language_picker_metadata(app: Path, language: str) -> None:
    assets = patcher.find_frontend_assets_dir(app)
    if assets is None:
        raise SystemExit("未找到语言选择器前端目录")
    try:
        english_name, local_name = LANGUAGE_PICKER_NAMES[language]
    except KeyError as exc:
        raise SystemExit(f"不支持的语言选择器语言：{language}") from exc
    marker = f'"{language}":{{name:"{english_name}",localName:"{local_name}"}}'
    if any(marker in path.read_text(encoding="utf-8") for path in assets.glob("*.js")):
        print("语言选择器已包含简体中文")
        return
    needle = (
        '"id-ID":{name:"Indonesian (Indonesia)",'
        'localName:"Indonesia (Indonesia)"}};function t('
    )
    replacement = (
        '"id-ID":{name:"Indonesian (Indonesia)",'
        'localName:"Indonesia (Indonesia)"},'
        + marker
        + '};function t('
    )
    matches = []
    for path in assets.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        if needle in text:
            matches.append((path, text))
    if len(matches) != 1:
        raise SystemExit(f"语言名称表匹配数量异常：{len(matches)}")
    path, text = matches[0]
    path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    print(f"已向语言选择器加入简体中文：{path.name}")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: patch_linux_frontend.py <ion-dist.asar> [language]")

    archive = Path(sys.argv[1]).resolve()
    language = sys.argv[2] if len(sys.argv) > 2 else "zh-CN"
    if not archive.is_file():
        raise SystemExit(f"未找到前端 ASAR: {archive}")

    patcher.update_electron_asar_integrity = lambda *args, **kwargs: False

    with tempfile.TemporaryDirectory(prefix="claude-linux-frontend-") as td:
        fake_app = Path(td) / "Claude.app"
        fake_resources = fake_app / "Contents/Resources"
        fake_resources.mkdir(parents=True)
        working_archive = fake_resources / "ion-dist.asar"
        shutil.copy2(archive, working_archive)

        target = patcher.prepare_frontend_target(fake_app)
        try:
            patcher.patch_language_whitelist(fake_app, language)
            patch_language_picker_metadata(fake_app, language)
            patcher.patch_hardcoded_frontend_strings(fake_app, language)
            patcher.patch_slash_command_menu(fake_app, language)
            patcher.patch_language_display_names(fake_app)
            patcher.merge_frontend_locale(fake_app, language)
            patcher.install_statsig_locale(fake_app, language)
            patcher.install_dynamic_locale(fake_app, language)
            patcher.finalize_frontend_target(fake_app, target)
        finally:
            patcher.cleanup_frontend_target(target)
        raw = patcher.read_frontend_entry(fake_app, f"i18n/{language}.json")
        if raw is None:
            raise SystemExit(f"补丁校验失败：ASAR 中缺少 i18n/{language}.json")
        data = json.loads(raw.decode("utf-8"))
        chinese = sum(
            1
            for value in data.values()
            if isinstance(value, str)
            and any("\u4e00" <= char <= "\u9fff" for char in value)
        )
        if chinese == 0:
            raise SystemExit("补丁校验失败：中文词条数量为 0")
        print(f"已验证前端 {language} 词库：{chinese}/{len(data)} 个中文词条")
        shutil.copy2(working_archive, archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

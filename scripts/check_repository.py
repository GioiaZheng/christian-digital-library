#!/usr/bin/env python3
"""阻止大型馆藏文件或禁止格式进入 Git 仓库。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_SIZE = 10 * 1024 * 1024
PROHIBITED_SUFFIXES = {
    ".7z",
    ".azw3",
    ".doc",
    ".docx",
    ".epub",
    ".gz",
    ".mobi",
    ".pdf",
    ".rar",
    ".tar",
    ".zip",
}


def tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def find_violations(paths: list[Path], max_size: int = MAX_FILE_SIZE) -> list[str]:
    violations: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        if path.suffix.lower() in PROHIBITED_SUFFIXES:
            violations.append(f"禁止格式：{path.name}")
        size = path.stat().st_size
        if size > max_size:
            violations.append(
                f"文件过大：{path.name}（{size / 1024 / 1024:.1f} MiB，限制 10 MiB）"
            )
    return violations


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        violations = find_violations(tracked_paths(ROOT))
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"仓库检查失败：{exc}")
        return 1
    if violations:
        print("发现不应提交到 GitHub 的文件：")
        for violation in violations:
            print(f"- {violation}")
        print("请将大型文件移出 Git 仓库，并只提交公开数据。")
        return 1
    print("仓库检查通过：没有受跟踪的禁止格式或超大文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

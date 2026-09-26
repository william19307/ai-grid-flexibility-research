#!/usr/bin/env python3
"""Create and verify a UTF-8 ZIP for the current paper package."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "outputs/research/current_paper_20260927"
TARGET = ROOT / "outputs/research/current_paper_20260927.zip"
TEMP = ROOT / "outputs/research/current_paper_20260927.zip.tmp"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if TEMP.exists():
        TEMP.unlink()
    files = sorted(path for path in PACKAGE.rglob("*") if path.is_file())
    with zipfile.ZipFile(TEMP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            arcname = f"{PACKAGE.name}/{path.relative_to(PACKAGE).as_posix()}"
            archive.write(path, arcname)

    manifest = json.loads((PACKAGE / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = {item["path"]: item["sha256"] for item in manifest["files"]}
    with zipfile.ZipFile(TEMP) as archive:
        names = archive.namelist()
        if len(names) != len(files) or len(names) != len(set(names)):
            raise SystemExit("ZIP entry count or uniqueness check failed")
        if f"{PACKAGE.name}/00_阅读说明.md" not in names:
            raise SystemExit("UTF-8 package guide name is missing from ZIP")
        bad_crc = archive.testzip()
        if bad_crc:
            raise SystemExit(f"ZIP CRC failure: {bad_crc}")
        for relative, expected_hash in expected.items():
            data = archive.read(f"{PACKAGE.name}/{relative}")
            if digest_bytes(data) != expected_hash:
                raise SystemExit(f"ZIP hash mismatch: {relative}")
        manifest_name = f"{PACKAGE.name}/MANIFEST.json"
        if archive.read(manifest_name) != (PACKAGE / "MANIFEST.json").read_bytes():
            raise SystemExit("ZIP manifest differs from package manifest")

    TEMP.replace(TARGET)
    print(f"wrote {TARGET} with {len(files)} verified files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Package text2drawio-skill with explicit, readable directory permissions."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "text2drawio-skill"
ARCHIVE = ROOT / "text2drawio-skill.zip"


def main() -> None:
    files = sorted(path for path in SKILL.rglob("*")
                   if path.is_file() and "__pycache__" not in path.parts
                   and path.name != ".DS_Store")
    directories = {SKILL}
    for path in files:
        directories.update(parent for parent in path.parents if parent == SKILL or SKILL in parent.parents)
    with ZipFile(ARCHIVE, "w") as archive:
        for path in sorted(directories):
            entry = ZipInfo(path.relative_to(ROOT).as_posix() + "/")
            entry.create_system = 3
            entry.external_attr = (0o40755 << 16) | 0x10
            entry.compress_type = ZIP_STORED
            archive.writestr(entry, b"")
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix(), compress_type=ZIP_DEFLATED)
    with ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        assert all((entry.external_attr >> 16) & 0o777 == 0o755
                   for entry in archive.infolist() if entry.is_dir())
    print(f"{ARCHIVE}: {len(files)} files, {len(directories)} readable directories")


if __name__ == "__main__":
    main()

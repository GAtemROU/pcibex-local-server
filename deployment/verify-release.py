#!/usr/bin/env python3
import io
import re
import sys
import tarfile
import zipfile
from pathlib import PurePosixPath


FORBIDDEN_PARTS = {
    ".env",
    ".git",
    "ibex",
    "node_modules",
    "tests",
    "fixtures",
    "venv",
    ".venv",
}


def path_parts(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Release contains an unsafe path: {name}")
    return tuple(part for part in path.parts if part not in (".", "/"))


def verify_release(path):
    with tarfile.open(path, "r:gz") as archive:
        archive_members = archive.getmembers()
        normalized_names = []
        for member in archive_members:
            parts = path_parts(member.name)
            if not parts:
                continue
            normalized_names.append("/".join(parts))
            if not member.isfile() and not member.isdir():
                raise ValueError(f"Release contains an unsupported file type: {member.name}")
            if parts[0] not in {"COMMIT", "backend", "frontend"}:
                raise ValueError(f"Release contains an unexpected path: {member.name}")
        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError("Release contains duplicate paths")
        members = [member for member in archive_members if member.isfile()]
        parts_by_name = {member.name: path_parts(member.name) for member in members}
        names = {"/".join(parts) for parts in parts_by_name.values()}

        required = {"COMMIT", "backend/requirements.lock"}
        missing = required - names
        if missing:
            raise ValueError(f"Release is missing required files: {sorted(missing)}")
        if not any(name.startswith("frontend/browser/") for name in names):
            raise ValueError("Release does not contain the Angular browser output")
        commit_file = next(
            member for member in members if "/".join(parts_by_name[member.name]) == "COMMIT"
        )
        with archive.extractfile(commit_file) as commit_contents:
            commit = commit_contents.read().decode("ascii").strip()
        if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit):
            raise ValueError("Release COMMIT must contain a hexadecimal commit identifier")

        wheels = [
            member
            for member in members
            if member.name.endswith(".whl")
            and "/".join(parts_by_name[member.name]).startswith("backend/")
            and "/".join(parts_by_name[member.name]).split("/")[1] != "wheelhouse"
        ]
        if len(wheels) != 1:
            raise ValueError("Release must contain exactly one backend wheel")
        runtime_wheels = [
            member
            for member in members
            if member.name.endswith(".whl")
            and "/".join(parts_by_name[member.name]).startswith("backend/wheelhouse/")
        ]
        if not runtime_wheels:
            raise ValueError("Release does not contain the locked backend runtime wheelhouse")

        for name, parts in parts_by_name.items():
            if any(
                part in FORBIDDEN_PARTS or part.endswith(".env")
                for part in parts
            ):
                raise ValueError(f"Release contains excluded path: {'/'.join(parts)}")

        with archive.extractfile(wheels[0]) as wheel_file:
            wheel_data = wheel_file.read()
        with zipfile.ZipFile(io.BytesIO(wheel_data)) as wheel:
            for name in wheel.namelist():
                parts = path_parts(name)
                if any(
                    part in FORBIDDEN_PARTS or part.endswith(".env")
                    for part in parts
                ):
                    raise ValueError(f"Backend wheel contains excluded path: {name}")
    return commit


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify-release.py RELEASE.tar.gz")
    verify_release(sys.argv[1])

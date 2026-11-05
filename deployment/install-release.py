#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

_VERIFIER_PATH = Path(__file__).with_name("verify-release.py")
_VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "pcibex_release_verifier",
    _VERIFIER_PATH,
)
if _VERIFIER_SPEC is None or _VERIFIER_SPEC.loader is None:
    raise ImportError(f"Could not load release verifier at {_VERIFIER_PATH}")
_VERIFIER = importlib.util.module_from_spec(_VERIFIER_SPEC)
_VERIFIER_SPEC.loader.exec_module(_VERIFIER)
path_parts = _VERIFIER.path_parts
verify_release = _VERIFIER.verify_release


MAX_RELEASE_SIZE = 2 * 1024 * 1024 * 1024


def verify_checksum(archive_path, checksum_path):
    fields = Path(checksum_path).read_text(encoding="ascii").strip().split()
    if not fields or not re.fullmatch(r"[0-9a-fA-F]{64}", fields[0]):
        raise ValueError("Checksum file must begin with a SHA-256 digest")

    digest = hashlib.sha256()
    with open(archive_path, "rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().lower() != fields[0].lower():
        raise ValueError("Release archive SHA-256 does not match the checksum file")


def safe_extract_release(archive_path, destination):
    destination = Path(destination)
    total_size = 0
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            parts = path_parts(member.name)
            if not member.isfile() and not member.isdir():
                raise ValueError(f"Unsupported archive member: {member.name}")
            total_size += member.size
            if total_size > MAX_RELEASE_SIZE:
                raise ValueError("Release archive exceeds the extraction size limit")
            target = destination.joinpath(*parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
                target.chmod(0o755)
                continue

            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read archive member: {member.name}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o644)


def run_command(command, cwd=None):
    subprocess.run(command, cwd=cwd, check=True)


def wait_for_health(url, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if (
                    response.status == 200
                    and json.loads(response.read()).get("status") == "ok"
                ):
                    return True
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(2)
    return False


def atomic_symlink(target, link):
    link = Path(link)
    link.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    if (link.exists() or link.is_symlink()) and not link.is_symlink():
        raise ValueError(f"Refusing to replace a non-symlink path: {link}")
    temporary_link = link.with_name(f".{link.name}.next-{uuid.uuid4().hex}")
    try:
        os.symlink(str(target), temporary_link)
        os.replace(temporary_link, link)
    finally:
        if temporary_link.is_symlink():
            temporary_link.unlink()


def current_release_target(current_link):
    current_link = Path(current_link)
    if not current_link.is_symlink():
        if current_link.exists():
            raise ValueError(
                f"{current_link} must be absent or a symlink; migrate the existing "
                "installation to a versioned release before using this installer"
            )
        return None
    target = Path(os.readlink(current_link))
    if not target.is_absolute():
        target = current_link.parent / target
    return target.resolve()

def rollback_release(
    install_root,
    target_commit,
    service="pcibex.service",
    health_url="http://127.0.0.1:3001/healthz",
    run=run_command,
    check_health=wait_for_health,
):
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", target_commit):
        raise ValueError("Rollback target must be a hexadecimal commit identifier")
    install_root = Path(install_root).expanduser().resolve()
    releases_root = install_root / "releases"
    target_release = releases_root / target_commit
    current_link = install_root / "current"
    previous_release = current_release_target(current_link)

    if not target_release.is_dir():
        raise ValueError(f"Rollback release does not exist: {target_release}")
    if previous_release is None:
        raise ValueError("There is no active release to roll back from")
    if not (target_release / ".venv" / "bin" / "hypercorn").is_file():
        raise ValueError(f"Rollback release is missing its backend environment: {target_release}")

    atomic_symlink(target_release, current_link)
    try:
        run(["systemctl", "restart", service])
        if not check_health(health_url):
            raise RuntimeError(f"Backend health check failed at {health_url}")
    except Exception as rollback_error:
        try:
            atomic_symlink(previous_release, current_link)
            run(["systemctl", "restart", service])
        except Exception as recovery_error:
            raise RuntimeError(
                f"Rollback failed ({rollback_error}); restoring the prior active "
                f"release also failed ({recovery_error}). Current link: {current_link}"
            ) from rollback_error
        raise RuntimeError(
            f"Rollback health check failed; the previous active release was restored: "
            f"{rollback_error}"
        ) from rollback_error

    print(f"Restored release {target_commit} at {current_link}")
    print(f"Health check passed: {health_url}")
    return target_release


def install_release(
    archive_path,
    checksum_path,
    install_root,
    python_executable="python3.12",
    service="pcibex.service",
    health_url="http://127.0.0.1:3001/healthz",
    run=run_command,
    check_health=wait_for_health,
):
    archive_path = Path(archive_path)
    checksum_path = Path(checksum_path)
    install_root = Path(install_root).expanduser().resolve()

    verify_checksum(archive_path, checksum_path)
    commit = verify_release(archive_path)
    releases_root = install_root / "releases"
    current_link = install_root / "current"
    previous_release = current_release_target(current_link)
    release_path = releases_root / commit
    if release_path.exists():
        raise ValueError(f"Release directory already exists: {release_path}")

    releases_root.mkdir(parents=True, exist_ok=True, mode=0o755)
    release_path.mkdir(mode=0o755)
    activated = False
    try:
        safe_extract_release(archive_path, release_path)
        venv_python = release_path / ".venv" / "bin" / "python"
        run([python_executable, "-m", "venv", str(release_path / ".venv")])
        run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(release_path / "backend" / "wheelhouse"),
                "-r",
                str(release_path / "backend" / "requirements.lock"),
            ]
        )
        backend_wheel = next((release_path / "backend").glob("*.whl"))
        run([str(venv_python), "-m", "pip", "install", "--no-deps", str(backend_wheel)])
        run(
            [
                str(venv_python),
                "-c",
                "from pcibex_server.server import app; assert app is not None",
            ],
            cwd=release_path,
        )

        atomic_symlink(release_path, current_link)
        activated = True
        try:
            run(["systemctl", "restart", service])
            if not check_health(health_url):
                raise RuntimeError(f"Backend health check failed at {health_url}")
        except Exception as deployment_error:
            try:
                if previous_release is None:
                    if current_link.is_symlink():
                        current_link.unlink()
                    run(["systemctl", "stop", service])
                else:
                    atomic_symlink(previous_release, current_link)
                    run(["systemctl", "restart", service])
            except Exception as rollback_error:
                raise RuntimeError(
                    f"Deployment failed ({deployment_error}); rollback also failed "
                    f"({rollback_error}). Current link: {current_link}"
                ) from deployment_error
            raise RuntimeError(
                f"Deployment failed and the previous release was restored: "
                f"{deployment_error}"
            ) from deployment_error
    except Exception:
        if not activated or current_release_target(current_link) != release_path:
            shutil.rmtree(release_path, ignore_errors=True)
        raise

    print(f"Activated release {commit} at {current_link}")
    print(f"Health check passed: {health_url}")
    return release_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify and atomically install a PCIbex release archive."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--archive", type=Path)
    target.add_argument("--rollback-to", metavar="COMMIT")
    parser.add_argument("--checksum", type=Path)
    parser.add_argument("--install-root", type=Path, default=Path("/opt/pcibex"))
    parser.add_argument("--python", default="python3.12", dest="python_executable")
    parser.add_argument("--service", default="pcibex.service")
    parser.add_argument(
        "--health-url",
        default="http://127.0.0.1:3001/healthz",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        args = parse_args()
        if args.rollback_to:
            if args.checksum:
                raise ValueError("--checksum is only used with --archive")
            rollback_release(
                args.install_root,
                args.rollback_to,
                service=args.service,
                health_url=args.health_url,
            )
        else:
            if not args.checksum:
                raise ValueError("--checksum is required with --archive")
            install_release(
                args.archive,
                args.checksum,
                args.install_root,
                python_executable=args.python_executable,
                service=args.service,
                health_url=args.health_url,
            )
    except Exception as error:
        print(f"Release installation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

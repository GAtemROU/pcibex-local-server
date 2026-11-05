import hashlib
import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


DEPLOYMENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOYMENT_DIR))

VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_release",
    DEPLOYMENT_DIR / "verify-release.py",
)
verify_release = importlib.util.module_from_spec(VERIFY_SPEC)
sys.modules["verify_release"] = verify_release
VERIFY_SPEC.loader.exec_module(verify_release)
INSTALLER_SPEC = importlib.util.spec_from_file_location(
    "install_release",
    DEPLOYMENT_DIR / "install-release.py",
)
install_release = importlib.util.module_from_spec(INSTALLER_SPEC)
INSTALLER_SPEC.loader.exec_module(install_release)


def make_wheel():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as wheel:
        wheel.writestr("pcibex_server/__init__.py", "")
    return output.getvalue()


def make_release(path, extra_member=None):
    files = {
        "./COMMIT": b"1234567890abcdef\n",
        "./backend/requirements.lock": b"quart==0.22.0\n",
        "./backend/pcibex_server-0.1.0-py3-none-any.whl": make_wheel(),
        "./backend/wheelhouse/quart-0.22.0-py3-none-any.whl": make_wheel(),
        "./frontend/browser/index.html": b"<!doctype html>",
    }
    if extra_member:
        files.update(extra_member)
    with tarfile.open(path, "w:gz") as archive:
        for name, data in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))

    checksum = path.with_suffix(path.suffix + ".sha256")
    checksum.write_text(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n",
        encoding="ascii",
    )
    return checksum


class ReleaseVerificationTests(unittest.TestCase):
    def test_accepts_complete_release_and_returns_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "release.tar.gz"
            make_release(archive)
            self.assertEqual(verify_release.verify_release(archive), "1234567890abcdef")

    def test_rejects_parent_directory_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "release.tar.gz"
            make_release(archive, {"./../outside": b"not safe"})
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                verify_release.verify_release(archive)

    def test_rejects_symbolic_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "release.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                link = tarfile.TarInfo("./frontend/browser/index.html")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                output.addfile(link)
            with self.assertRaisesRegex(ValueError, "unsupported file type"):
                verify_release.verify_release(archive)

    def test_rejects_a_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "release.tar.gz"
            checksum = make_release(archive)
            archive.write_bytes(archive.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "does not match"):
                install_release.verify_checksum(archive, checksum)


class InstallerTests(unittest.TestCase):
    def test_health_check_accepts_compact_json(self):
        class HealthResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def read(self):
                return b'{"status":"ok"}'

        with patch.object(
            install_release.urllib.request,
            "urlopen",
            return_value=HealthResponse(),
        ):
            self.assertTrue(install_release.wait_for_health("http://127.0.0.1/healthz"))
    def test_activates_release_after_staging_and_health_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "release.tar.gz"
            checksum = make_release(archive)
            commands = []

            def fake_run(command, cwd=None):
                commands.append((command, cwd))

            installed = install_release.install_release(
                archive,
                checksum,
                root / "install",
                run=fake_run,
                check_health=lambda _: True,
            )

            current = root / "install" / "current"
            self.assertEqual(current.resolve(), installed)
            self.assertEqual(
                (installed / "frontend/browser/index.html").read_bytes(),
                b"<!doctype html>",
            )
            self.assertTrue(
                any(
                    command[:2] == ["systemctl", "restart"]
                    for command, _ in commands
                )
            )

    def test_restores_previous_release_when_health_check_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "release.tar.gz"
            checksum = make_release(archive)
            install_root = root / "install"
            previous_release = install_root / "releases" / "previous"
            previous_release.mkdir(parents=True)
            current = install_root / "current"
            current.symlink_to(previous_release)
            commands = []

            with self.assertRaisesRegex(RuntimeError, "previous release was restored"):
                install_release.install_release(
                    archive,
                    checksum,
                    install_root,
                    run=lambda command, cwd=None: commands.append(command),
                    check_health=lambda _: False,
                )

            self.assertEqual(current.resolve(), previous_release)
            self.assertFalse((install_root / "releases" / "1234567890abcdef").exists())
            self.assertEqual(
                sum(command[:2] == ["systemctl", "restart"] for command in commands),
                2,
            )

    def test_refuses_to_replace_an_existing_non_symlink_current_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "release.tar.gz"
            checksum = make_release(archive)
            install_root = root / "install"
            current = install_root / "current"
            current.mkdir(parents=True)

            with self.assertRaisesRegex(ValueError, "must be absent or a symlink"):
                install_release.install_release(
                    archive,
                    checksum,
                    install_root,
                    run=lambda command, cwd=None: None,
                    check_health=lambda _: True,
                )
    def test_explicit_rollback_switches_to_a_retained_release(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir) / "install"
            old_release = install_root / "releases" / "1234567890abcdef"
            active_release = install_root / "releases" / "fedcba0987654321"
            (old_release / ".venv/bin").mkdir(parents=True)
            (old_release / ".venv/bin/hypercorn").touch()
            active_release.mkdir(parents=True)
            current = install_root / "current"
            current.symlink_to(active_release)
            commands = []

            restored = install_release.rollback_release(
                install_root,
                "1234567890abcdef",
                run=lambda command, cwd=None: commands.append(command),
                check_health=lambda _: True,
            )

            self.assertEqual(restored, old_release)
            self.assertEqual(current.resolve(), old_release)
            self.assertEqual(commands, [["systemctl", "restart", "pcibex.service"]])


if __name__ == "__main__":
    unittest.main()

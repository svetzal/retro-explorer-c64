"""Firmware placement and verification with original stand-in ROM bytes."""

import hashlib
import io
import json
import tarfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from firmware import (
    FirmwareSourceGateway,
    load_manifest,
    provision,
    targets,
    verify_installed,
)

KERNAL, CHARGEN = b"K" * 16, b"C" * 8
RELEASE_DIRECTORY = "vice-x/data/C64"


def release_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(f"{RELEASE_DIRECTORY}/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.fixture
def release() -> bytes:
    return release_bytes({"kernal.bin": KERNAL, "chargen.bin": CHARGEN})


@pytest.fixture
def project(tmp_path: Path, release: bytes) -> Path:
    def rom(role: str, data: bytes) -> dict[str, object]:
        return {
            "role": role,
            "description": role,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    manifest = {
        "release": {
            "name": "test release",
            "url": "https://example.org/vice-x.tar.gz",
            "sha256": hashlib.sha256(release).hexdigest(),
            "directory": RELEASE_DIRECTORY,
        },
        "roms": {"kernal.bin": rom("kernal", KERNAL), "chargen.bin": rom("chargen", CHARGEN)},
        "targets": {"t-pal": ["kernal.bin", "chargen.bin"], "t-ntsc": ["kernal.bin"]},
    }
    (tmp_path / "firmware.json").write_text(json.dumps(manifest))
    return tmp_path


def sources(installed: dict[str, bytes] | None = None, release: bytes | None = None) -> Mock:
    gateway = Mock(spec=FirmwareSourceGateway)
    gateway.installed.side_effect = lambda name: (installed or {}).get(name)
    gateway.download.return_value = release
    return gateway


def rom_path(project: Path, name: str) -> Path:
    return project / "local/roms/C64" / name


class DescribeProvision:
    def should_copy_verified_roms_from_the_installed_vice(self, project: Path) -> None:
        gateway = sources({"kernal.bin": KERNAL, "chargen.bin": CHARGEN})

        provision(project, "t-pal", gateway)

        assert rom_path(project, "kernal.bin").read_bytes() == KERNAL
        assert rom_path(project, "chargen.bin").read_bytes() == CHARGEN
        gateway.download.assert_not_called()

    def should_fall_back_to_the_pinned_release_and_cache_it(
        self, project: Path, release: bytes
    ) -> None:
        gateway = sources({"kernal.bin": b"wrong" * 3 + b"!"}, release)

        provision(project, "t-pal", gateway)
        provision(project, "t-ntsc", sources())

        assert rom_path(project, "kernal.bin").read_bytes() == KERNAL
        assert (project / "local/firmware-sources/vice-x.tar.gz").read_bytes() == release
        gateway.download.assert_called_once_with("https://example.org/vice-x.tar.gz")

    def should_reject_a_release_with_another_checksum(self, project: Path) -> None:
        with pytest.raises(ValueError, match="checksum mismatch"):
            provision(project, "t-pal", sources(release=b"tampered"))

        assert not rom_path(project, "kernal.bin").exists()

    def should_reject_a_release_without_the_rom(self, project: Path, release: bytes) -> None:
        manifest = json.loads((project / "firmware.json").read_text())
        empty = release_bytes({})
        manifest["release"]["sha256"] = hashlib.sha256(empty).hexdigest()
        (project / "firmware.json").write_text(json.dumps(manifest))

        with pytest.raises(ValueError, match="not found"):
            provision(project, "t-ntsc", sources(release=empty))

    def should_keep_an_existing_rom_that_differs_for_inspection(self, project: Path) -> None:
        path = rom_path(project, "kernal.bin")
        path.parent.mkdir(parents=True)
        path.write_bytes(b"X" * 16)

        with pytest.raises(ValueError, match="inspect it"):
            provision(project, "t-ntsc", sources({"kernal.bin": KERNAL}))

        assert path.read_bytes() == b"X" * 16

    def should_name_an_unknown_target(self, project: Path) -> None:
        with pytest.raises(ValueError, match="No firmware profile"):
            provision(project, "t-other", sources())


class DescribeVerifyInstalled:
    def should_return_the_paths_of_matching_roms(self, project: Path) -> None:
        provision(project, "t-pal", sources({"kernal.bin": KERNAL, "chargen.bin": CHARGEN}))

        assert set(verify_installed(project, "t-pal")) == {"kernal.bin", "chargen.bin"}

    @pytest.mark.parametrize("content", [b"K" * 15, b"k" * 16, None])
    def should_stop_with_a_recovery_command(self, project: Path, content: bytes | None) -> None:
        if content is not None:
            rom_path(project, "kernal.bin").parent.mkdir(parents=True)
            rom_path(project, "kernal.bin").write_bytes(content)

        with pytest.raises(ValueError, match="--target t-ntsc --firmware-only"):
            verify_installed(project, "t-ntsc")

    def should_reject_a_rom_the_manifest_does_not_list(self, project: Path) -> None:
        with pytest.raises(ValueError, match="not listed"):
            verify_installed(project, "t-pal", ("basic.bin",))


class DescribeRepositoryManifest:
    def should_list_both_standard_targets_with_the_same_rom_roles(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(root)

        assert targets(root) == ("c64-pal", "c64-ntsc")
        for target in targets(root):
            roles = sorted(manifest.roms[name].role for name in manifest.names(target))
            assert roles == ["basic", "chargen", "kernal"]

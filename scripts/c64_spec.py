"""c64.py: unit specs for its decisions, and real 64tass and VICE runs with negative controls."""

import hashlib
import json
import shutil
import subprocess
import wave
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import c64
import numpy as np
import pytest
from c64 import (
    Build,
    Check,
    Host,
    Machine,
    Project,
    ProjectError,
    Result,
    address,
    load_project,
    parse_labels,
    petscii,
)
from firmware import load_manifest
from native import tool_path
from PIL import Image
from vice_monitor import Display
from vice_session import Capture

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/first-screen"
PAL = Machine(
    model="c64",
    video="pal",
    vicii="6569",
    sid="6581",
    ram_kib=64,
    kernal="kernal-901227-03.bin",
    basic="basic-901226-01.bin",
    chargen="chargen-901225-01.bin",
)
TOML = """
[targets.t]
model = "c64"
video = "pal"
vicii = "6569"
sid = "6581"
ram_kib = 64
kernal = "kernal-901227-03.bin"
basic = "basic-901226-01.bin"
chargen = "chargen-901225-01.bin"

[check]
checkpoint = "shown"
hit = 2
unreachable = ["shown+1"]
cycle_limit = 1000
screen = 0x0400
colours = 0xD800
border_ring = 1
"""


def write_project(directory: Path, toml: str = TOML) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "c64.toml").write_text(toml)
    (directory / "main.asm").write_text("; empty\n")
    return directory


def rom_bytes() -> dict[str, bytes]:
    """Stand-in ROM contents whose checksums the spec's manifest records."""
    return {"kernal": b"K" * 8, "basic": b"B" * 8, "chargen": bytes(range(256)) * 8}


@pytest.fixture
def starter(tmp_path: Path) -> Path:
    """A starter root whose firmware.json describes stand-in ROMs."""
    roms = rom_bytes()
    manifest = json.loads((ROOT / "firmware.json").read_text())
    for rom in manifest["roms"].values():
        rom["sha256"] = hashlib.sha256(roms[rom["role"]]).hexdigest()
        rom["size"] = len(roms[rom["role"]])
    (tmp_path / "firmware.json").write_text(json.dumps(manifest))
    return tmp_path


@pytest.fixture
def project(starter: Path) -> c64.Project:
    return load_project(write_project(starter / "projects/demo"), starter)


def display(frame: np.ndarray, inner: tuple[int, int, int, int]) -> Display:
    x, y, width, height = inner
    return Display(
        width=frame.shape[1],
        height=frame.shape[0],
        inner_x=x,
        inner_y=y,
        inner_width=width,
        inner_height=height,
        pixels=frame.tobytes(),
        missing=0,
    )


def capture(**changes: object) -> Capture:
    frame = np.full((6, 6), 6, dtype=np.uint8)
    frame[1:5, 1:5] = 0
    values = {
        "vice_version": "3.10.0.0",
        "reached": True,
        "outcome": "stopped at hit 2",
        "hits": 2,
        "registers": {"PC": 0x0834},
        "ram": bytes(0x10000),
        "io": bytes(0x1000),
        "roms": rom_bytes(),
        "machine": {"video": "pal", "vicii": "6569", "sid": "6581"},
        "display": display(frame, (1, 1, 4, 4)),
        "palette": [(0, 0, 0)] * 16,
    }
    return Capture(**(values | changes))


def built(tmp_path: Path) -> Build:
    return Build(
        variant="main",
        program=tmp_path / "main.prg",
        labels=tmp_path / "main.labels",
        listing=tmp_path / "main.lst",
        symbols={"shown": 0x0834},
    )


def model(**functions: object) -> SimpleNamespace:
    return SimpleNamespace(**functions)


class DescribeLabels:
    def should_read_vice_labels_from_64tass(self) -> None:
        text = "al 80d .start\nal C:0834 .shown\nnot a label\n"

        assert parse_labels(text) == {"start": 0x080D, "shown": 0x0834}

    @pytest.mark.parametrize(
        "expression, value",
        [("shown", 0x0834), ("shown+1", 0x0835), ("shown - 4", 0x0830), ("shown+$10", 0x0844)],
    )
    def should_resolve_label_expressions(self, expression: str, value: int) -> None:
        assert address({"shown": 0x0834}, expression) == value

    @pytest.mark.parametrize("expression", ["missing", "shown*2", "1234"])
    def should_reject_unknown_labels_and_other_expressions(self, expression: str) -> None:
        with pytest.raises(ProjectError):
            address({"shown": 0x0834}, expression)

    def should_send_upper_case_text_as_the_same_codes(self) -> None:
        assert petscii("RUN 1") == b"RUN 1"


class DescribeProjectSettings:
    def should_load_targets_and_check(self, project: c64.Project) -> None:
        assert project.settings.targets["t"] == PAL
        assert project.require_check().border_ring == 1
        assert project.output == project.root / "build/projects/demo"

    @pytest.mark.parametrize(
        "change, message",
        [
            (('sid = "6581"', 'sid = "6582"'), "sid must be one of"),
            (("ram_kib = 64", "ram_kib = 32"), "ram_kib"),
            (('video = "pal"', 'video = "secam"'), "video"),
            (
                ("[check]", "[variants.x]\ndefines = ['A=1']\ntargets = ['u']\n\n[check]"),
                "unknown targets",
            ),
            (("hit = 2", "hit = 0"), "hit"),
        ],
    )
    def should_reject_invalid_settings(self, starter: Path, change, message: str) -> None:
        directory = write_project(starter / "bad", TOML.replace(*change))

        with pytest.raises(ProjectError, match=message):
            load_project(directory, starter)

    def should_explain_a_missing_settings_file(self, tmp_path: Path) -> None:
        with pytest.raises(ProjectError, match="c64.toml"):
            load_project(tmp_path)

    def should_require_a_check_table_for_checks(self, starter: Path) -> None:
        toml = TOML[: TOML.index("[check]")]
        project = load_project(write_project(starter / "p", toml), starter)

        with pytest.raises(ProjectError, match="no \\[check\\]"):
            project.require_check()

    def should_put_outside_projects_under_their_folder_name(self, starter: Path, tmp_path) -> None:
        outside = write_project(tmp_path.parent / f"{tmp_path.name}-outside")

        assert load_project(outside, starter).output == starter / "build" / outside.name


class DescribeCommands:
    def should_assemble_with_vice_labels_and_defines(self, tmp_path: Path) -> None:
        command = c64.assemble_command("64tass", tmp_path / "main.asm", tmp_path, ("A=1",))

        assert command[:2] == ["64tass", "--cbm-prg"]
        assert command[command.index("-l") + 1] == str(tmp_path / "main.labels")
        assert "--vice-labels" in command
        assert command[-3:] == ["-D", "A=1", str(tmp_path / "main.asm")]

    def should_name_the_disk_after_the_project(self, tmp_path: Path) -> None:
        command = c64.disk_command(
            "c1541", tmp_path / "p.prg", tmp_path / "p.d64", "first screen x"
        )

        assert command[1:4] == ["-format", "FIRST SCREEN X,01", "d64"]
        assert command[-1] == "FIRST SCREEN X"

    def should_open_x64sc_with_the_verified_rom_folder(self, project, tmp_path: Path) -> None:
        host = Mock(spec=Host)
        host.executable.return_value = "x64sc"

        command = c64.person_command(project, host, PAL, tmp_path / "main.prg")

        assert command[command.index("-directory") + 1].endswith("local/roms:$$")
        assert command[-2:] == ["-autostart", str((tmp_path / "main.prg").resolve())]

    def should_report_assembler_errors(self, project: c64.Project) -> None:
        host = Mock(spec=Host)
        host.executable.return_value = "64tass"
        host.run.return_value = subprocess.CompletedProcess([], 1, "main.asm:1: error", "")

        with pytest.raises(ProjectError, match="64tass failed"):
            c64.build(project, host)

    def should_reject_unknown_variants_and_targets(self, project: c64.Project) -> None:
        with pytest.raises(ProjectError, match="Unknown variant"):
            c64.defines_for(project, "missing")
        with pytest.raises(ProjectError, match="Unknown target"):
            c64.target_machine(project, "c128")

    def should_return_one_for_project_errors(self, tmp_path: Path, capsys) -> None:
        assert c64.main(["build", str(tmp_path)]) == 1
        assert "c64.toml" in capsys.readouterr().err

    def should_stop_before_launch_when_firmware_is_not_verified(self, project, capsys) -> None:
        host = Mock(spec=Host)
        host.executable.side_effect = lambda name: name
        host.run.side_effect = lambda command: write_labels(command)
        host.firmware.side_effect = ValueError("Cannot use t firmware")

        assert c64.main(["run", str(project.directory)], host, project.root) == 1

        host.launch.assert_not_called()
        assert "Cannot use t firmware" in capsys.readouterr().err


def write_labels(command: list[str]) -> subprocess.CompletedProcess:
    Path(command[command.index("-l") + 1]).write_text("al 834 .shown\n")
    Path(command[command.index("-o") + 1]).write_bytes(b"\x01\x08")
    return subprocess.CompletedProcess(command, 0, "", "")


class DescribeEvidenceResults:
    def should_pass_execution_only_at_the_checkpoint_address(self, tmp_path: Path) -> None:
        check = Check(checkpoint="shown", hit=2, unreachable=("shown+1",), cycle_limit=10)
        plan = c64.plan_for(check, built(tmp_path))

        good = c64.execution_result(capture(), plan, check)
        elsewhere = c64.execution_result(capture(registers={"PC": 0x0900}), plan, check)
        stopped = c64.execution_result(capture(reached=False, outcome="cycle limit"), plan, check)

        assert good.status == "pass" and "shown+1 never ran" in good.detail
        assert elsewhere.status == "fail" and "$0900" in elsewhere.detail
        assert (stopped.status, stopped.detail) == ("fail", "cycle limit")

    def should_compare_the_emulator_rom_bytes_with_the_manifest(self, project) -> None:
        wrong = rom_bytes() | {"chargen": b"x"}

        assert c64.firmware_result(project, PAL, capture()).status == "pass"
        failed = c64.firmware_result(project, PAL, capture(roms=wrong))
        assert failed.status == "fail" and "chargen" in failed.detail

    def should_compare_the_chips_vice_reports(self) -> None:
        ntsc = capture(machine={"video": "ntsc", "vicii": "6567", "sid": "6581"})

        assert c64.machine_result(PAL, capture()).status == "pass"
        assert "video is ntsc, declared pal" in c64.machine_result(PAL, ntsc).detail

    def should_compare_screen_and_low_colour_bits(self, project) -> None:
        check = project.require_check()
        io = bytearray(0x1000)
        io[0x800] = 0xF1  # the upper bits of colour memory are not part of the colour
        ram = bytearray(0x10000)
        ram[0x0400] = 0x08
        good = model(expected_screen=lambda: b"\x08", expected_colours=lambda: b"\x01")
        bad = model(expected_screen=lambda: b"\x09", expected_colours=lambda: b"\x02")
        state = capture(ram=bytes(ram), io=bytes(io))

        assert c64.screen_result(check, good, state, "t", "main").status == "pass"
        assert c64.colour_result(check, good, state, "t", "main").status == "pass"
        assert "expected $09, found $08" in c64.screen_result(check, bad, state, "t", "main").detail
        assert c64.colour_result(check, bad, state, "t", "main").status == "fail"

    def should_need_addresses_for_screen_and_colour_models(self, starter: Path) -> None:
        check = Check(checkpoint="shown", cycle_limit=10)

        with pytest.raises(ProjectError, match="screen"):
            c64.screen_result(check, model(expected_screen=lambda: b""), capture(), "t", "main")
        with pytest.raises(ProjectError, match="colours"):
            c64.colour_result(check, model(expected_colours=lambda: b""), capture(), "t", "main")

    def should_report_state_assertions(self, tmp_path: Path) -> None:
        def verify_state(state, target):
            assert target == "t", "wrong target"
            assert state.io[0x20] == 1, "border is not white"

        result = c64.state_result(
            model(verify_state=verify_state), capture(), built(tmp_path), "t", "main"
        )

        assert (result.status, result.detail) == ("fail", "border is not white")

    def should_compare_the_inner_frame_and_the_border_ring(self, project) -> None:
        inner = np.zeros((4, 4), dtype=np.uint8)
        good = model(expected_frame=lambda chargen: inner, expected_border=lambda: 6)
        wrong_border = model(expected_frame=lambda chargen: inner, expected_border=lambda: 2)
        wrong_inner = model(expected_frame=lambda chargen: inner + 1)
        wrong_size = model(expected_frame=lambda chargen: np.zeros((2, 2), dtype=np.uint8))

        assert c64.frame_result(project, good, capture(), "t", "main").status == "pass"
        assert (
            "20 of 20 border pixels"
            in c64.frame_result(project, wrong_border, capture(), "t", "main").detail
        )
        assert (
            "16 of 16 pixels differ"
            in c64.frame_result(project, wrong_inner, capture(), "t", "main").detail
        )
        assert "2x2" in c64.frame_result(project, wrong_size, capture(), "t", "main").detail

    def should_fail_the_frame_when_vice_returns_none(self, project) -> None:
        result = c64.frame_result(
            project, model(expected_frame=None), capture(display=None), "t", "main"
        )

        assert result.status == "fail"

    def should_pass_target_and_variant_only_to_functions_that_ask(self) -> None:
        def both(value, target, variant):
            return (value, target, variant)

        assert c64.call(both, 1, target="t", variant="v") == (1, "t", "v")
        assert c64.call(lambda: 5, target="t", variant="v") == 5

    def should_report_each_kind_and_fail_on_any_failure(self) -> None:
        results = [
            Result(kind="execution", status="pass", detail="ok"),
            Result(kind="sound", status="not captured", detail="add --audio"),
        ]

        assert c64.report("t", "main", results)[0] == "t main: PASS"
        assert not c64.passed([*results, Result(kind="frame", status="fail", detail="x")])

    def should_say_when_there_is_no_model(self, project, tmp_path) -> None:
        results = c64.model_results(project, PAL, None, capture(), built(tmp_path), "t", "main")

        assert results[0].status == "not compared"


class DescribeSound:
    def write_recording(self, directory: Path) -> None:
        with wave.open(str(directory / "sound.wav"), "wb") as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(48000)
            recording.writeframes(np.array([0, 1000, -1000], dtype="<i2").tobytes())
        (directory / "sid-writes.txt").write_text("34 24 0\n10 24 15\n")

    def should_give_the_model_samples_and_absolute_write_cycles(self, tmp_path: Path) -> None:
        self.write_recording(tmp_path)

        sound = c64.read_sound(tmp_path)

        assert sound.rate == 48000 and list(sound.samples) == [0, 1000, -1000]
        assert sound.writes == [(34, 24, 0), (44, 24, 15)]

    def should_report_capture_without_a_judge_and_the_judge_verdict(self, tmp_path: Path) -> None:
        self.write_recording(tmp_path)

        def silent(sound):
            assert sound.samples.max() == 0, "the recording is not silent"

        assert c64.sound_result(None, tmp_path, False, "t", "main").status == "not captured"
        assert c64.sound_result(model(), tmp_path, True, "t", "main").status == "captured"
        verdict = c64.sound_result(model(verify_sound=silent), tmp_path, True, "t", "main")
        assert (verdict.status, verdict.detail) == ("fail", "the recording is not silent")


class DescribeFrameImage:
    def should_keep_colour_numbers_and_attach_the_palette(self, tmp_path: Path) -> None:
        frame = np.array([[0, 1], [6, 15]], dtype=np.uint8)
        palette = [(index, index, index) for index in range(16)]

        c64.frame_image(display(frame, (0, 0, 2, 2)), palette).save(tmp_path / "f.png")

        image = Image.open(tmp_path / "f.png")
        assert image.mode == "P"
        assert np.array_equal(np.array(image), frame)
        assert image.convert("RGB").getpixel((1, 1)) == (15, 15, 15)


class DescribeCheckWithAScriptedEmulator:
    def should_write_a_result_record_for_each_target_and_variant(self, project, capsys) -> None:
        (project.directory / "c64.toml").write_text(
            TOML + '\n[variants.calm]\ndefines = ["CALM=1"]\n'
        )
        host = Mock(spec=Host)
        host.executable.side_effect = lambda name: name
        host.run.side_effect = write_labels
        host.free_port.return_value = 6502
        host.capture.return_value = capture()

        assert c64.main(["check", str(project.directory)], host, project.root) == 0

        output = capsys.readouterr().out
        assert "t main: PASS" in output and "t calm: PASS" in output
        record = json.loads((project.output / "calm/t/results.json").read_text())
        assert record["passed"] and record["variant"] == "calm"
        assert (project.output / "main/t/frame.png").is_file()


# ---- real 64tass and VICE ------------------------------------------------------------


def tools_ready() -> bool:
    if not all(tool_path(name) for name in ("64tass", "x64sc", "c1541")):
        return False
    manifest = load_manifest(ROOT)
    return all((ROOT / "local/roms/C64" / name).is_file() for name in manifest.roms)


needs_vice = pytest.mark.skipif(
    not tools_ready(), reason="needs 64tass, VICE and firmware: sh scripts/bootstrap.sh c64-pal"
)


@pytest.fixture
def real_starter(tmp_path: Path) -> Path:
    """A starter root with the real manifest and the verified local ROMs."""
    shutil.copy(ROOT / "firmware.json", tmp_path / "firmware.json")
    (tmp_path / "local/roms").mkdir(parents=True)
    shutil.copytree(ROOT / "local/roms/C64", tmp_path / "local/roms/C64")
    return tmp_path


def copy_example(
    starter: Path, *edits: tuple[str, str], toml: tuple[str, str] | None = None
) -> Path:
    """A copy of first-screen with exact text edits; each edit must apply once."""
    directory = starter / "examples/first-screen"
    shutil.copytree(EXAMPLE, directory, ignore=shutil.ignore_patterns("__pycache__"))
    for path, (old, new) in [
        *(("main.asm", e) for e in edits),
        *((("c64.toml", toml),) if toml else ()),
    ]:
        text = (directory / path).read_text()
        assert text.count(old) == 1, f"{old!r} must occur once in {path}"
        (directory / path).write_text(text.replace(old, new))
    return directory


def check(directory: Path, starter: Path, *options: str) -> tuple[int, dict[str, dict[str, str]]]:
    """Exit status and, per target, each evidence kind's status."""
    status = c64.main(["check", str(directory), *options], root=starter)
    output = starter / "build/examples/first-screen/main"
    kinds = {}
    for record in output.glob("*/results.json"):
        data = json.loads(record.read_text())
        kinds[data["target"]] = {r["kind"]: r["status"] for r in data["results"]}
    return status, kinds


@pytest.mark.integration
@needs_vice
class DescribeFirstScreenOnVice:
    def should_pass_every_kind_of_evidence_on_both_targets(self, real_starter: Path) -> None:
        status, kinds = check(copy_example(real_starter), real_starter)

        assert status == 0
        assert set(kinds) == {"c64-pal", "c64-ntsc"}
        for target in kinds.values():
            for kind in (
                "execution",
                "firmware",
                "machine",
                "screen memory",
                "colour memory",
                "state",
                "rendered frame",
            ):
                assert target[kind] == "pass"
            assert target["visual inspection"] == "not done"

    def should_fail_screen_memory_and_frame_for_one_wrong_letter(self, real_starter) -> None:
        directory = copy_example(real_starter, ('"first screen"', '"first screem"'))

        status, kinds = check(directory, real_starter, "--target", "c64-pal")

        assert status == 1
        assert kinds["c64-pal"]["screen memory"] == "fail"
        assert kinds["c64-pal"]["colour memory"] == "pass"
        assert kinds["c64-pal"]["rendered frame"] == "fail"

    def should_fail_colour_memory_and_frame_for_a_wrong_text_colour(self, real_starter) -> None:
        directory = copy_example(real_starter, ("        lda #YELLOW\n", "        lda #WHITE\n"))

        status, kinds = check(directory, real_starter, "--target", "c64-ntsc")

        assert status == 1
        assert kinds["c64-ntsc"]["screen memory"] == "pass"
        assert kinds["c64-ntsc"]["colour memory"] == "fail"
        assert kinds["c64-ntsc"]["rendered frame"] == "fail"

    def should_fail_state_and_border_for_a_wrong_border_colour(self, real_starter) -> None:
        directory = copy_example(
            real_starter, ("lda #BLUE\n        sta BORDER", "lda #WHITE\n        sta BORDER")
        )

        status, kinds = check(directory, real_starter, "--target", "c64-pal")

        assert status == 1
        assert kinds["c64-pal"]["state"] == "fail"
        assert kinds["c64-pal"]["rendered frame"] == "fail"

    def should_fail_only_the_frame_for_the_lower_case_character_set(self, real_starter) -> None:
        # POKE 53272,23 switches to lower case (Programmer's Reference Guide, PDF 395).
        # Memory stays the same, so only the rendered frame can catch it.
        directory = copy_example(real_starter, ("start\n", "start   lda #23\n        sta $d018\n"))

        status, kinds = check(directory, real_starter, "--target", "c64-pal")

        assert status == 1
        assert kinds["c64-pal"]["screen memory"] == "pass"
        assert kinds["c64-pal"]["colour memory"] == "pass"
        assert kinds["c64-pal"]["state"] == "pass"
        assert kinds["c64-pal"]["rendered frame"] == "fail"

    def should_fail_execution_when_the_checkpoint_is_never_reached(self, real_starter) -> None:
        directory = copy_example(
            real_starter,
            ("frame   lda $d012", "stall   jmp stall\nframe   lda $d012"),
            toml=("cycle_limit = 20_000_000", "cycle_limit = 5_000_000"),
        )

        status, kinds = check(directory, real_starter, "--target", "c64-pal")

        assert status == 1
        assert kinds == {"c64-pal": {"execution": "fail"}}

    def should_fail_execution_when_an_unreachable_label_runs(self, real_starter) -> None:
        directory = copy_example(real_starter, toml=('["shown+1"]', '["wait"]'))

        status, kinds = check(directory, real_starter, "--target", "c64-ntsc")

        assert status == 1
        assert kinds == {"c64-ntsc": {"execution": "fail"}}

    def should_fail_machine_when_the_target_names_another_vic(self, real_starter) -> None:
        directory = copy_example(real_starter, toml=('vicii = "6569"', 'vicii = "6567"'))

        status, kinds = check(directory, real_starter, "--target", "c64-pal")

        assert status == 1
        assert kinds["c64-pal"]["machine"] == "fail"

    def should_refuse_to_launch_with_a_changed_rom(self, real_starter, capsys) -> None:
        rom = real_starter / "local/roms/C64/chargen-901225-01.bin"
        rom.write_bytes(b"\xff" + rom.read_bytes()[1:])

        status, kinds = check(copy_example(real_starter), real_starter)

        assert status == 1 and kinds == {}
        assert "checksum mismatch" in capsys.readouterr().err


PROBE = """\
*       = $0801
        .word (+), 2026
        .null $9e, format("%4d", start)
+       .word 0
start   {body}
"""
PROBE_TOML = (
    TOML.replace("[targets.t]", "[targets.c64-pal]")
    .replace("hit = 2\n", "hit = 1\n")
    .replace('unreachable = ["shown+1"]\n', "")
    .replace("cycle_limit = 1000", "cycle_limit = 20_000_000")
    .replace("border_ring = 1\n", "")
)


def probe(
    starter: Path, name: str, body: str, toml: str = PROBE_TOML, model: str | None = None
) -> Path:
    directory = write_project(starter / "probes" / name, toml)
    (directory / "main.asm").write_text(PROBE.format(body=body))
    if model:
        (directory / "expected.py").write_text(model)
    return directory


@pytest.mark.integration
@needs_vice
class DescribeMeasuredAbilities:
    # GETIN at $FFE4 returns the next key from the keyboard buffer in A, or 0
    # (Programmer's Reference Guide, PDF 302).
    KEYS = """jsr $ffe4
        beq start
        sta $c000
        jsr $ffe4
        sta $c001
shown   jmp shown
"""
    KEYS_MODEL = """
def verify_state(state):
    assert state.ram[0xC000:0xC002] == b"GO", f"typed {state.ram[0xC000:0xC002]!r}"
"""

    def should_type_text_into_the_keyboard_buffer(self, real_starter: Path) -> None:
        toml = PROBE_TOML + '\n[check.input]\nat = "start"\ntext = "GO"\n'
        directory = probe(real_starter, "keys", self.KEYS, toml, self.KEYS_MODEL)

        assert c64.main(["check", str(directory)], root=real_starter) == 0

    def should_fail_the_keyboard_model_without_input(self, real_starter: Path) -> None:
        # No input: GETIN never returns a key, so the checkpoint is never reached.
        toml = PROBE_TOML.replace("cycle_limit = 20_000_000", "cycle_limit = 5_000_000")
        directory = probe(real_starter, "no-keys", self.KEYS, toml, self.KEYS_MODEL)

        assert c64.main(["check", str(directory)], root=real_starter) == 1

    # SID registers from 54272 ($D400): voice 1 frequency $D400-$D401, control
    # $D404, attack/decay $D405, sustain/release $D406, volume in the low 4 bits
    # of $D418 (Programmer's Reference Guide, PDF 343-345).
    TONE = """lda #{volume}
        sta $d418
        lda #$00
        sta $d405
        lda #$f0
        sta $d406
        lda #$1d
        sta $d401
        lda #$11
        sta $d404
        ldx #0
        ldy #0
wait    dex
        bne wait
        dey
        bne wait
shown   jmp shown
"""
    TONE_MODEL = """
import numpy as np

def verify_sound(sound):
    assert (0x18, 15) in [(r, v) for _, r, v in sound.writes], "volume 15 was not written"
    level = float(np.sqrt(np.mean(sound.samples[-2000:].astype(float) ** 2)))
    assert level > 500, f"the last samples are near silence (RMS {level:.0f})"
    return f"RMS {level:.0f} in the last 2000 samples"
"""

    def should_record_the_sid_output_and_its_register_writes(self, real_starter: Path) -> None:
        directory = probe(real_starter, "tone", self.TONE.format(volume=15), model=self.TONE_MODEL)

        assert c64.main(["check", str(directory), "--audio"], root=real_starter) == 0
        result = json.loads(
            (real_starter / "build/probes/tone/main/c64-pal/results.json").read_text()
        )
        sound = next(r for r in result["results"] if r["kind"] == "sound")
        assert sound["status"] == "pass"

    def should_fail_the_sound_model_for_a_muted_tone(self, real_starter: Path) -> None:
        directory = probe(real_starter, "muted", self.TONE.format(volume=0), model=self.TONE_MODEL)

        assert c64.main(["check", str(directory), "--audio"], root=real_starter) == 1

    def should_write_a_disk_image_that_lists_the_program(self, real_starter: Path, capsys) -> None:
        directory = probe(real_starter, "disk-demo", "rts\nshown   rts\n")

        assert c64.main(["build", str(directory), "--disk"], root=real_starter) == 0

        image = Path(capsys.readouterr().out.splitlines()[-1])
        listing = subprocess.run(
            [tool_path("c1541"), "-attach", str(image), "-list"],
            capture_output=True,
            text=True,
            errors="replace",
            check=True,
        ).stdout
        assert '"disk demo"' in listing.lower()

    @staticmethod
    def start_template_from(starter: Path, image: Callable[[Project, Host, Build], Path]):
        """Autostart a disk image instead of the PRG; the template's check plan applies."""
        shutil.copytree(ROOT / "template", starter / "template", dirs_exist_ok=True)
        project = load_project(starter / "template", starter)
        host = Host()
        built = c64.build(project, host, "main")
        plan = c64.plan_for(project.require_check(), built)
        launch = c64.Launch(
            executable=host.executable("x64sc"),
            rom_directory=starter / "local/roms",
            model="c64",
            sid="6581",
            port=host.free_port(),
            cycle_limit=20_000_000,
        )
        from_disk = plan.model_copy(update={"program": image(project, host, built)})
        return built, host.capture(launch, from_disk, starter / "vice.log")

    def should_start_the_template_from_its_disk_image(self, real_starter: Path) -> None:
        # The run --disk path: VICE autostarts the D64, so the program must reach its
        # checkpoint from the disk. This does not show which drive emulation loaded it.
        built, capture = self.start_template_from(real_starter, c64.make_disk)

        assert capture.reached, capture.outcome
        assert capture.registers["PC"] == built.symbols["frame"]

    def should_not_reach_the_checkpoint_from_an_empty_disk(self, real_starter: Path) -> None:
        def empty_disk(project: Project, host: Host, built: Build) -> Path:
            image = real_starter / "empty.d64"
            host.run([host.executable("c1541"), "-format", "EMPTY,01", "d64", str(image)])
            return image

        _, capture = self.start_template_from(real_starter, empty_disk)

        assert not capture.reached

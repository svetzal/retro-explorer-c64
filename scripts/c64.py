"""Build, run, snapshot or check a C64 project folder described by its c64.toml.

A project folder holds main.asm (64tass source), c64.toml, README.md and,
optionally, expected.py: an independent model of what the checkpoint must show.
All C64 facts (machine, firmware, addresses, labels, pictures) live in those
project files. This tool only assembles with 64tass and drives VICE's x64sc
through its binary monitor.

build assembles a PRG into build/<folder>/<variant>/ with a VICE label file and
a listing. --disk also writes a D64 disk image with VICE's c1541.

run assembles, checks the firmware, and opens x64sc with autostart for a person.

snapshot runs the program headless (minimized window, no sound unless --audio)
from power-on until the [check] checkpoint label has executed its Nth time,
and saves the evidence: RAM, I/O, registers, the rendered frame as PNG and,
with --audio, a WAV of the SID output and a log of SID register writes.

check runs every [targets.<name>] table and every [variants.<name>] build,
compares the evidence with expected.py and reports pass or fail for each kind.

Evidence boundaries:
- execution: VICE reported the checkpoint hit and the stopped PC equals the
  label address. Labels in [check] unreachable must never execute. The run
  stops at [check] cycle_limit emulated cycles (VICE -limitcycles).
- firmware: the KERNAL, BASIC and character ROM bytes read from the running
  emulator match firmware.json. The ROM files are also checked before launch.
- machine: VICE's video standard, VIC-II model and SID model match the target.
- memory: screen and colour memory and expected.py state checks. A memory
  match does not prove the picture: a wrong mode or character set can show
  the same bytes differently.
- rendered frame: VICE's frame buffer as colour indices, compared with
  expected_frame (inner area) and expected_border. It is VICE's renderer, not
  a window, a television or a monitor.
- sound: with --audio, a WAV of VICE's SID output and the SID register writes,
  judged by expected.py verify_sound. Not host playback or listening.
- keyboard: [check.input] text goes into the KERNAL keyboard buffer through
  the monitor. It does not press keys in the keyboard matrix.
- not supplied: joystick input, visual inspection by a person, physical C64
  hardware (including the C64 Ultimate).
"""

import argparse
import hashlib
import importlib.util
import inspect
import json
import re
import subprocess
import sys
import tomllib
import wave
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import numpy as np
from firmware import load_manifest, rom_directory, verify_installed
from native import ROOT, tool_path
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from vice_monitor import Display
from vice_session import SID_MODELS, Capture, Launch, Plan, ViceProcessGateway, session

LABEL_LINE = re.compile(r"^al\s+(?:C:)?([0-9a-fA-F]+)\s+\.(\S+)$")
EXPRESSION = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*(?:([+-])\s*(\d+|\$[0-9a-fA-F]+))?\s*$")
MODEL = "expected.py"
PASS, FAIL = "pass", "fail"
# The I/O window that the monitor's "io" bank returns starts here. Commodore 64
# Programmer's Reference Guide, PDF 120: the VIC-II registers start at 53248 ($D000).
IO_START = 0xD000
# Colour memory is 4 bits wide. Programmer's Reference Guide, PDF 120.
COLOUR_BITS = 0x0F


class ProjectError(ValueError):
    """The project, its build or its check cannot continue."""


class Machine(BaseModel):
    """One target: the VICE model, the chips it must report and the ROM files."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    model: str
    video: str = Field(pattern=r"^(pal|ntsc)$")
    vicii: str
    sid: str
    ram_kib: int = Field(ge=64, le=64)
    kernal: str
    basic: str
    chargen: str

    @field_validator("sid")
    @classmethod
    def known_sid(cls, value: str) -> str:
        if value not in SID_MODELS.values():
            raise ValueError(f"sid must be one of {', '.join(SID_MODELS.values())}")
        return value

    def roms(self) -> dict[str, str]:
        return {"kernal": self.kernal, "basic": self.basic, "chargen": self.chargen}


class Variant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    defines: tuple[str, ...] = Field(min_length=1)
    targets: tuple[str, ...] = ()

    def applies_to(self, target: str) -> bool:
        return not self.targets or target in self.targets


class Input(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    at: str
    text: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z0-9 ]+$")


class Check(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    checkpoint: str
    hit: int = Field(default=1, ge=1)
    unreachable: tuple[str, ...] = ()
    cycle_limit: int = Field(gt=0)
    screen: int | None = None
    colours: int | None = None
    border_ring: int = Field(default=0, ge=0)
    input: Input | None = None


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: str = "main.asm"
    targets: dict[str, Machine] = Field(min_length=1)
    variants: dict[str, Variant] = {}
    check: Check | None = None


class Project(BaseModel):
    model_config = ConfigDict(frozen=True)
    directory: Path
    settings: Settings
    root: Path = ROOT

    @property
    def output(self) -> Path:
        try:
            relative = self.directory.resolve().relative_to(self.root.resolve())
        except ValueError:
            relative = Path(self.directory.resolve().name)
        return self.root / "build" / relative

    def require_check(self) -> Check:
        if self.settings.check is None:
            raise ProjectError(f"{self.directory / 'c64.toml'} has no [check] table")
        return self.settings.check


class Build(BaseModel):
    model_config = ConfigDict(frozen=True)
    variant: str
    program: Path
    labels: Path
    listing: Path
    symbols: dict[str, int]


class Result(BaseModel):
    """One kind of evidence and what it showed."""

    model_config = ConfigDict(frozen=True)
    kind: str
    status: str
    detail: str


def load_project(directory: Path, root: Path = ROOT) -> Project:
    path = directory / "c64.toml"
    try:
        settings = Settings.model_validate(tomllib.loads(path.read_text()))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        raise ProjectError(f"{path}: {error}") from error
    for name, variant in settings.variants.items():
        unknown = set(variant.targets) - set(settings.targets)
        if unknown:
            raise ProjectError(
                f"Variant {name} names unknown targets: {', '.join(sorted(unknown))}"
            )
    return Project(directory=directory, settings=settings, root=root)


def parse_labels(text: str) -> dict[str, int]:
    """Read 64tass --vice-labels output: lines of 'al <hex> .<name>'."""
    symbols = {}
    for line in text.splitlines():
        if match := LABEL_LINE.match(line.strip()):
            symbols[match.group(2)] = int(match.group(1), 16)
    return symbols


def address(symbols: dict[str, int], expression: str) -> int:
    """Resolve 'label', 'label+N' or 'label-$N' with the assembled labels."""
    match = EXPRESSION.match(expression)
    if not match:
        raise ProjectError(f"Cannot read the address expression {expression!r}")
    name, sign, offset = match.groups()
    if name not in symbols:
        raise ProjectError(f"Label {name!r} is not in the assembled labels")
    value = 0 if offset is None else int(offset[1:], 16) if offset[0] == "$" else int(offset)
    return (symbols[name] + (value if sign == "+" else -value)) & 0xFFFF


def petscii(text: str) -> bytes:
    """Upper-case letters, digits and space have the same codes in ASCII and PETSCII.

    Programmer's Reference Guide, Appendix C, PDF 398-399 (CHR$ 32-90).
    """
    return text.encode("ascii")


def assemble_command(tass: str, source: Path, build: Path, defines: tuple[str, ...]) -> list[str]:
    command = [tass, "--cbm-prg", "--ascii", "--quiet", "-o", str(build / "main.prg")]
    command += ["--vice-labels", "-l", str(build / "main.labels"), "-L", str(build / "main.lst")]
    for define in defines:
        command += ["-D", define]
    return [*command, str(source)]


def disk_command(c1541: str, program: Path, image: Path, name: str) -> list[str]:
    title = name.upper()[:16]
    return [c1541, "-format", f"{title},01", "d64", str(image), "-write", str(program), title]


class Host:
    """Executables, subprocesses and the emulator session."""

    def executable(self, name: str) -> str:
        found = tool_path(name)
        if not found:
            raise ProjectError(f"{name} is missing; run uv run python scripts/doctor.py")
        return found

    def run(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            command, capture_output=True, text=True, errors="replace", check=False
        )

    def launch(self, command: list[str]) -> None:
        subprocess.run(command, check=False)

    def firmware(self, root: Path, target: str, names: tuple[str, ...]) -> dict[str, Path]:
        return verify_installed(root, target, names)

    def capture(self, launch: Launch, plan: Plan, log: Path) -> Capture:
        return session(launch, plan, log)

    def free_port(self) -> int:
        return ViceProcessGateway().free_port()


def variant_names(project: Project, target: str | None = None) -> list[str]:
    declared = project.settings.variants.items()
    return ["main", *(n for n, v in declared if target is None or v.applies_to(target))]


def defines_for(project: Project, variant: str) -> tuple[str, ...]:
    if variant == "main":
        return ()
    if variant not in project.settings.variants:
        raise ProjectError(
            f"Unknown variant {variant!r}; c64.toml declares: "
            + ", ".join(project.settings.variants)
        )
    return project.settings.variants[variant].defines


def build(project: Project, host: Host, variant: str = "main") -> Build:
    directory = project.output / variant
    directory.mkdir(parents=True, exist_ok=True)
    source = project.directory / project.settings.source
    command = assemble_command(
        host.executable("64tass"), source, directory, defines_for(project, variant)
    )
    result = host.run(command)
    if result.returncode != 0:
        raise ProjectError(f"64tass failed for {source}:\n{result.stdout}{result.stderr}")
    labels = directory / "main.labels"
    return Build(
        variant=variant,
        program=directory / "main.prg",
        labels=labels,
        listing=directory / "main.lst",
        symbols=parse_labels(labels.read_text()),
    )


def make_disk(project: Project, host: Host, built: Build) -> Path:
    image = built.program.with_suffix(".d64")
    image.unlink(missing_ok=True)
    name = project.directory.resolve().name.replace("-", " ")
    result = host.run(disk_command(host.executable("c1541"), built.program, image, name))
    if result.returncode != 0 or not image.is_file():
        raise ProjectError(f"c1541 failed:\n{result.stdout}{result.stderr}")
    return image


def target_machine(project: Project, target: str | None) -> tuple[str, Machine]:
    name = target or next(iter(project.settings.targets))
    if name not in project.settings.targets:
        raise ProjectError(
            f"Unknown target {name!r}; c64.toml declares: " + ", ".join(project.settings.targets)
        )
    return name, project.settings.targets[name]


def verified_firmware(project: Project, host: Host, target: str, machine: Machine) -> None:
    try:
        host.firmware(project.root, target, tuple(machine.roms().values()))
    except ValueError as error:
        raise ProjectError(str(error)) from error


def person_command(project: Project, host: Host, machine: Machine, image: Path) -> list[str]:
    return [
        host.executable("x64sc"),
        "-default",
        "-directory",
        f"{rom_directory(project.root)}:$$",
        "-model",
        machine.model,
        "-sidmodel",
        str({v: k for k, v in SID_MODELS.items()}[machine.sid]),
        "-autostart",
        str(image.resolve()),
    ]


def plan_for(check: Check, built: Build) -> Plan:
    feed = check.input
    return Plan(
        program=built.program,
        checkpoint=address(built.symbols, check.checkpoint),
        hit=check.hit,
        unreachable=tuple(address(built.symbols, label) for label in check.unreachable),
        feed_at=address(built.symbols, feed.at) if feed else None,
        feed=petscii(feed.text) if feed else b"",
    )


def evidence_directory(project: Project, target: str, variant: str) -> Path:
    directory = project.output / variant / target
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def snapshot_run(
    project: Project, host: Host, target: str, variant: str, audio: bool
) -> tuple[Build, Capture, Path]:
    check = project.require_check()
    name, machine = target_machine(project, target)
    built = build(project, host, variant)
    plan = plan_for(check, built)
    verified_firmware(project, host, name, machine)
    directory = evidence_directory(project, name, variant)
    for stale in directory.iterdir():
        stale.unlink()
    launch = Launch(
        executable=host.executable("x64sc"),
        rom_directory=rom_directory(project.root),
        model=machine.model,
        sid=machine.sid,
        port=host.free_port(),
        cycle_limit=check.cycle_limit,
        sound_log=directory / "sid-writes.txt" if audio else None,
        wav=directory / "sound.wav" if audio else None,
    )
    capture = host.capture(launch, plan, directory / "vice.log")
    save_evidence(capture, directory)
    return built, capture, directory


def save_evidence(capture: Capture, directory: Path) -> None:
    if not capture.reached and not capture.ram:
        return
    (directory / "ram.bin").write_bytes(capture.ram)
    (directory / "io.bin").write_bytes(capture.io)
    (directory / "registers.json").write_text(json.dumps(capture.registers, indent=2) + "\n")
    if capture.display is not None:
        frame_image(capture.display, capture.palette).save(directory / "frame.png")


def frame_image(display: Display, palette: list[tuple[int, int, int]]) -> Image.Image:
    """An indexed PNG: the colour numbers VICE drew, with VICE's palette for viewing."""
    image = Image.frombytes("P", (display.width, display.height), display.pixels)
    image.putpalette([channel for colour in palette for channel in colour])
    return image


def frame_array(display: Display) -> np.ndarray:
    return np.frombuffer(display.pixels, dtype=np.uint8).reshape(display.height, display.width)


# ---- comparison with expected.py -------------------------------------------------------


class Sound(BaseModel):
    """VICE's SID output and the register writes, given to verify_sound."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    rate: int
    samples: np.ndarray
    writes: list[tuple[int, int, int]]


class State(BaseModel):
    """The memory and registers at the checkpoint, given to verify_state."""

    model_config = ConfigDict(frozen=True)
    ram: bytes
    io: bytes
    registers: dict[str, int]
    symbols: dict[str, int]


def load_model(directory: Path) -> ModuleType | None:
    path = directory / MODEL
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"expected_{directory.name}", path)
    if spec is None or spec.loader is None:
        raise ProjectError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call(function: Callable, *args: object, target: str, variant: str) -> object:
    """Pass target= and variant= only to a model function that declares them."""
    parameters = inspect.signature(function).parameters
    keywords = {
        name: value
        for name, value in (("target", target), ("variant", variant))
        if name in parameters
    }
    return function(*args, **keywords)


def bytes_difference(expected: bytes, actual: bytes, start: int) -> str | None:
    if len(actual) != len(expected):
        return f"compared {len(actual)} bytes, expected {len(expected)}"
    wrong = [i for i, (a, b) in enumerate(zip(expected, actual, strict=True)) if a != b]
    if not wrong:
        return None
    first = wrong[0]
    return (
        f"{len(wrong)} of {len(expected)} bytes differ; first at ${start + first:04X}: "
        f"expected ${expected[first]:02X}, found ${actual[first]:02X}"
    )


def execution_result(capture: Capture, plan: Plan, check: Check) -> Result:
    if not capture.reached:
        return Result(kind="execution", status=FAIL, detail=capture.outcome)
    pc = capture.registers.get("PC")
    if pc != plan.checkpoint:
        return Result(
            kind="execution",
            status=FAIL,
            detail=f"stopped with PC ${pc or 0:04X}, not at {check.checkpoint} ${plan.checkpoint:04X}",
        )
    never = f"; {', '.join(check.unreachable)} never ran" if check.unreachable else ""
    return Result(
        kind="execution",
        status=PASS,
        detail=f"{check.checkpoint} (${plan.checkpoint:04X}) ran {capture.hits} times; "
        f"stopped there with PC ${pc:04X}{never}",
    )


def firmware_result(project: Project, machine: Machine, capture: Capture) -> Result:
    roms = load_manifest(project.root).roms
    wrong = [
        f"{role} ({name})"
        for role, name in machine.roms().items()
        if hashlib.sha256(capture.roms.get(role, b"")).hexdigest() != roms[name].sha256
    ]
    if wrong:
        return Result(
            kind="firmware",
            status=FAIL,
            detail="ROM bytes in the emulator differ from firmware.json: " + ", ".join(wrong),
        )
    names = ", ".join(roms[name].description for name in machine.roms().values())
    return Result(kind="firmware", status=PASS, detail=f"emulator ROM bytes match {names}")


def machine_result(machine: Machine, capture: Capture) -> Result:
    declared = {"video": machine.video, "vicii": machine.vicii, "sid": machine.sid}
    wrong = [
        f"{key} is {capture.machine.get(key)}, declared {value}"
        for key, value in declared.items()
        if capture.machine.get(key) != value
    ]
    summary = ", ".join(f"{key} {value}" for key, value in capture.machine.items())
    if wrong:
        return Result(kind="machine", status=FAIL, detail="; ".join(wrong))
    return Result(
        kind="machine", status=PASS, detail=f"VICE {capture.vice_version} x64sc reports {summary}"
    )


def screen_result(
    check: Check, model: ModuleType, capture: Capture, target: str, variant: str
) -> Result:
    if check.screen is None:
        raise ProjectError("expected_screen needs [check] screen = <address>")
    expected = bytes(call(model.expected_screen, target=target, variant=variant))
    actual = capture.ram[check.screen : check.screen + len(expected)]
    if problem := bytes_difference(expected, actual, check.screen):
        return Result(kind="screen memory", status=FAIL, detail=problem)
    return Result(
        kind="screen memory",
        status=PASS,
        detail=f"{len(expected)} bytes at ${check.screen:04X} match expected_screen",
    )


def colour_result(
    check: Check, model: ModuleType, capture: Capture, target: str, variant: str
) -> Result:
    if check.colours is None:
        raise ProjectError("expected_colours needs [check] colours = <address>")
    expected = bytes(call(model.expected_colours, target=target, variant=variant))
    offset = check.colours - IO_START
    actual = bytes(b & COLOUR_BITS for b in capture.io[offset : offset + len(expected)])
    if problem := bytes_difference(expected, actual, check.colours):
        return Result(kind="colour memory", status=FAIL, detail=problem)
    return Result(
        kind="colour memory",
        status=PASS,
        detail=f"{len(expected)} colour values (low 4 bits) at ${check.colours:04X} match expected_colours",
    )


def state_result(
    model: ModuleType, capture: Capture, built: Build, target: str, variant: str
) -> Result:
    state = State(
        ram=capture.ram, io=capture.io, registers=capture.registers, symbols=built.symbols
    )
    try:
        detail = call(model.verify_state, state, target=target, variant=variant)
    except AssertionError as error:
        return Result(
            kind="state", status=FAIL, detail=assertion_text(error, "verify_state failed")
        )
    return Result(kind="state", status=PASS, detail=str(detail or "verify_state accepted"))


def frame_difference(expected: np.ndarray, actual: np.ndarray) -> str | None:
    if expected.shape != actual.shape:
        return f"expected a {expected.shape[1]}x{expected.shape[0]} area, captured {actual.shape[1]}x{actual.shape[0]}"
    wrong = np.argwhere(expected != actual)
    if not len(wrong):
        return None
    y, x = wrong[0]
    return (
        f"{len(wrong)} of {expected.size} pixels differ; first at x={x}, y={y}: "
        f"expected colour {expected[y, x]}, found {actual[y, x]}"
    )


def border_pixels(frame: np.ndarray, display: Display, ring: int) -> np.ndarray:
    top, left = display.inner_y - ring, display.inner_x - ring
    bottom = display.inner_y + display.inner_height + ring
    right = display.inner_x + display.inner_width + ring
    area = frame[top:bottom, left:right].copy()
    mask = np.ones(area.shape, dtype=bool)
    mask[ring:-ring, ring:-ring] = False
    return area[mask]


def border_problem(
    model: ModuleType, frame: np.ndarray, display: Display, check: Check, target: str, variant: str
) -> str | None:
    if not hasattr(model, "expected_border") or check.border_ring == 0:
        return None
    colour = int(call(model.expected_border, target=target, variant=variant))
    ring = border_pixels(frame, display, check.border_ring)
    wrong = int(np.count_nonzero(ring != colour))
    if wrong:
        return f"{wrong} of {ring.size} border pixels are not colour {colour}"
    return None


def frame_result(
    project: Project, model: ModuleType, capture: Capture, target: str, variant: str
) -> Result:
    display = capture.display
    if display is None:
        return Result(kind="rendered frame", status=FAIL, detail="VICE returned no display")
    frame = frame_array(display)
    inner = frame[
        display.inner_y : display.inner_y + display.inner_height,
        display.inner_x : display.inner_x + display.inner_width,
    ]
    chargen = capture.roms.get("chargen", b"")
    expected = np.asarray(
        call(model.expected_frame, chargen, target=target, variant=variant), dtype=np.uint8
    )
    check = project.require_check()
    problem = frame_difference(expected, inner) or border_problem(
        model, frame, display, check, target, variant
    )
    if problem:
        return Result(kind="rendered frame", status=FAIL, detail=problem)
    border = (
        f" and a {check.border_ring}-pixel border ring"
        if check.border_ring and hasattr(model, "expected_border")
        else ""
    )
    return Result(
        kind="rendered frame",
        status=PASS,
        detail=f"{inner.size} pixels of the {display.inner_width}x{display.inner_height} "
        f"inner area{border} match expected_frame",
    )


def read_sound(directory: Path) -> Sound:
    with wave.open(str(directory / "sound.wav")) as recording:
        frames = recording.readframes(recording.getnframes())
        samples = np.frombuffer(frames, dtype="<i2").reshape(-1, recording.getnchannels())
        rate = recording.getframerate()
    writes, clock = [], 0
    for line in (directory / "sid-writes.txt").read_text().splitlines():
        delta, register, value = (int(part) for part in line.split())
        clock += delta
        writes.append((clock, register, value))
    return Sound(rate=rate, samples=samples[:, 0].copy(), writes=writes)


def sound_result(
    model: ModuleType | None, directory: Path, audio: bool, target: str, variant: str
) -> Result:
    if not audio:
        return Result(
            kind="sound", status="not captured", detail="add --audio to record the SID output"
        )
    if model is None or not hasattr(model, "verify_sound"):
        return Result(
            kind="sound",
            status="captured",
            detail=f"not compared (no verify_sound); {directory / 'sound.wav'}",
        )
    sound = read_sound(directory)
    try:
        detail = call(model.verify_sound, sound, target=target, variant=variant)
    except AssertionError as error:
        return Result(
            kind="sound", status=FAIL, detail=assertion_text(error, "verify_sound failed")
        )
    return Result(kind="sound", status=PASS, detail=str(detail or "verify_sound accepted"))


def model_results(
    project: Project,
    machine: Machine,
    model: ModuleType | None,
    capture: Capture,
    built: Build,
    target: str,
    variant: str,
) -> list[Result]:
    if model is None:
        return [
            Result(
                kind="model", status="not compared", detail=f"add {MODEL} with an independent model"
            )
        ]
    check = project.require_check()
    checks = (
        ("expected_screen", lambda: screen_result(check, model, capture, target, variant)),
        ("expected_colours", lambda: colour_result(check, model, capture, target, variant)),
        ("verify_state", lambda: state_result(model, capture, built, target, variant)),
        ("expected_frame", lambda: frame_result(project, model, capture, target, variant)),
    )
    return [compare() for function, compare in checks if hasattr(model, function)]


def evaluate(
    project: Project,
    target: str,
    variant: str,
    built: Build,
    capture: Capture,
    directory: Path,
    audio: bool,
) -> list[Result]:
    check = project.require_check()
    _, machine = target_machine(project, target)
    execution = execution_result(capture, plan_for(check, built), check)
    if execution.status != PASS:
        return [execution]
    model = load_model(project.directory)
    return [
        execution,
        firmware_result(project, machine, capture),
        machine_result(machine, capture),
        *model_results(project, machine, model, capture, built, target, variant),
        sound_result(model, directory, audio, target, variant),
        Result(
            kind="visual inspection",
            status="not done",
            detail="no person looked; use the run command",
        ),
        Result(kind="physical hardware", status="not tested", detail="VICE only"),
    ]


def assertion_text(error: AssertionError, fallback: str) -> str:
    """The model's own message: its first line, without any assertion rewriting detail."""
    lines = str(error).splitlines()
    return lines[0] if lines else fallback


def passed(results: list[Result]) -> bool:
    return all(result.status != FAIL for result in results)


def check_one(project: Project, host: Host, target: str, variant: str, audio: bool) -> list[Result]:
    built, capture, directory = snapshot_run(project, host, target, variant, audio)
    results = evaluate(project, target, variant, built, capture, directory, audio)
    record = {
        "target": target,
        "variant": variant,
        "program_sha256": hashlib.sha256(built.program.read_bytes()).hexdigest(),
        "vice": capture.vice_version,
        "machine": capture.machine,
        "passed": passed(results),
        "results": [result.model_dump() for result in results],
    }
    (directory / "results.json").write_text(json.dumps(record, indent=2) + "\n")
    return results


def report(target: str, variant: str, results: list[Result]) -> list[str]:
    verdict = "PASS" if passed(results) else "FAIL"
    return [f"{target} {variant}: {verdict}"] + [
        f"  {result.kind}: {result.status}: {result.detail}" for result in results
    ]


# ---- commands --------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="c64.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = root.add_subparsers(dest="command", required=True)
    for name, text in (
        ("build", "assemble the project and print the PRG path"),
        ("run", "assemble and open x64sc at normal speed for a person"),
        ("snapshot", "run headless to the checkpoint and save the evidence"),
        ("check", "compare the evidence of every target and variant with expected.py"),
    ):
        command = commands.add_parser(name, help=text, description=text)
        command.add_argument("project", type=Path, help="folder holding c64.toml")
        command.add_argument("--target", help="a [targets.<name>] table; default: the first")
        if name != "check":
            command.add_argument("--variant", default="main", help="a [variants.<name>] build")
        if name in ("build", "run"):
            command.add_argument("--disk", action="store_true", help="also write (and run) a D64")
        if name in ("snapshot", "check"):
            command.add_argument(
                "--audio", action="store_true", help="record the SID output as WAV"
            )
    return root


def build_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    built = build(project, host, arguments.variant)
    print(built.program)
    print(built.labels)
    if arguments.disk:
        print(make_disk(project, host, built))


def run_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    name, machine = target_machine(project, arguments.target)
    built = build(project, host, arguments.variant)
    image = make_disk(project, host, built) if arguments.disk else built.program
    verified_firmware(project, host, name, machine)
    print(f"Opening x64sc ({name}) with {image}. Close the window to stop it.")
    host.launch(person_command(project, host, machine, image))


def snapshot_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    name, _ = target_machine(project, arguments.target)
    built, capture, directory = snapshot_run(
        project, host, name, arguments.variant, arguments.audio
    )
    result = execution_result(
        capture, plan_for(project.require_check(), built), project.require_check()
    )
    print(f"execution: {result.status}: {result.detail}")
    for path in sorted(directory.iterdir()):
        print(path)
    if result.status != PASS:
        raise ProjectError("The checkpoint was not reached; the evidence above is incomplete.")


def check_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    targets = (
        [target_machine(project, arguments.target)[0]]
        if arguments.target
        else list(project.settings.targets)
    )
    failed = []
    for target in targets:
        for variant in variant_names(project, target):
            results = check_one(project, host, target, variant, arguments.audio)
            print("\n".join(report(target, variant, results)))
            if not passed(results):
                failed.append(f"{target} {variant}")
    if failed:
        raise ProjectError("Check failed: " + ", ".join(failed))
    print(f"Check passed on {', '.join(targets)}. Evidence is in {project.output}.")


COMMANDS = {
    "build": build_command,
    "run": run_command,
    "snapshot": snapshot_command,
    "check": check_command,
}


def main(argv: list[str] | None = None, host: Host | None = None, root: Path = ROOT) -> int:
    arguments = parser().parse_args(argv)
    try:
        project = load_project(arguments.project, root)
        COMMANDS[arguments.command](project, arguments, host or Host())
    except ProjectError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

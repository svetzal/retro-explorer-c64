"""Launch x64sc with the binary monitor, run a program to a checkpoint and collect evidence."""

import socket
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from vice_monitor import (
    Command,
    Display,
    Event,
    Monitor,
    MonitorConnection,
    MonitorError,
    autostart,
    checkpoint_set,
    keyboard_feed,
    memory_get,
    parse_banks,
    parse_checkpoint,
    parse_display,
    parse_memory,
    parse_palette,
    parse_register_names,
    parse_registers,
    parse_resource,
    parse_vice_info,
    resource_get,
)

# VICE resources that describe the emulated machine. Their values are VICE's own
# enumerations: src/machine.h (MACHINE_SYNC_*), src/vicii.h (VICII_MODEL_*) and
# src/sid/sid.h (SID_MODEL_*) in the VICE 3.10 source.
VIDEO_STANDARDS = {1: "pal", 2: "ntsc", 3: "ntsc-old", 4: "pal-n"}
VICII_MODELS = {0: "6569", 1: "8565", 2: "6569r1", 3: "6567", 4: "8562", 5: "6567r56a", 6: "6572"}
SID_MODELS = {0: "6581", 1: "8580"}
SID_MODEL_IDS = {name: number for number, name in SID_MODELS.items()}
# Measured with VICE 3.10 x64sc: on PAL, the display response reports the display
# window at row 51, but the buffer holds it at row 50. The PAL border fills rows 15-286
# for VICE's visible lines 16-287 (src/viciisc/vicii-timing.h), so PAL buffer row r
# holds raster line r + 1. On NTSC the reported offset and the buffer agree.
DISPLAY_ROW_CORRECTION = {"pal": -1}
# Wall-clock safety limit for one monitor reply. Emulated time is bounded by -limitcycles.
SOCKET_TIMEOUT = 120.0
CONNECT_ATTEMPTS = 200


class Launch(BaseModel):
    """Everything the x64sc command line needs."""

    model_config = ConfigDict(frozen=True)
    executable: str
    rom_directory: Path
    model: str
    sid: str
    port: int
    cycle_limit: int
    sound_log: Path | None = None
    wav: Path | None = None


class Plan(BaseModel):
    """Where to stop, what must never run, and what to type."""

    model_config = ConfigDict(frozen=True)
    program: Path
    checkpoint: int
    hit: int
    unreachable: tuple[int, ...] = ()
    feed_at: int | None = None
    feed: bytes = b""


class RomWindow(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str
    start: int
    end: int


# Where each ROM sits in the address space: Commodore 64 Programmer's Reference Guide,
# PDF 281 (memory map). The session reads them through VICE's "rom" bank.
ROM_WINDOWS = (
    RomWindow(role="basic", start=0xA000, end=0xBFFF),
    RomWindow(role="chargen", start=0xD000, end=0xDFFF),
    RomWindow(role="kernal", start=0xE000, end=0xFFFF),
)


class Capture(BaseModel):
    model_config = ConfigDict(frozen=True)
    vice_version: str
    reached: bool
    outcome: str
    hits: int = 0
    registers: dict[str, int] = {}
    ram: bytes = b""
    io: bytes = b""
    roms: dict[str, bytes] = {}
    machine: dict[str, str] = {}
    display: Display | None = None
    palette: list[tuple[int, int, int]] = []


def vice_arguments(launch: Launch) -> list[str]:
    """Factory settings, the verified ROM folder first, the declared model, monitor control."""
    sound = (
        [
            "-sound",
            "-sounddev",
            "dump",
            "-soundarg",
            str(launch.sound_log),
            "-soundrecdev",
            "wav",
            "-soundrecarg",
            str(launch.wav),
        ]
        if launch.wav and launch.sound_log
        else ["+sound"]
    )
    return [
        launch.executable,
        "-default",
        "-directory",
        f"{launch.rom_directory}:$$",
        "-model",
        launch.model,
        "-sidmodel",
        str(SID_MODEL_IDS[launch.sid]),
        "-binarymonitor",
        "-binarymonitoraddress",
        f"ip4://127.0.0.1:{launch.port}",
        "-autostart-warp",
        "-autostartprgmode",
        "1",
        "-limitcycles",
        str(launch.cycle_limit),
        "-minimized",
        *sound,
    ]


class ViceProcessGateway:
    """Start, connect to and stop the x64sc process."""

    def free_port(self) -> int:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]

    def start(self, command: list[str], log: Path) -> subprocess.Popen:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w") as stream:
            return subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)

    def connect(self, process: subprocess.Popen, port: int) -> MonitorConnection:
        for _ in range(CONNECT_ATTEMPTS):
            if process.poll() is not None:
                break
            try:
                return MonitorConnection(port, SOCKET_TIMEOUT)
            except OSError:
                try:
                    process.wait(timeout=0.05)
                except subprocess.TimeoutExpired:
                    continue
        raise MonitorError("VICE did not open its binary monitor; read the VICE log")

    def stop(self, process: subprocess.Popen) -> None:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def set_checkpoints(monitor: Monitor, plan: Plan) -> dict[int, str]:
    """Checkpoint numbers and their roles: stop, never, feed."""
    roles = {}
    for address, role in (
        (plan.checkpoint, "stop"),
        *((address, "never") for address in plan.unreachable),
        *(((plan.feed_at, "feed"),) if plan.feed_at is not None else ()),
    ):
        reply = monitor.request(Command.CHECKPOINT_SET, checkpoint_set(address))
        roles[parse_checkpoint(reply.body).number] = role
    return roles


def run_to_checkpoint(monitor: Monitor, plan: Plan, roles: dict[int, str]) -> tuple[bool, str, int]:
    """Continue after each stop until the planned hit, an unreachable hit or a jam."""
    hits, fed, pending = 0, False, None
    while True:
        event = monitor.next_event()
        if event.type == Event.CHECKPOINT:
            checkpoint = parse_checkpoint(event.body)
            pending = roles.get(checkpoint.number)
            if pending == "stop":
                hits = checkpoint.hit_count
            elif pending == "never":
                return False, f"reached the unreachable address ${checkpoint.start:04X}", hits
        elif event.type == Event.JAM:
            return False, f"the CPU jammed at ${int.from_bytes(event.body[:2], 'little'):04X}", hits
        elif event.type == Event.STOPPED:
            if pending == "stop" and hits >= plan.hit:
                return True, f"stopped at hit {hits}", hits
            if pending == "feed" and not fed:
                monitor.request(Command.KEYBOARD_FEED, keyboard_feed(plan.feed))
                fed = True
            pending = None
            monitor.request(Command.EXIT)


def read_memory(monitor: Monitor, start: int, end: int, bank: int) -> bytes:
    return parse_memory(monitor.request(Command.MEMORY_GET, memory_get(start, end, bank)).body)


def read_machine(monitor: Monitor) -> dict[str, str]:
    def value(name: str) -> int:
        return int(parse_resource(monitor.request(Command.RESOURCE_GET, resource_get(name)).body))

    return {
        "video": VIDEO_STANDARDS.get(value("MachineVideoStandard"), "unknown"),
        "vicii": VICII_MODELS.get(value("VICIIModel"), "unknown"),
        "sid": SID_MODELS.get(value("SidModel"), "unknown"),
    }


def corrected(display: Display, video: str) -> Display:
    shift = DISPLAY_ROW_CORRECTION.get(video, 0)
    return display.model_copy(update={"inner_y": display.inner_y + shift})


def collect(monitor: Monitor, names: dict[int, str], banks: dict[str, int]) -> dict[str, object]:
    machine = read_machine(monitor)
    registers = parse_registers(monitor.request(Command.REGISTERS_GET, b"\0").body, names)
    ram = read_memory(monitor, 0x0000, 0x7FFF, banks["ram"]) + read_memory(
        monitor, 0x8000, 0xFFFF, banks["ram"]
    )
    return {
        "registers": registers,
        "ram": ram,
        "io": read_memory(monitor, 0xD000, 0xDFFF, banks["io"]),
        "roms": {
            window.role: read_memory(monitor, window.start, window.end, banks["rom"])
            for window in ROM_WINDOWS
        },
        "machine": machine,
        "display": corrected(
            parse_display(monitor.request(Command.DISPLAY_GET, b"\1\0").body), machine["video"]
        ),
        "palette": parse_palette(monitor.request(Command.PALETTE_GET, b"\1").body),
    }


def drive(monitor: Monitor, plan: Plan) -> Capture:
    version = parse_vice_info(monitor.request(Command.VICE_INFO).body)
    banks = parse_banks(monitor.request(Command.BANKS_AVAILABLE).body)
    names = parse_register_names(monitor.request(Command.REGISTERS_AVAILABLE, b"\0").body)
    roles = set_checkpoints(monitor, plan)
    monitor.request(Command.AUTOSTART, autostart(str(plan.program.resolve())))
    monitor.request(Command.EXIT)
    # Events queued so far report the stops that the setup commands caused.
    monitor.events.clear()
    try:
        reached, outcome, hits = run_to_checkpoint(monitor, plan, roles)
    except MonitorError:
        return Capture(
            vice_version=version,
            reached=False,
            outcome="VICE stopped before the checkpoint; the cycle limit ended the run",
        )
    evidence = collect(monitor, names, banks)
    return Capture(vice_version=version, reached=reached, outcome=outcome, hits=hits, **evidence)


def session(
    launch: Launch, plan: Plan, log: Path, processes: ViceProcessGateway | None = None
) -> Capture:
    """Run one VICE process for one capture, and always stop it."""
    processes = processes or ViceProcessGateway()
    process = processes.start(vice_arguments(launch), log)
    connection = None
    try:
        connection = processes.connect(process, launch.port)
        monitor = Monitor(connection)
        capture = drive(monitor, plan)
        try:
            monitor.request(Command.QUIT)
        except MonitorError:
            pass
        return capture
    finally:
        if connection is not None:
            connection.close()
        processes.stop(process)

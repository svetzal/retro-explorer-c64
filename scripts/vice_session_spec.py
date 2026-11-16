"""Session decisions against a scripted monitor connection; the real VICE runs in c64_spec."""

import struct
from collections import deque
from pathlib import Path
from unittest.mock import Mock

import pytest
from vice_monitor import EVENT_REQUEST_ID, Command, Display, Event, MonitorConnection, MonitorError
from vice_session import (
    Launch,
    Plan,
    ViceProcessGateway,
    corrected,
    session,
    vice_arguments,
)

STOP, NEVER, FEED = 0x0834, 0x0835, 0x0820


def frame(kind: int, body: bytes = b"", request_id: int = EVENT_REQUEST_ID) -> bytes:
    return struct.pack("<BBIBBI", 2, 2, len(body), kind, 0, request_id) + body


def items(*entries: bytes) -> bytes:
    return struct.pack("<H", len(entries)) + b"".join(bytes([len(e)]) + e for e in entries)


def checkpoint_info(number: int, address: int, hits: int, hit: bool = True) -> bytes:
    return struct.pack(
        "<IBHHBBBBIIBB", number, int(hit), address, address, 1, 1, 4, 0, hits, 0, 0, 0
    )


class FakeVice:
    """Answer each command as VICE's binary monitor would, and play scripted runs."""

    def __init__(self, runs: list[list[bytes]], video: int = 1) -> None:
        self.runs = deque(runs)
        self.buffer = b""
        self.checkpoints: list[int] = []
        self.sent: list[tuple[int, bytes]] = []
        self.video = video

    def send(self, data: bytes) -> None:
        _, _, length, request_id, command = struct.unpack_from("<BBIIB", data)
        body = data[11 : 11 + length]
        self.sent.append((command, body))
        if command == Command.EXIT and self.runs:
            run = self.runs.popleft()
            self.buffer += frame(command, request_id=request_id) + b"".join(run)
            return
        self.buffer += frame(command, self.answer(command, body), request_id)

    def answer(self, command: int, body: bytes) -> bytes:
        if command == Command.CHECKPOINT_SET:
            (address,) = struct.unpack_from("<H", body)
            self.checkpoints.append(address)
            return checkpoint_info(len(self.checkpoints), address, 0, hit=False)
        if command == Command.MEMORY_GET:
            _, start, end = struct.unpack_from("<BHH", body)
            return struct.pack("<H", end - start + 1) + bytes(end - start + 1)
        return {
            Command.VICE_INFO: b"\x04\x03\x0a\x00\x00\x04\x00\x00\x00\x00",
            Command.BANKS_AVAILABLE: items(
                b"\x01\x00\x03ram", b"\x02\x00\x03rom", b"\x03\x00\x02io"
            ),
            Command.REGISTERS_AVAILABLE: items(b"\x03\x10\x02PC"),
            Command.REGISTERS_GET: items(b"\x03" + struct.pack("<H", STOP)),
            Command.RESOURCE_GET: b"\x01\x04" + struct.pack("<I", self.video),
            Command.DISPLAY_GET: struct.pack("<IHHHHHHBI", 13, 2, 2, 0, 1, 1, 1, 8, 4) + bytes(4),
            Command.PALETTE_GET: items(b"\x00\x00\x00"),
        }.get(command, b"")

    def receive(self, size: int) -> bytes:
        if len(self.buffer) < size:
            raise MonitorError("VICE closed the monitor connection")
        chunk, self.buffer = self.buffer[:size], self.buffer[size:]
        return chunk


def hit(number: int, address: int, count: int) -> list[bytes]:
    return [
        frame(Event.CHECKPOINT, checkpoint_info(number, address, count)),
        frame(Event.STOPPED, struct.pack("<H", address)),
    ]


@pytest.fixture
def plan(tmp_path: Path) -> Plan:
    return Plan(program=tmp_path / "main.prg", checkpoint=STOP, hit=2, unreachable=(NEVER,))


@pytest.fixture
def launch(tmp_path: Path) -> Launch:
    return Launch(
        executable="x64sc",
        rom_directory=tmp_path / "roms",
        model="c64",
        sid="6581",
        port=6502,
        cycle_limit=1000,
    )


def run(fake: FakeVice, launch: Launch, plan: Plan, tmp_path: Path):
    connection = Mock(spec=MonitorConnection)
    connection.send.side_effect = fake.send
    connection.receive.side_effect = fake.receive
    processes = Mock(spec=ViceProcessGateway)
    processes.connect.return_value = connection
    capture = session(launch, plan, tmp_path / "vice.log", processes)
    processes.stop.assert_called_once()
    connection.close.assert_called_once()
    return capture


class DescribeViceArguments:
    def should_put_the_verified_rom_folder_first_and_bound_the_run(self, launch: Launch) -> None:
        arguments = vice_arguments(launch)

        assert arguments[arguments.index("-directory") + 1] == f"{launch.rom_directory}:$$"
        assert arguments[arguments.index("-limitcycles") + 1] == "1000"
        assert arguments[arguments.index("-sidmodel") + 1] == "0"
        assert "+sound" in arguments
        assert "-warp" not in arguments  # warp skips rendered frames (vsync.c)

    def should_record_sound_only_when_paths_are_given(self, launch: Launch, tmp_path: Path) -> None:
        recording = launch.model_copy(
            update={"wav": tmp_path / "s.wav", "sound_log": tmp_path / "s.txt"}
        )

        arguments = vice_arguments(recording)

        assert arguments[arguments.index("-soundrecdev") + 1] == "wav"
        assert arguments[arguments.index("-soundarg") + 1] == str(tmp_path / "s.txt")


class DescribeDisplayCorrection:
    def should_move_the_pal_window_up_one_row_and_leave_ntsc(self) -> None:
        display = Display(
            width=1,
            height=1,
            inner_x=0,
            inner_y=51,
            inner_width=1,
            inner_height=1,
            pixels=b"\0",
            missing=0,
        )

        assert corrected(display, "pal").inner_y == 50
        assert corrected(display, "ntsc").inner_y == 51


class DescribeSession:
    def should_continue_until_the_planned_hit_then_collect(self, launch, plan, tmp_path) -> None:
        fake = FakeVice([[frame(Event.STOPPED, b"\0\0")], hit(1, STOP, 1), hit(1, STOP, 2)])

        capture = run(fake, launch, plan, tmp_path)

        assert capture.reached and capture.hits == 2
        assert capture.registers == {"PC": STOP}
        assert len(capture.ram) == 0x10000 and len(capture.io) == 0x1000
        assert set(capture.roms) == {"basic", "chargen", "kernal"}
        assert capture.machine == {"video": "pal", "vicii": "8565", "sid": "8580"}
        assert capture.display.inner_y == 0  # reported row 1, corrected for PAL
        assert fake.checkpoints == [STOP, NEVER]
        assert fake.sent[-1][0] == Command.QUIT

    def should_fail_when_an_unreachable_address_runs(self, launch, plan, tmp_path) -> None:
        fake = FakeVice([hit(2, NEVER, 1)])

        capture = run(fake, launch, plan, tmp_path)

        assert not capture.reached
        assert capture.outcome == "reached the unreachable address $0835"

    def should_fail_when_the_cpu_jams(self, launch, plan, tmp_path) -> None:
        fake = FakeVice([[frame(Event.JAM, b"\x02\x08")]])

        assert run(fake, launch, plan, tmp_path).outcome == "the CPU jammed at $0802"

    def should_report_the_cycle_limit_when_vice_exits_first(self, launch, plan, tmp_path) -> None:
        fake = FakeVice([hit(1, STOP, 1)])

        capture = run(fake, launch, plan, tmp_path)

        assert not capture.reached and "cycle limit" in capture.outcome
        assert capture.ram == b""

    def should_type_the_input_once_at_its_label(self, launch, plan, tmp_path) -> None:
        typing = plan.model_copy(update={"feed_at": FEED, "feed": b"GO", "hit": 1})
        fake = FakeVice([hit(3, FEED, 1), hit(3, FEED, 2), hit(1, STOP, 1)])

        capture = run(fake, launch, typing, tmp_path)

        feeds = [body for command, body in fake.sent if command == Command.KEYBOARD_FEED]
        assert capture.reached and feeds == [b"\x02GO"]

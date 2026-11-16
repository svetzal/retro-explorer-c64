"""A client for the VICE binary monitor protocol, API version 2.

The message layouts follow the VICE manual, chapter 13 "Binary monitor"
(https://vice-emu.sourceforge.io/vice_13.html), read for VICE 3.10.
"""

import socket
import struct
from collections import deque
from enum import IntEnum

from pydantic import BaseModel, ConfigDict

STX = 0x02
API_VERSION = 0x02
EVENT_REQUEST_ID = 0xFFFFFFFF
HEADER = struct.Struct("<BBIBBI")  # STX, API, body length, type, error, request ID
COMMAND_HEADER = struct.Struct("<BBIIB")  # STX, API, body length, request ID, command


class Command(IntEnum):
    MEMORY_GET = 0x01
    CHECKPOINT_SET = 0x12
    REGISTERS_GET = 0x31
    RESOURCE_GET = 0x51
    KEYBOARD_FEED = 0x72
    BANKS_AVAILABLE = 0x82
    REGISTERS_AVAILABLE = 0x83
    DISPLAY_GET = 0x84
    VICE_INFO = 0x85
    PALETTE_GET = 0x91
    EXIT = 0xAA
    QUIT = 0xBB
    AUTOSTART = 0xDD


class Event(IntEnum):
    CHECKPOINT = 0x11
    REGISTERS = 0x31
    JAM = 0x61
    STOPPED = 0x62
    RESUMED = 0x63


class Operation(IntEnum):
    LOAD = 0x01
    STORE = 0x02
    EXEC = 0x04


class MonitorError(RuntimeError):
    """VICE refused a command, or the connection ended."""


class Response(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: int
    error: int
    request_id: int
    body: bytes

    @property
    def is_event(self) -> bool:
        return self.request_id == EVENT_REQUEST_ID


class Checkpoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    number: int
    hit: bool
    start: int
    end: int
    hit_count: int


class Display(BaseModel):
    """VICE's indexed frame buffer, the whole uncropped area, and its inner window."""

    model_config = ConfigDict(frozen=True)
    width: int
    height: int
    inner_x: int
    inner_y: int
    inner_width: int
    inner_height: int
    pixels: bytes
    missing: int


def encode(request_id: int, command: int, body: bytes = b"") -> bytes:
    return COMMAND_HEADER.pack(STX, API_VERSION, len(body), request_id, command) + body


def decode_header(header: bytes) -> tuple[int, int, int, int]:
    """Body length, type, error and request ID of a response header."""
    stx, api, length, kind, error, request_id = HEADER.unpack(header)
    if stx != STX or api != API_VERSION:
        raise MonitorError(f"Unexpected response header {header.hex()}")
    return length, kind, error, request_id


def memory_get(start: int, end: int, bank: int, side_effects: bool = False) -> bytes:
    return struct.pack("<BHHBH", int(side_effects), start, end, 0, bank)


def checkpoint_set(address: int, operation: Operation = Operation.EXEC) -> bytes:
    """A stopping, enabled, permanent checkpoint on one address in main memory."""
    return struct.pack("<HHBBBBB", address, address, 1, 1, operation, 0, 0)


def autostart(path: str, run: bool = True) -> bytes:
    name = path.encode()
    if len(name) > 255:
        raise ValueError(f"Path too long for the autostart command: {path}")
    return struct.pack("<BHB", int(run), 0, len(name)) + name


def keyboard_feed(petscii: bytes) -> bytes:
    if len(petscii) > 255:
        raise ValueError("Keyboard feed text is limited to 255 bytes")
    return bytes([len(petscii)]) + petscii


def resource_get(name: str) -> bytes:
    encoded = name.encode()
    return bytes([len(encoded)]) + encoded


def parse_memory(body: bytes) -> bytes:
    (length,) = struct.unpack_from("<H", body)
    data = body[2:]
    if length and len(data) != length:
        raise MonitorError(f"Memory response holds {len(data)} bytes, header says {length}")
    return data


def parse_checkpoint(body: bytes) -> Checkpoint:
    number, hit, start, end = struct.unpack_from("<IBHH", body)
    (hit_count,) = struct.unpack_from("<I", body, 13)
    return Checkpoint(number=number, hit=bool(hit), start=start, end=end, hit_count=hit_count)


def parse_items(body: bytes) -> list[bytes]:
    """A count-prefixed array whose items each start with their own size."""
    (count,) = struct.unpack_from("<H", body)
    items, offset = [], 2
    for _ in range(count):
        size = body[offset]
        items.append(body[offset + 1 : offset + 1 + size])
        offset += 1 + size
    return items


def parse_banks(body: bytes) -> dict[str, int]:
    banks = {}
    for item in parse_items(body):
        (bank,) = struct.unpack_from("<H", item)
        banks[item[3 : 3 + item[2]].decode()] = bank
    return banks


def parse_register_names(body: bytes) -> dict[int, str]:
    return {item[0]: item[3 : 3 + item[2]].decode() for item in parse_items(body)}


def parse_registers(body: bytes, names: dict[int, str]) -> dict[str, int]:
    values = {}
    for item in parse_items(body):
        (value,) = struct.unpack_from("<H", item, 1)
        values[names.get(item[0], f"id{item[0]}")] = value
    return values


def parse_resource(body: bytes) -> str | int:
    kind, length = body[0], body[1]
    value = body[2 : 2 + length]
    return value.decode() if kind == 0 else int.from_bytes(value, "little")


def parse_vice_info(body: bytes) -> str:
    length = body[0]
    return ".".join(str(part) for part in body[1 : 1 + length])


def parse_palette(body: bytes) -> list[tuple[int, int, int]]:
    return [(item[0], item[1], item[2]) for item in parse_items(body)]


def parse_display(body: bytes) -> Display:
    """Parse a display response.

    VICE 3.10 counts the response length without the 4-byte buffer length field
    (src/monitor/monitor_binary.c, monitor_binary_process_display_get), so it sends
    4 bytes fewer than the buffer holds. The last pixels are missing; they are in the
    bottom-right corner of the uncropped buffer, outside the visible area.
    """
    (info_length,) = struct.unpack_from("<I", body)
    width, height, inner_x, inner_y, inner_width, inner_height, depth = struct.unpack_from(
        "<HHHHHHB", body, 4
    )
    if depth != 8:
        raise MonitorError(f"Unexpected display depth {depth}")
    start = 4 + info_length
    (buffer_length,) = struct.unpack_from("<I", body, start)
    pixels = body[start + 4 : start + 4 + buffer_length]
    missing = width * height - len(pixels)
    return Display(
        width=width,
        height=height,
        inner_x=inner_x,
        inner_y=inner_y,
        inner_width=inner_width,
        inner_height=inner_height,
        pixels=pixels + bytes(missing),
        missing=missing,
    )


class MonitorConnection:
    """The TCP socket to VICE's binary monitor."""

    def __init__(self, port: int, timeout: float) -> None:
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=timeout)

    def send(self, data: bytes) -> None:
        self.socket.sendall(data)

    def receive(self, size: int) -> bytes:
        """Exactly size bytes; raises MonitorError when VICE closes the connection."""
        chunks, remaining = [], size
        while remaining:
            try:
                chunk = self.socket.recv(remaining)
            except OSError as error:  # reset when VICE exits, or the wall-clock timeout
                raise MonitorError(f"VICE monitor connection failed: {error}") from error
            if not chunk:
                raise MonitorError("VICE closed the monitor connection")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        self.socket.close()


class Monitor:
    """Match each command with its response and queue the events that arrive between them."""

    def __init__(self, connection: MonitorConnection) -> None:
        self.connection = connection
        self.events: deque[Response] = deque()
        self.request_id = 0

    def read(self) -> Response:
        length, kind, error, request_id = decode_header(self.connection.receive(HEADER.size))
        body = self.connection.receive(length) if length else b""
        return Response(type=kind, error=error, request_id=request_id, body=body)

    def request(self, command: Command, body: bytes = b"") -> Response:
        self.request_id += 1
        self.connection.send(encode(self.request_id, command, body))
        while True:
            response = self.read()
            if response.request_id == self.request_id:
                if response.error:
                    raise MonitorError(
                        f"VICE refused command 0x{command:02x} with error 0x{response.error:02x}"
                    )
                return response
            self.events.append(response)

    def next_event(self) -> Response:
        return self.events.popleft() if self.events else self.read()

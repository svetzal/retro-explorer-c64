"""The binary monitor codec and request matching, against the layouts in the VICE manual."""

import struct
from unittest.mock import Mock

import pytest
from vice_monitor import (
    EVENT_REQUEST_ID,
    Command,
    Event,
    Monitor,
    MonitorConnection,
    MonitorError,
    Operation,
    autostart,
    checkpoint_set,
    decode_header,
    encode,
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


def response(kind: int, body: bytes = b"", request_id: int = 1, error: int = 0) -> bytes:
    return struct.pack("<BBIBBI", 2, 2, len(body), kind, error, request_id) + body


def items(*entries: bytes) -> bytes:
    return struct.pack("<H", len(entries)) + b"".join(bytes([len(e)]) + e for e in entries)


class ScriptedConnection:
    """Bytes that VICE would send, served to the monitor's receive calls."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def receive(self, size: int) -> bytes:
        if len(self.data) < size:
            raise MonitorError("VICE closed the monitor connection")
        chunk, self.data = self.data[:size], self.data[size:]
        return chunk


@pytest.fixture
def connection() -> Mock:
    return Mock(spec=MonitorConnection)


def serve(connection: Mock, data: bytes) -> None:
    connection.receive.side_effect = ScriptedConnection(data).receive


class DescribeCommandEncoding:
    def should_match_the_manual_example_for_a_temporary_checkpoint(self) -> None:
        body = struct.pack("<HHBBBB", 0xFCE2, 0xFCE3, 1, 1, 4, 1)

        encoded = encode(0x1234DEAD, Command.CHECKPOINT_SET, body)

        assert encoded.hex(" ") == "02 02 08 00 00 00 ad de 34 12 12 e2 fc e3 fc 01 01 04 01"

    def should_set_a_stopping_enabled_permanent_checkpoint_in_main_memory(self) -> None:
        assert checkpoint_set(0x0834) == bytes.fromhex("3408 3408 01 01 04 00 00")
        assert checkpoint_set(0xC000, Operation.STORE)[4:7] == bytes([1, 1, 2])

    def should_encode_memory_requests_without_side_effects(self) -> None:
        assert memory_get(0xD000, 0xDFFF, 3) == bytes.fromhex("00 00d0 ffdf 00 0300")

    def should_prefix_names_and_text_with_their_length(self) -> None:
        assert resource_get("SidModel") == b"\x08SidModel"
        assert keyboard_feed(b"A") == b"\x01A"
        assert autostart("/tmp/x.prg") == bytes([1, 0, 0, 10]) + b"/tmp/x.prg"

    @pytest.mark.parametrize(
        "call", [lambda: keyboard_feed(b"A" * 256), lambda: autostart("x" * 256)]
    )
    def should_reject_text_longer_than_one_length_byte(self, call) -> None:
        with pytest.raises(ValueError):
            call()


class DescribeResponseParsing:
    def should_reject_a_header_from_another_protocol(self) -> None:
        with pytest.raises(MonitorError):
            decode_header(bytes(12))

    def should_read_the_manual_example_checkpoint_response(self) -> None:
        body = bytes.fromhex("02000000 00 e2fc e3fc 01 01 04 01 05000000 00000000 00 00")

        checkpoint = parse_checkpoint(body)

        assert (checkpoint.number, checkpoint.hit, checkpoint.start) == (2, False, 0xFCE2)
        assert checkpoint.hit_count == 5

    def should_name_registers_with_the_ids_vice_reports(self) -> None:
        names = parse_register_names(items(b"\x03\x10\x02PC", b"\x00\x08\x01A"))
        values = items(b"\x03\xcf\xe5", b"\x00\x2a\x00", b"\x09\x01\x00")

        assert parse_registers(values, names) == {"PC": 0xE5CF, "A": 0x2A, "id9": 1}

    def should_map_bank_names_to_ids(self) -> None:
        body = items(b"\x00\x00\x03cpu", b"\x01\x00\x03ram", b"\x03\x00\x02io")

        assert parse_banks(body) == {"cpu": 0, "ram": 1, "io": 3}

    def should_read_memory_and_check_its_length(self) -> None:
        assert parse_memory(b"\x02\x00\xaa\xbb") == b"\xaa\xbb"
        with pytest.raises(MonitorError):
            parse_memory(b"\x03\x00\xaa")

    def should_read_string_and_integer_resources(self) -> None:
        assert parse_resource(b"\x00\x03abc") == "abc"
        assert parse_resource(b"\x01\x04\x02\x00\x00\x00") == 2

    def should_join_version_parts(self) -> None:
        assert parse_vice_info(b"\x04\x03\x0a\x00\x00\x04\x00\x00\x00\x00") == "3.10.0.0"

    def should_read_palette_entries(self) -> None:
        assert parse_palette(items(b"\x00\x00\x00", b"\xff\xff\xff")) == [
            (0, 0, 0),
            (255, 255, 255),
        ]

    def should_pad_the_pixels_that_vice_does_not_send(self) -> None:
        header = struct.pack("<IHHHHHHB", 13, 4, 3, 1, 1, 2, 1, 8)
        sent = bytes(range(8))  # the buffer holds 12 pixels; VICE 3.10 sends 4 fewer

        display = parse_display(header + struct.pack("<I", 12) + sent)

        assert (display.width, display.height, display.inner_x, display.inner_width) == (4, 3, 1, 2)
        assert display.pixels == sent + bytes(4)
        assert display.missing == 4

    def should_reject_an_unknown_pixel_depth(self) -> None:
        header = struct.pack("<IHHHHHHB", 13, 1, 1, 0, 0, 1, 1, 16)

        with pytest.raises(MonitorError):
            parse_display(header + struct.pack("<I", 2) + b"\0\0")


class DescribeMonitor:
    def should_return_the_matching_response_and_queue_events(self, connection: Mock) -> None:
        event = response(Event.STOPPED, b"\x34\x08", EVENT_REQUEST_ID)
        serve(connection, event + response(Command.VICE_INFO, b"\x01\x03\x00", 1))
        monitor = Monitor(connection)

        reply = monitor.request(Command.VICE_INFO)

        connection.send.assert_called_once_with(encode(1, Command.VICE_INFO))
        assert reply.type == Command.VICE_INFO
        queued = monitor.next_event()
        assert queued.is_event and queued.type == Event.STOPPED

    def should_read_the_next_event_from_the_connection_when_none_is_queued(
        self, connection: Mock
    ) -> None:
        serve(connection, response(Event.RESUMED, b"\x00\x08", EVENT_REQUEST_ID))

        assert Monitor(connection).next_event().type == Event.RESUMED

    def should_raise_when_vice_refuses_a_command(self, connection: Mock) -> None:
        serve(connection, response(Command.MEMORY_GET, request_id=1, error=0x81))

        with pytest.raises(MonitorError, match="error 0x81"):
            Monitor(connection).request(Command.MEMORY_GET, memory_get(0, 1, 0))

    def should_raise_when_vice_closes_the_connection(self, connection: Mock) -> None:
        serve(connection, b"\x02\x02")

        with pytest.raises(MonitorError, match="closed"):
            Monitor(connection).request(Command.PALETTE_GET, b"\1")

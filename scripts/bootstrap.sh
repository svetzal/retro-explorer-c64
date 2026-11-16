#!/bin/sh
# Prepare the host-side environment without requiring Python in advance.
set -eu

case "${1:-}" in
    c64-ntsc|c64-pal) target=$1 ;;
    -h|--help)
        echo 'Usage: sh scripts/bootstrap.sh c64-ntsc|c64-pal'
        echo 'Prepare Python, 64tass, VICE, verified firmware and the reference index.'
        echo 'Missing uv is installed with Homebrew when available, otherwise its official installer.'
        exit 0 ;;
    *) echo 'Choose a machine: sh scripts/bootstrap.sh c64-ntsc|c64-pal' >&2; exit 2 ;;
esac
if [ "$#" -ne 1 ]; then
    echo 'Supply exactly one machine target.' >&2
    exit 2
fi
if [ "$(uname -s)" = Darwin ] && [ "$(uname -m)" != arm64 ]; then
    echo 'macOS requires Apple Silicon (arm64); Intel Macs are unsupported. Use a native arm64 terminal on Apple Silicon, or Ubuntu 24.04. See guidance/starter/toolchain.md#supported-hosts.' >&2
    exit 1
fi
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

if ! command -v uv >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        echo 'Installing uv with Homebrew.'
        brew install uv
    else
        if ! command -v curl >/dev/null 2>&1; then
            if ! command -v apt-get >/dev/null 2>&1; then
                echo 'curl is missing. Install curl and CA certificates with your system package manager, then rerun bootstrap.' >&2
                exit 1
            fi
            if [ "$(id -u)" -eq 0 ]; then
                set --
            elif command -v sudo >/dev/null 2>&1; then
                set -- sudo -n
            else
                echo 'Installing curl requires root or non-interactive sudo. Ask an administrator to install curl and ca-certificates, then rerun bootstrap.' >&2
                exit 1
            fi
            echo 'Installing curl and CA certificates with apt.'
            if ! "$@" apt-get update || ! "$@" apt-get install -y curl ca-certificates; then
                echo 'Could not install curl and ca-certificates. Resolve the apt error above and ensure root or non-interactive sudo access, then rerun bootstrap.' >&2
                exit 1
            fi
        fi
        echo 'Installing uv with its official installer.'
        installer=$(mktemp)
        trap 'rm -f "$installer"' EXIT HUP INT TERM
        curl --fail --location --silent --show-error https://astral.sh/uv/install.sh -o "$installer"
        UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$installer"
        PATH="$HOME/.local/bin:$PATH"
        export PATH
    fi
fi

printf 'For later commands, uv is at: %s\n' "$(command -v uv)"
echo 'Preparing the project Python environment. The first run can take a while.'
uv sync --locked
echo 'Writing the local reference index without downloading or converting references.'
uv run python scripts/setup.py --target "$target" --guidance-only
echo 'Installing missing assembler and emulator tools.'
uv run python scripts/native.py
echo 'Placing and verifying the firmware for the selected target.'
uv run python scripts/setup.py --target "$target" --firmware-only
echo 'Checking tools and firmware.'
uv run python scripts/doctor.py --target "$target"
echo 'Tools and firmware are ready. Run an example check before you open the emulator.'

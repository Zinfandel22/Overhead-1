#!/usr/bin/env python3
"""Build a full-flash factory image for the CYD 3.5-inch USB-C target."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    project_dir = Path(__file__).resolve().parent.parent
    core_dir = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=project_dir / ".pio" / "build" / "cyd35_usbc",
    )
    parser.add_argument(
        "--esptool",
        type=Path,
        default=core_dir / "packages" / "tool-esptoolpy" / "esptool.py",
    )
    args = parser.parse_args()

    build_dir = args.build_dir.resolve()
    output = build_dir / "cyd35_usbc_merged.bin"
    images = [
        ("0x1000", build_dir / "bootloader.bin"),
        ("0x8000", build_dir / "partitions.bin"),
        ("0xe000", project_dir / "docs" / "flash" / "boot_app0.bin"),
        ("0x10000", build_dir / "firmware.bin"),
        ("0x390000", build_dir / "littlefs.bin"),
    ]

    for _, image in images:
        if not image.is_file():
            raise FileNotFoundError("Factory image input is missing: {}".format(image))

    command = [
        sys.executable,
        str(args.esptool.resolve()),
        "--chip",
        "esp32",
        "merge_bin",
        "--output",
        str(output),
        "--flash_mode",
        "dio",
        "--flash_freq",
        "40m",
        "--flash_size",
        "4MB",
        "--fill-flash-size",
        "4MB",
    ]
    for offset, image in images:
        command.extend((offset, str(image)))

    subprocess.check_call(command)
    print("[merge_factory] wrote {} ({} bytes)".format(output, output.stat().st_size))


if __name__ == "__main__":
    main()

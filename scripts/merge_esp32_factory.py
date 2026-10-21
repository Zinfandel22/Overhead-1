#!/usr/bin/env python3
"""Build a full-flash (4 MB) factory image: bootloader + partitions + boot_app0 +
firmware + LittleFS, flashable at offset 0.

Two entry points:
  * PlatformIO post-script (extra_scripts = post:scripts/merge_esp32_factory.py):
    every `pio run` also builds littlefs.bin and <env>_merged.bin.
  * Standalone: python scripts/merge_esp32_factory.py [--build-dir DIR]
"""
import os
import subprocess
import sys
from pathlib import Path

FS_OFFSET = "0x390000"   # spiffs partition in partitions.csv


def merge(build_dir, project_dir, esptool, python, output):
    images = [
        ("0x1000", build_dir / "bootloader.bin"),
        ("0x8000", build_dir / "partitions.bin"),
        ("0xe000", project_dir / "docs" / "flash" / "boot_app0.bin"),
        ("0x10000", build_dir / "firmware.bin"),
        (FS_OFFSET, build_dir / "littlefs.bin"),
    ]
    for _, image in images:
        if not image.is_file():
            raise FileNotFoundError("Factory image input is missing: {}".format(image))

    command = [python, str(esptool), "--chip", "esp32", "merge_bin",
               "--output", str(output),
               "--flash_mode", "dio", "--flash_freq", "40m",
               "--flash_size", "4MB", "--fill-flash-size", "4MB"]
    for offset, image in images:
        command.extend((offset, str(image)))
    subprocess.check_call(command)
    print("[merge_factory] wrote {} ({} bytes)".format(output, output.stat().st_size))


try:
    Import("env")  # noqa: F821  (only defined when run by PlatformIO/SCons)
except NameError:
    env = None

if env is not None:
    build_dir = Path(env.subst("$BUILD_DIR"))
    project_dir = Path(env.subst("$PROJECT_DIR"))
    merged = build_dir / "{}_merged.bin".format(env["PIOENV"])
    esptool = Path(env.PioPlatform().get_package_dir("tool-esptoolpy")) / "esptool.py"

    # Build the LittleFS image (data/) as a dependency; `pio run` skips it by default.
    fs_bin = env.DataToBin(str(build_dir / "littlefs.bin"), "$PROJECT_DATA_DIR")
    env.NoCache(fs_bin)

    def _merge_action(target, source, env):
        merge(build_dir, project_dir, esptool, env.subst("$PYTHONEXE"), merged)

    target = env.Command(str(merged), [str(build_dir / "firmware.bin"), fs_bin],
                         env.VerboseAction(_merge_action, "Merging factory image " + merged.name))
    env.Default(target)
else:
    import argparse
    project_dir = Path(__file__).resolve().parent.parent
    core_dir = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path,
                        default=project_dir / ".pio" / "build" / "cyd35_usbc")
    parser.add_argument("--esptool", type=Path,
                        default=core_dir / "packages" / "tool-esptoolpy" / "esptool.py")
    args = parser.parse_args()
    bdir = args.build_dir.resolve()
    merge(bdir, project_dir, args.esptool.resolve(), sys.executable,
          bdir / "{}_merged.bin".format(bdir.name))

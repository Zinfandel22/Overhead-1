# HARDWARE_SETUP.md — build, flash & wire Overhead

Everything you need to go from a bare board to a running [Overhead](README.md)
dashboard. The README is the showcase; this is the "boring but necessary" detail.

---

## Supported targets

| Target | PlatformIO env | Display | MCU | Status |
|---|---|---|---|---|
| **2.8" CYD** (ESP32-2432S028R) | `cyd28_ili9341` | 2.8" ILI9341, 320×240, resistive | ESP32-WROOM (no PSRAM) | ✅ **verified** |
| 4" CYD | `cyd4_st7796` | 4" ST7796 | ESP32-WROOM | ⚠️ WIP (untested on hw) |
| 3.5" CYD USB-C (ESP32-3248S035R) | `cyd35_usbc` | 3.5" ST7796, 480×320 | ESP32-WROOM (no PSRAM) | ⚠️ running; also emits a merged 4 MB image (`.pio/build/cyd35_usbc/cyd35_usbc_merged.bin`, flash at 0x0) |
| CrowPanel 5" HMI | `crowpanel_s3_5hmi` | 5" parallel-RGB | ESP32-S3 (PSRAM) | ⚠️ WIP (untested on hw) |

The 2.8" CYD is the reference build. The other two compile and are board-conditional
(see `src/hal/Board.h`) but haven't been validated on real hardware yet.

## Bill of materials (2.8" CYD)

- **ESP32-2432S028R "Cheap Yellow Display"** — 2.8" ILI9341 LCD + XPT2046 resistive
  touch + microSD + LDR + RGB LED, ~$10–15 (AliExpress / Amazon). Two revisions exist
  (single micro-USB, and dual USB-C+micro); the dual-USB ILI9341 has reversed R/B
  wiring — set `CYD_PANEL_RGB_ORDER 1` for it (see below).
- **USB cable** matching your board's port (micro-USB or USB-C).
- A **5 V USB supply** (any phone charger) for always-on shelf use.
- *Optional:* a DS3231/PCF8563 **RTC** on the free I²C header (GPIO 27 SDA / 22 SCL) —
  the firmware currently runs NTP-only, RTC driver is a stub.

No soldering required for the base build — it's a self-contained dev board.

## Toolchain

PlatformIO is the build system. **The CLI is not on your PATH** when installed via the
VS Code extension — invoke it from the venv (see [PIO_DEBUG.md](PIO_DEBUG.md)):

```
# Windows (this project's environment)
C:/Users/<you>/.platformio/penv/Scripts/platformio.exe run -e cyd28_ili9341
# macOS/Linux
~/.platformio/penv/bin/platformio run -e cyd28_ili9341
```

1. Install **PlatformIO** (VS Code extension, or `pip install platformio`).
2. `git clone <repo>` and open the folder.
3. Build: `platformio run -e cyd28_ili9341`. First build pulls the libraries
   (LovyanGFX, ArduinoJson, SGP4, JPEGENC, ElegantOTA, ESPAsyncWebServer, WiFiManager).
4. **ESP32-S3 env only:** the pioarduino platform's install glitches with
   `No module named 'esptool'`. Fix once:
   `~/.platformio/penv/Scripts/python.exe -m pip install esptool==5.3.0`.

> The classic CYD envs (`cyd28`, `cyd4`) stay on `espressif32 @ 6.9.0` (arduino-esp32
> 2.0.x) — 3.x leaves too little heap for the TLS reads on a no-PSRAM board. Only the
> PSRAM CrowPanel uses pioarduino (arduino-esp32 3.x). See `platformio.ini`.

## First flash (USB)

1. Connect the board over USB (it enumerates as a CH340 serial port — **COM5** on the
   dev machine).
2. `platformio run -e cyd28_ili9341 -t upload`.
3. On first boot the touch panel runs a **4-corner calibration** — tap the crosshairs.
4. It then opens a WiFi **captive portal**: join the `Overhead-Setup-XXXX` access point,
   pick your network, enter the password. It saves the creds and reboots.
   *(No WiFi handy? Tap the screen at the portal to boot straight into **offline field
   mode** on cached data.)*
5. It IP-geolocates, syncs NTP, and starts pulling feeds. Watch the serial console at
   `115200` baud, or open `http://overhead-XXXX.local/` (or the LAN IP).

## Over-the-air updates

After the first USB flash, update over WiFi — no cable:

- **Script:** `pwsh -NoProfile -File scripts/ota.ps1` (MD5 + ElegantOTA v3 upload,
  basic-auth `admin`/`overhead`).
- **Browser:** `http://<device>/update` (ElegantOTA).
- OTA can flake (`upload=100` then `400`) when the AsyncTCP task is busy — let the
  device **boot-settle ~20 s** or two-tap **Reboot** on Health, then retry.

## Board quirks (read before changing display / touch / screenshot / WiFi code)

The hard-won details — display orientation (MV=0 rotation 6), touch calibration
inversion, the dual-USB R/B colour fix, the JPEG screenshot colour readback, the
no-PSRAM TLS heap budget, the LittleFS `spiffs` partition-label gotcha, OTA/WiFi
recovery — are all in **[CYD-ESP32-2432S028R.md](CYD-ESP32-2432S028R.md)**.

## Troubleshooting

- **Mirrored / 90°-rotated / wrong-colour display:** orientation + RGB-order fix in
  `CYD-ESP32-2432S028R.md` (it's the rotation/`CYD_PANEL_RGB_ORDER`, not your drawing).
- **Device unreachable over WiFi** (`/api/status` times out, `ota.ps1` returns
  `upload=000`): the radio wedged. Hard-reset over USB serial —
  `~/.platformio/penv/Scripts/python.exe -m esptool --port COM5 --before default_reset --after hard_reset flash_id`
  — wait ~18 s for boot + WiFi rejoin, then OTA normally.
- **Feeds stuck "stale" / `httpsSkip` climbing:** the no-PSRAM TLS heap floor — the
  binding constraint. See the no-PSRAM budget section in `CYD-ESP32-2432S028R.md`.
- **Touch off / inverted:** re-run calibration from **Health → Recalibrate**.
- **Settings/cache writes silently fail:** the data partition must be labelled `spiffs`
  (see `partitions.csv` and the LittleFS note in `CYD-ESP32-2432S028R.md`).

See **[PIO_DEBUG.md](PIO_DEBUG.md)** for the autonomous build → flash → screenshot →
tap remote-debug loop.

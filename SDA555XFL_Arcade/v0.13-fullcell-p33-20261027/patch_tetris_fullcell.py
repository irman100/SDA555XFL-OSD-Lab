#!/usr/bin/env python3
"""Patch the 420-byte Tetris DRCS upload stream in an existing SDA555XFL BIN.

This intentionally does NOT assemble or regenerate the game. The supplied
Arcade v0.12 P3.3 image already contains 420 MOV-immediate stores that upload
seven 12x10 4-bpp glyphs to XRAM at 0xCA16. We replace only those immediate
operands while preserving opcodes, addresses, code size, Pong and launcher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zlib
from pathlib import Path

FLASH_SIZE = 128 * 1024
STORE_START = 0x013B  # first MOV A,#imm after MOV DPTR,#0xCA16
STORE_COUNT = 420     # 7 glyphs * 60 bytes per 12x10 4-bpp glyph
STORE_STRIDE = 4      # 74 imm / F0 / A3
STORE_END = STORE_START + STORE_COUNT * STORE_STRIDE  # exclusive, 0x07CB
EXPECTED_INPUT_SHA256 = "09f59d40672278b5ccd56c241f769ed6bf4c55b191a7e18727e63c2ac1065896"
EXPECTED_DRCS_SHA256 = "a5a3899e6a6b0592be8a4f7351a0d7b478fd0444925dc112d49b1cd4b23129e7"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def crc32(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08X}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="original Arcade v0.12 P3.3 BIN")
    parser.add_argument("--drcs", required=True, type=Path, help="exactly 420 bytes of 4-bpp DRCS data")
    parser.add_argument("--output", required=True, type=Path, help="new patched BIN (never overwrite input)")
    parser.add_argument("--report", type=Path, help="optional JSON report path")
    args = parser.parse_args()

    source = args.input.read_bytes()
    drcs = args.drcs.read_bytes()
    if len(source) != FLASH_SIZE:
        raise SystemExit(f"STOP: firmware size is {len(source)} bytes, expected {FLASH_SIZE}")
    source_sha = sha256(source)
    if source_sha != EXPECTED_INPUT_SHA256:
        raise SystemExit(f"STOP: unexpected input SHA-256 {source_sha}; expected {EXPECTED_INPUT_SHA256}")
    if len(drcs) != STORE_COUNT:
        raise SystemExit(f"STOP: DRCS payload is {len(drcs)} bytes, expected {STORE_COUNT}")
    drcs_sha = sha256(drcs)
    if drcs_sha != EXPECTED_DRCS_SHA256:
        raise SystemExit(f"STOP: unexpected DRCS SHA-256 {drcs_sha}; expected {EXPECTED_DRCS_SHA256}")
    if args.output.resolve() == args.input.resolve():
        raise SystemExit("STOP: refusing to overwrite input firmware")
    if STORE_END > len(source):
        raise SystemExit("STOP: DRCS store sequence exceeds the input image")

    # The current image stores each payload byte as: MOV A,#imm; MOVX @DPTR,A; INC DPTR.
    old_drcs = bytearray()
    operand_offsets: list[int] = []
    for n in range(STORE_COUNT):
        inst = STORE_START + n * STORE_STRIDE
        if source[inst] != 0x74 or source[inst + 2] != 0xF0 or source[inst + 3] != 0xA3:
            raise SystemExit(f"STOP: unexpected opcode pattern at 0x{inst:04X}: {source[inst:inst+4].hex(' ')}")
        old_drcs.append(source[inst + 1])
        operand_offsets.append(inst + 1)

    out = bytearray(source)
    for offset, value in zip(operand_offsets, drcs):
        out[offset] = value

    changed_offsets = [i for i, (a, b) in enumerate(zip(source, out)) if a != b]
    operand_offset_set = set(operand_offsets)
    if not all(i in operand_offset_set for i in changed_offsets):
        raise SystemExit("STOP: patch changed a byte outside an immediate operand")
    if len(out) != FLASH_SIZE:
        raise SystemExit("STOP: output size changed unexpectedly")
    for n in range(STORE_COUNT):
        inst = STORE_START + n * STORE_STRIDE
        if out[inst] != 0x74 or out[inst + 2] != 0xF0 or out[inst + 3] != 0xA3:
            raise SystemExit(f"STOP: instruction changed after patch at 0x{inst:04X}")
        if out[inst + 1] != drcs[n]:
            raise SystemExit(f"STOP: read-back mismatch for DRCS byte {n}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)

    report = {
        "schema": "sda555xfl-arcade-firmware-patch-report-v1",
        "version": "0.13-full-cell-tetris",
        "source": {
            "file": args.input.name,
            "size_bytes": len(source),
            "crc32": crc32(source),
            "sha256": source_sha,
        },
        "target": {
            "file": args.output.name,
            "size_bytes": len(out),
            "crc32": crc32(out),
            "sha256": sha256(out),
        },
        "drcs_payload": {
            "bytes": len(drcs),
            "crc32": crc32(drcs),
            "sha256": drcs_sha,
            "glyph_count": 7,
            "bytes_per_glyph": 60,
            "dimensions": "12x10",
        },
        "patch": {
            "rom_offset_start": f"0x{STORE_START:04X}",
            "rom_offset_end_exclusive": f"0x{STORE_END:04X}",
            "immediate_operands_replaced": STORE_COUNT,
            "actual_byte_values_changed": len(changed_offsets),
            "all_changes_are_immediate_operands": all(i in operand_offset_set for i in changed_offsets),
            "all_non_operand_bytes_identical": all(source[i] == out[i] for i in range(len(source)) if i not in operand_offset_set),
            "instruction_opcodes_preserved": True,
            "size_preserved": True,
        },
        "validation": {
            "input_sha256_matches_expected": True,
            "drcs_sha256_matches_expected": True,
            "store_stream_shape_valid": True,
            "readback_matches_payload": True,
            "flash_written": False,
            "physical_tv_tested": False,
        },
        "scope": {
            "changed": "Tetris DRCS glyph data only",
            "tetris_game_logic_changed": False,
            "pong_logic_changed": False,
            "launcher_logic_changed": False,
            "settings_logic_changed": False,
            "hardware_profile": "P3.3 inherited from input BIN; P3.2 variant not built",
        },
        "notes": [
            "This patches the user-supplied Arcade v0.12 P3.3 binary; it does not reconstruct the firmware from missing source files.",
            "The patch writes the new seven full-cell glyphs into the existing 420-byte startup upload sequence to XRAM 0xCA16..0xCBB9.",
            "Each glyph uses the original per-piece palette-index convention (highlight 1, face 2..8, shade 9..15), so no CLUT or CDW logic changed.",
            "The 420-byte payload contains no pixel index 0, removing the former black border/inset from every Tetris cell.",
            "No external Flash was written and no physical-TV test was performed.",
        ],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "result": "PASS",
        "output": str(args.output),
        "bytes": len(out),
        "crc32": report["target"]["crc32"],
        "sha256": report["target"]["sha256"],
        "immediate_operands_replaced": STORE_COUNT,
        "actual_byte_values_changed": len(changed_offsets),
        "non_operand_bytes_changed": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

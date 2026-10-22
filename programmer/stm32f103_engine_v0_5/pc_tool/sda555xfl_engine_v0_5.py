#!/usr/bin/env python3
"""
SDA555XFL SST39LF/VF010 programming/recovery engine simulator v0.5.

This tool DOES NOT send erase/program commands to hardware.
It validates the full state machine in memory:
  current -> chip erase -> target program -> target verify
          -> chip erase -> recovery program -> recovery verify

It also audits a v0.5 firmware source/build for the compile lock.
"""
from __future__ import annotations

import argparse, hashlib, json, re, sys, zlib
from pathlib import Path

FLASH_SIZE = 0x20000
ORIGINAL_SHA256 = "6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816"
ORIGINAL_CRC32 = 0xB3680360

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def crc32(b: bytes) -> int:
    return zlib.crc32(b) & 0xffffffff

def load_image(path: str) -> bytes:
    b = Path(path).read_bytes()
    if len(b) != FLASH_SIZE:
        raise ValueError(f"{path}: expected {FLASH_SIZE} bytes, got {len(b)}")
    return b

class FlashModel:
    def __init__(self, initial: bytes):
        if len(initial) != FLASH_SIZE:
            raise ValueError("bad flash size")
        self.mem = bytearray(initial)
        self.erase_count = 0
        self.program_count = 0

    def chip_erase(self):
        self.mem[:] = b"\xff" * FLASH_SIZE
        self.erase_count += 1
        assert all(x == 0xff for x in self.mem)

    def program_byte(self, addr: int, value: int):
        before = self.mem[addr]
        if (before & value) != value:
            raise RuntimeError(
                f"illegal 0->1 program at 0x{addr:05X}: {before:02X}->{value:02X}"
            )
        self.mem[addr] = before & value
        self.program_count += 1
        if self.mem[addr] != value:
            raise RuntimeError("model readback mismatch")

    def program_image_after_erase(self, image: bytes):
        if any(x != 0xff for x in self.mem):
            raise RuntimeError("program_image_after_erase requires all-FF array")
        count = 0
        for a, d in enumerate(image):
            if d != 0xff:
                self.program_byte(a, d)
                count += 1
        return count

    def bytes(self) -> bytes:
        return bytes(self.mem)

def simulate_cycle(current: bytes, target: bytes, recovery: bytes):
    if sha256(current) != ORIGINAL_SHA256:
        raise RuntimeError("current baseline is not the proven original")
    if sha256(recovery) != ORIGINAL_SHA256:
        raise RuntimeError("recovery image is not the proven original")

    model = FlashModel(current)

    # Gate 1: proven live baseline.
    live_crc_before = crc32(model.bytes())
    assert live_crc_before == ORIGINAL_CRC32

    # Original -> test target.
    model.chip_erase()
    erased_crc_1 = crc32(model.bytes())
    erased_sha_1 = sha256(model.bytes())
    target_programmed = model.program_image_after_erase(target)
    target_crc = crc32(model.bytes())
    target_sha = sha256(model.bytes())
    if target_sha != sha256(target):
        raise RuntimeError("target full-image verification failed")

    # Negative safety test: programming 0->1 without erase must fail.
    negative_test = "not_applicable"
    non_ff = next((i for i,b in enumerate(target) if b != 0xff), None)
    if non_ff is not None:
        try:
            model.program_byte(non_ff, 0xff)
        except RuntimeError:
            negative_test = "PASS: illegal 0->1 rejected"
        else:
            raise RuntimeError("model failed to reject illegal 0->1")

    # Test target -> original recovery.
    model.chip_erase()
    erased_crc_2 = crc32(model.bytes())
    recovery_programmed = model.program_image_after_erase(recovery)
    recovery_crc = crc32(model.bytes())
    recovery_sha = sha256(model.bytes())
    if recovery_sha != ORIGINAL_SHA256:
        raise RuntimeError("recovery full-image verification failed")

    return {
        "result": "PASS",
        "baseline": {
            "crc32": f"{live_crc_before:08X}",
            "sha256": sha256(current),
        },
        "target": {
            "crc32": f"{target_crc:08X}",
            "sha256": target_sha,
            "programmed_non_ff_bytes": target_programmed,
        },
        "erased_state": {
            "crc32_first": f"{erased_crc_1:08X}",
            "sha256_first": erased_sha_1,
            "crc32_second": f"{erased_crc_2:08X}",
        },
        "recovery": {
            "crc32": f"{recovery_crc:08X}",
            "sha256": recovery_sha,
            "programmed_non_ff_bytes": recovery_programmed,
        },
        "negative_0_to_1_test": negative_test,
        "erase_operations": model.erase_count,
        "total_program_operations": model.program_count,
    }

def audit_firmware(source: str, platformio: str):
    src = Path(source).read_text(encoding="utf-8")
    pio = Path(platformio).read_text(encoding="utf-8")

    checks = {
        "compile_lock_default_in_source":
            "#define ALLOW_DESTRUCTIVE_FPI 0" in src,
        "safe_platformio_flag":
            "-DALLOW_DESTRUCTIVE_FPI=0" in pio,
        "proven_id_BF_D5":
            "PROVEN_SST_MFR_ID" in src and "0xBFU" in src and
            "PROVEN_SST_DEVICE_ID" in src and "0xD5U" in src,
        "program_sequence_present":
            all(x in src for x in ("0xAAU","0x55U","0xA0U")),
        "erase_sequence_present":
            all(x in src for x in ("0x80U","0x10U")),
        "dq7_dq6_polling_present":
            "0x80U" in src and "0x40U" in src and "sst_wait_ready" in src,
        "full_ff_verify_present":
            "flash_all_ff" in src,
        "full_crc_verify_present":
            "flash_crc32_all" in src,
        "binary_stream_drain_on_failure":
            "Always drain the full image" in src,
        "magic_erase_interlock":
            "SST39_BFD5_ERASE" in src,
        "magic_program_interlock":
            "SST39_BFD5_PROGRAM" in src,
        "generic_write_not_exposed":
            'ERR USE_GATED_ENGINE' in src,
    }
    return {
        "result": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("simulate-cycle")
    p.add_argument("current")
    p.add_argument("target")
    p.add_argument("recovery")
    p.add_argument("--out")

    p = sub.add_parser("audit-firmware")
    p.add_argument("source")
    p.add_argument("platformio")
    p.add_argument("--out")

    a = ap.parse_args()

    if a.cmd == "simulate-cycle":
        result = simulate_cycle(
            load_image(a.current),
            load_image(a.target),
            load_image(a.recovery),
        )
    else:
        result = audit_firmware(a.source, a.platformio)

    print(json.dumps(result, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Saved: {a.out}")
    return 0 if result["result"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())

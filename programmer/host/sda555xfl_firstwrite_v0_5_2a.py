#!/usr/bin/env python3
"""
SDA555XFL v0.5.2a FIRST-WR / RESUME / RECOVERY host.

Restricted hardware workflows:
  first-write : proven original -> exact VCS test image
  restore     : any current contents -> exact proven original

The firmware exposes no arbitrary byte-program command. Image upload is split
into <=256-byte blocks. Every block CRC32 is checked by STM32 before any byte
from that block is programmed.
"""
from __future__ import annotations

import argparse, hashlib, json, sys, time, zlib
from pathlib import Path

try:
    import serial
except ImportError:
    print("Install pyserial: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

BAUD=115200
FLASH_SIZE=0x20000
BLOCK=0x100

ORIGINAL_SHA256="6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816"
ORIGINAL_CRC32=0xB3680360
VCS_SHA256="8527dd1f0fd8b5fbb1539d4cae1e6a9133a6d37853f47aef212054cf24b7748b"
VCS_CRC32=0xE0123039
ERASED_SHA256="b5a41c3758763bbec72769fab4a2533bf2db0b6312d93d25a695f9e4b9e02260"
ERASED_CRC32=0x154803CC

def sha256(b): return hashlib.sha256(b).hexdigest()
def crc32(b): return zlib.crc32(b)&0xffffffff

def open_port(port):
    s=serial.Serial(port,BAUD,timeout=5,write_timeout=10)
    time.sleep(0.15)
    s.reset_input_buffer()
    return s

def send(s,cmd):
    s.write((cmd+"\n").encode("ascii"))
    s.flush()

def line(s,timeout=5):
    old=s.timeout; s.timeout=timeout
    try:
        b=s.readline()
        if not b: raise TimeoutError("Timeout waiting for STM32")
        return b.decode("ascii",errors="replace").strip()
    finally:
        s.timeout=old

def nonempty_line(s,timeout=5):
    end=time.monotonic()+timeout
    while True:
        x=line(s,max(0.05,end-time.monotonic()))
        if x: return x

def exact(s,n,timeout=60):
    old=s.timeout; s.timeout=timeout
    try:
        out=bytearray()
        while len(out)<n:
            b=s.read(n-len(out))
            if not b: raise TimeoutError(f"binary timeout {len(out)}/{n}")
            out.extend(b)
        return bytes(out)
    finally:
        s.timeout=old

def command_lines(s,cmd,timeout=30,terminal=None):
    send(s,cmd)
    out=[]
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        x=nonempty_line(s,max(0.05,end-time.monotonic()))
        out.append(x)
        if x.startswith("ERR "): return out
        if terminal and terminal(x): return out
        if not terminal and x=="OK": return out
    raise TimeoutError(f"timeout for {cmd!r}; got {out!r}")

def read_full(s):
    send(s,f"READ 0 {FLASH_SIZE:X}")
    hdr=nonempty_line(s,10)
    exp=f"DATA 00000000 {FLASH_SIZE:08X}"
    if hdr != exp: raise RuntimeError(f"bad READ header {hdr!r}")
    data=exact(s,FLASH_SIZE,90)
    c=nonempty_line(s,10)
    if not c.startswith("CRC32 "):
        raise RuntimeError(f"missing CRC line {c!r}")
    dev=int(c.split()[1],16)
    host=crc32(data)
    if dev!=host:
        raise RuntimeError(f"CRC mismatch STM32={dev:08X} PC={host:08X}")
    return data

def id_check(s):
    r=command_lines(s,"ID5555",10,lambda x:x=="IDEXIT OK")
    print("\n".join(r))
    if not any(" RAW BF D5 " in (" "+x+" ") for x in r) or "IDEXIT OK" not in r:
        raise RuntimeError("BF D5 / IDEXIT check failed")

def status_check(s, require_wr):
    r=command_lines(s,"ENGINESTATUS",10)
    print("\n".join(r))
    if "ENGINE COMPILED" not in r:
        raise RuntimeError("engine is not compiled")
    wanted="WR FUSE ENABLED" if require_wr else "WR FUSE COMPILE_LOCKED"
    if wanted not in r:
        raise RuntimeError(f"expected {wanted!r}")
    if "PROFILE ORIGINAL B3680360 -> VCS E0123039" not in r:
        raise RuntimeError("strict profile banner missing")
    if "RESUME 154803CC -> VCS E0123039" not in r:
        raise RuntimeError("erased->VCS resume profile missing")
    return r

def load_exact(path, expected_sha, expected_crc, label):
    b=Path(path).read_bytes()
    if len(b)!=FLASH_SIZE:
        raise RuntimeError(f"{label} size {len(b)} != {FLASH_SIZE}")
    sh=sha256(b); cr=crc32(b)
    if sh!=expected_sha or cr!=expected_crc:
        raise RuntimeError(
            f"{label} mismatch CRC={cr:08X} SHA={sh}"
        )
    return b

def save_backup(data, path):
    p=Path(path)
    if p.exists():
        old=p.read_bytes()
        if old != data:
            raise RuntimeError(f"refusing to overwrite different backup: {p}")
        print(f"Backup already exists and matches: {p}")
        return
    p.write_bytes(data)
    print(f"Backup saved: {p}")

def expect_line(lines,prefix_or_exact):
    return any(x==prefix_or_exact or x.startswith(prefix_or_exact) for x in lines)

def erase_session(s,current_crc,target_crc):
    r=command_lines(
        s,
        f"ERASEGO {current_crc:08X} {target_crc:08X} SST39_BFD5_ERASE",
        timeout=180
    )
    print("\n".join(r))
    if any(x.startswith("ERR ") for x in r):
        raise RuntimeError("chip erase failed: "+" | ".join(r))
    if not any(x.startswith(f"ERASED FF CRC {ERASED_CRC32:08X}") for x in r):
        raise RuntimeError("missing verified erased-state response")

def verify_erased_host(s):
    print("Host full-array FF verification...")
    b=read_full(s)
    cr=crc32(b); sh=sha256(b)
    print(f"Erased CRC32 : {cr:08X}")
    print(f"Erased SHA256: {sh}")
    if cr!=ERASED_CRC32 or sh!=ERASED_SHA256 or any(x!=0xff for x in b):
        raise RuntimeError("host full-array erase verification failed")
    return b

def program_blocks(s,image,target_crc):
    running=0
    nblocks=FLASH_SIZE//BLOCK
    for bi,addr in enumerate(range(0,FLASH_SIZE,BLOCK),1):
        chunk=image[addr:addr+BLOCK]
        bc=crc32(chunk)
        cmd=f"PROGRAMBLOCK {addr:X} {len(chunk):X} {bc:08X} SST39_BFD5_BLOCK"
        send(s,cmd)
        ready=nonempty_line(s,10)
        if ready.startswith("ERR "):
            raise RuntimeError(f"block 0x{addr:05X} rejected: {ready}")
        exp=f"READY BLOCK {addr:08X} {len(chunk):08X}"
        if ready!=exp:
            raise RuntimeError(f"block ready mismatch: {ready!r} != {exp!r}")

        s.write(chunk); s.flush()

        result=nonempty_line(s,30)
        if result.startswith("ERR "):
            raise RuntimeError(f"block 0x{addr:05X} failed: {result}")
        if not result.startswith("BLOCKOK NEXT "):
            raise RuntimeError(f"unexpected block result {result!r}")

        if bi==1 or bi==nblocks or bi%32==0:
            print(f"Blocks {bi:3}/{nblocks}  next=0x{addr+len(chunk):05X}")

    r=command_lines(
        s,
        f"FINALIZE {target_crc:08X} SST39_BFD5_FINAL",
        timeout=120
    )
    print("\n".join(r))
    if any(x.startswith("ERR ") for x in r):
        raise RuntimeError("FINALIZE failed: "+" | ".join(r))
    if not any(x.startswith(f"FINALIZED TARGET {target_crc:08X} ") for x in r):
        raise RuntimeError("missing successful FINALIZE response")

def final_verify(s,expected,expected_crc,expected_sha,label):
    print(f"Reading full Flash for {label} verification...")
    b=read_full(s)
    cr=crc32(b); sh=sha256(b)
    print(f"Final CRC32 : {cr:08X}")
    print(f"Final SHA256: {sh}")
    if cr!=expected_crc or sh!=expected_sha or b!=expected:
        raise RuntimeError(f"{label} full-image verify failed")
    return b

def first_write(port,target_path,recovery_path,execute,out_path):
    if execute!="FIRST-WR-VCS-E0123039":
        raise RuntimeError(
            "real write not armed: use --execute FIRST-WR-VCS-E0123039"
        )

    target=load_exact(target_path,VCS_SHA256,VCS_CRC32,"VCS target")
    recovery=load_exact(recovery_path,ORIGINAL_SHA256,ORIGINAL_CRC32,"recovery")

    report={"mode":"FIRST-WR","result":"FAIL","steps":[]}
    with open_port(port) as s:
        status_check(s,True)
        id_check(s)

        print("Reading live Flash...")
        live=read_full(s)
        live_crc=crc32(live); live_sha=sha256(live)
        print(f"Live CRC32 : {live_crc:08X}")
        print(f"Live SHA256: {live_sha}")

        if live_crc==ORIGINAL_CRC32 and live_sha==ORIGINAL_SHA256 and live==recovery:
            print("STATE: PROVEN ORIGINAL")
            save_backup(live,"backup_live_original_B3680360.bin")
            report["steps"].append("live_original_verified_and_backed_up")

            arm=command_lines(
                s,
                f"ARM {ORIGINAL_CRC32:08X} {VCS_CRC32:08X}",
                timeout=120,
                terminal=lambda x:x.startswith("ARMED ")
            )
            print("\n".join(arm))
            if not any(x.startswith(
                f"ARMED BF D5 CURRENT {ORIGINAL_CRC32:08X} TARGET {VCS_CRC32:08X} ERASE_REQUIRED"
            ) for x in arm):
                raise RuntimeError("ARM failed")
            report["steps"].append("arm_original_to_vcs_pass")

            erase_session(s,ORIGINAL_CRC32,VCS_CRC32)
            report["steps"].append("firmware_erase_and_ff_verify_pass")

            verify_erased_host(s)
            report["steps"].append("host_full_ff_verify_pass")

        elif live_crc==ERASED_CRC32 and live_sha==ERASED_SHA256 and all(x==0xff for x in live):
            print("STATE: FULLY ERASED FF ARRAY — RESUME WITHOUT ANOTHER ERASE")
            report["steps"].append("exact_erased_state_verified")

            arm=command_lines(
                s,
                f"ARM {ERASED_CRC32:08X} {VCS_CRC32:08X}",
                timeout=120,
                terminal=lambda x:x.startswith("ARMED ")
            )
            print("\n".join(arm))
            if not any(x.startswith(
                f"ARMED BF D5 CURRENT {ERASED_CRC32:08X} TARGET {VCS_CRC32:08X} ERASED_READY"
            ) for x in arm):
                raise RuntimeError("erased->VCS resume ARM failed")
            report["steps"].append("arm_erased_to_vcs_resume_pass")

            verify_erased_host(s)
            report["steps"].append("host_full_ff_verify_pass")

        else:
            raise RuntimeError(
                "refusing first-write: live Flash is neither exact proven original "
                "nor exact all-FF erased array"
            )

        program_blocks(s,target,VCS_CRC32)
        report["steps"].append("block_program_and_finalize_pass")

        final_verify(s,target,VCS_CRC32,VCS_SHA256,"VCS target")
        report["steps"].append("host_full_target_verify_pass")

        # Deliberately leave target in FPI/reset. RUN is a separate command.
        report["result"]="PASS"
        report["final"]={"crc32":f"{VCS_CRC32:08X}","sha256":VCS_SHA256}
        report["target_released_to_run"]=False

    if out_path:
        Path(out_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(f"Saved: {out_path}")

    print("\nFIRST-WR RESULT: PASS")
    print("TARGET VERIFIED; CPU NOT RELEASED (still held in FPI/reset).")
    print("Use the separate run-target command only after reviewing this result.")
    return 0

def restore(port,recovery_path,execute,out_path):
    if execute!="RESTORE-ORIGINAL-B3680360":
        raise RuntimeError(
            "restore not armed: use --execute RESTORE-ORIGINAL-B3680360"
        )

    recovery=load_exact(recovery_path,ORIGINAL_SHA256,ORIGINAL_CRC32,"recovery")
    report={"mode":"RESTORE","result":"FAIL","steps":[]}

    with open_port(port) as s:
        status_check(s,True)
        id_check(s)

        print("Reading current Flash before restore...")
        current=read_full(s)
        cur_crc=crc32(current); cur_sha=sha256(current)
        print(f"Current CRC32 : {cur_crc:08X}")
        print(f"Current SHA256: {cur_sha}")
        Path(f"backup_before_restore_{cur_crc:08X}.bin").write_bytes(current)
        report["current"]={"crc32":f"{cur_crc:08X}","sha256":cur_sha}

        if cur_crc==ORIGINAL_CRC32 and cur_sha==ORIGINAL_SHA256 and current==recovery:
            print("Already exact original; no erase/program needed.")
            report["result"]="PASS_ALREADY_ORIGINAL"
            if out_path:
                Path(out_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
            return 0

        arm=command_lines(
            s,
            f"RECOVERYARM {cur_crc:08X} RECOVER_ORIGINAL_B3680360",
            timeout=120,
            terminal=lambda x:x.startswith("RECOVERY ARMED ")
        )
        print("\n".join(arm))
        if any(x.startswith("ERR ") for x in arm):
            raise RuntimeError("RECOVERYARM failed")

        already_erased = any(" ERASED_READY" in x for x in arm)
        if not already_erased:
            erase_session(s,cur_crc,ORIGINAL_CRC32)
            verify_erased_host(s)
        else:
            print("Array already has erased CRC; skipping another erase.")
            verify_erased_host(s)

        program_blocks(s,recovery,ORIGINAL_CRC32)
        final_verify(s,recovery,ORIGINAL_CRC32,ORIGINAL_SHA256,"original recovery")

        report["result"]="PASS"
        report["final"]={"crc32":f"{ORIGINAL_CRC32:08X}","sha256":ORIGINAL_SHA256}

    if out_path:
        Path(out_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
        print(f"Saved: {out_path}")
    print("\nRESTORE RESULT: PASS")
    return 0

def verify(port):
    with open_port(port) as s:
        id_check(s)
        b=read_full(s)
        print(f"CRC32 : {crc32(b):08X}")
        print(f"SHA256: {sha256(b)}")
        if sha256(b)==ORIGINAL_SHA256:
            print("MATCH: PROVEN ORIGINAL")
        elif sha256(b)==VCS_SHA256:
            print("MATCH: VCS FIRST-SCREEN TEST")
        elif sha256(b)==ERASED_SHA256:
            print("MATCH: FULLY ERASED FF ARRAY")
        else:
            print("MATCH: UNKNOWN/PARTIAL IMAGE")

def run_target(port,execute):
    if execute!="RUN-VERIFIED-TARGET":
        raise RuntimeError("use --execute RUN-VERIFIED-TARGET")
    with open_port(port) as s:
        b=read_full(s)
        sh=sha256(b)
        if sh not in (ORIGINAL_SHA256,VCS_SHA256):
            raise RuntimeError("refusing RUN: Flash is not a known verified image")
        send(s,"RUN")
        r=nonempty_line(s,5)
        print(r)
        if r!="OK RUN":
            raise RuntimeError(f"unexpected RUN response {r!r}")
        print("Target released from FPI/reset.")

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)

    p=sub.add_parser("verify")
    p.add_argument("port")

    p=sub.add_parser("first-write")
    p.add_argument("port")
    p.add_argument("target")
    p.add_argument("--recovery",required=True)
    p.add_argument("--execute",required=True)
    p.add_argument("--out")

    p=sub.add_parser("restore")
    p.add_argument("port")
    p.add_argument("recovery")
    p.add_argument("--execute",required=True)
    p.add_argument("--out")

    p=sub.add_parser("run-target")
    p.add_argument("port")
    p.add_argument("--execute",required=True)

    a=ap.parse_args()
    if a.cmd=="verify": verify(a.port); return 0
    if a.cmd=="first-write":
        return first_write(a.port,a.target,a.recovery,a.execute,a.out)
    if a.cmd=="restore":
        return restore(a.port,a.recovery,a.execute,a.out)
    if a.cmd=="run-target":
        run_target(a.port,a.execute); return 0
    return 2

if __name__=="__main__":
    raise SystemExit(main())

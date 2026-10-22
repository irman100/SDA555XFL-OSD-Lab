#!/usr/bin/env python3
"""
SDA555XFL non-destructive JEDEC software-ID probe.

Firmware required:
  S55FPI STM32F103 IDPROBE 0.3

Examples:
  py sda555xfl_idprobe.py ports
  py sda555xfl_idprobe.py info COM9
  py sda555xfl_idprobe.py probe COM9 5555
  py sda555xfl_idprobe.py probe COM9 0555

Safety:
  This utility has no program/erase command.
"""
from __future__ import annotations
import argparse, time, sys

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Install pyserial: py -m pip install pyserial", file=sys.stderr)
    raise SystemExit(2)

BAUD=115200

KNOWN_IDS = {
    (0xBF,0xD5): "SST39LF/VF010 family (SST manufacturer BF, 1-Mbit device D5)",
    (0x1F,0x17): "Atmel AT49F/LV/BV010 family (manufacturer 1F, device 17)",
    (0x01,0x6E): "AMD Am29LV010B family (manufacturer 01, device 6E)",
    (0x20,0x23): "ST M29W010B family (manufacturer 20, device 23)",
}

def open_port(port):
    s=serial.Serial(port,BAUD,timeout=5,write_timeout=5)
    time.sleep(0.15)
    s.reset_input_buffer()
    return s

def send(s,line):
    s.write((line+"\n").encode("ascii"))
    s.flush()

def readline(s):
    r=s.readline()
    if not r:
        raise TimeoutError("Timeout waiting for STM32")
    return r.decode("ascii",errors="replace").strip()

def ports():
    for p in serial.tools.list_ports.comports():
        print(f"{p.device:12} {p.description} [{p.hwid}]")

def info(port):
    with open_port(port) as s:
        send(s,"INFO")
        while True:
            line=readline(s)
            print(line)
            if line=="OK":
                break

def parse_id_line(line):
    # ID 5555 PRE C2 82 RAW BF D5 xx xx POST C2 82
    t=line.split()
    if len(t)!=13 or t[0]!="ID" or t[2]!="PRE" or t[5]!="RAW" or t[10]!="POST":
        raise RuntimeError(f"Unexpected response: {line!r}")
    return {
        "mode":t[1],
        "pre":(int(t[3],16),int(t[4],16)),
        "raw":tuple(int(x,16) for x in t[6:10]),
        "post":(int(t[11],16),int(t[12],16)),
    }

def probe(port,mode):
    command={"5555":"ID5555","0555":"ID0555"}[mode]
    with open_port(port) as s:
        send(s,command)
        result=parse_id_line(readline(s))
        exit_line=readline(s)

    print(f"Mode      : {result['mode']}")
    print(f"Before ID : {result['pre'][0]:02X} {result['pre'][1]:02X}")
    print("ID bytes  : " + " ".join(f"{x:02X}" for x in result["raw"]))
    print(f"After exit: {result['post'][0]:02X} {result['post'][1]:02X}")
    print(f"Exit check: {exit_line}")

    if result["pre"] != result["post"] or exit_line != "IDEXIT OK":
        print("STOP: read-array mode was not cleanly restored.", file=sys.stderr)
        return 2

    ident=(result["raw"][0],result["raw"][1])
    if ident in KNOWN_IDS:
        print("MATCH     :",KNOWN_IDS[ident])
    elif result["raw"][:2] == result["pre"]:
        print("RESULT    : no ID-mode response with this unlock-address convention")
    else:
        print("RESULT    : ID mode changed data, but manufacturer/device pair is not in the small local table")
    return 0

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    sub.add_parser("ports")
    p=sub.add_parser("info"); p.add_argument("port")
    p=sub.add_parser("probe"); p.add_argument("port"); p.add_argument("mode",choices=["5555","0555"])
    a=ap.parse_args()
    if a.cmd=="ports": ports(); return 0
    if a.cmd=="info": info(a.port); return 0
    if a.cmd=="probe": return probe(a.port,a.mode)
    return 2

if __name__=="__main__":
    raise SystemExit(main())

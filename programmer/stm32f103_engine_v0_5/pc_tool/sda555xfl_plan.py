#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys, time, zlib
from pathlib import Path
try:
    import serial, serial.tools.list_ports
except ImportError:
    print("Install pyserial: py -m pip install pyserial", file=sys.stderr); raise SystemExit(2)
BAUD=115200; FLASH_SIZE=0x20000
PROVEN_ORIGINAL_SHA256="6aa37c6d74d115eefdb52db8792b929b4104c59733485fc2c27a3402c2fce816"
def hsha(b): return hashlib.sha256(b).hexdigest()
def hcrc(b): return f"{zlib.crc32(b)&0xffffffff:08X}"
def open_port(port):
    s=serial.Serial(port,BAUD,timeout=5,write_timeout=5); time.sleep(.15); s.reset_input_buffer(); return s
def send(s,x): s.write((x+"\n").encode('ascii')); s.flush()
def line(s,timeout=None):
    old=s.timeout
    if timeout is not None: s.timeout=timeout
    try:
        r=s.readline()
        if not r: raise TimeoutError('Timeout waiting for STM32')
        return r.decode('ascii',errors='replace').strip()
    finally: s.timeout=old
def exact(s,n,timeout=60):
    old=s.timeout; s.timeout=timeout
    try:
        o=bytearray()
        while len(o)<n:
            c=s.read(n-len(o))
            if not c: raise TimeoutError(f'binary timeout {len(o)}/{n}')
            o.extend(c)
        return bytes(o)
    finally: s.timeout=old
def ports():
    for p in serial.tools.list_ports.comports(): print(f"{p.device:12} {p.description} [{p.hwid}]")
def info(port):
    with open_port(port) as s:
        send(s,'INFO')
        while True:
            x=line(s); print(x)
            if x=='OK': break
def idprobe(port):
    with open_port(port) as s:
        send(s,'ID5555'); a=line(s); b=line(s); print(a); print(b)
        if ' RAW BF D5 ' not in (' '+a+' '): return 2
        if b!='IDEXIT OK': return 3
    return 0
def print_plan(port,cmd):
    with open_port(port) as s:
        send(s,cmd)
        while True:
            x=line(s); print(x)
            if x=='OK' or x.startswith('ERR'): break
def read_current(port):
    with open_port(port) as s:
        send(s,f'READ 0 {FLASH_SIZE:X}')
        hdr=line(s,10); exp=f'DATA 00000000 {FLASH_SIZE:08X}'
        if hdr!=exp: raise RuntimeError(f'bad header {hdr!r}')
        data=exact(s,FLASH_SIZE,60)
        c=line(s,10)
        if not c.startswith('CRC32 '): raise RuntimeError(f'missing CRC {c!r}')
        if int(c.split()[1],16)!=(zlib.crc32(data)&0xffffffff): raise RuntimeError('CRC mismatch')
        send(s,'RUN'); _=line(s,5)
        return data
def transition_stats(old,new):
    u=d=e=0
    for a,b in zip(old,new):
        if a==b: u+=1
        elif (a & b)==b: d+=1
        else: e+=1
    return {'unchanged_bytes':u,'changed_1_to_0_only_bytes':d,'changed_with_0_to_1_bytes':e,'full_chip_erase_required':bool(e),'bytes_to_program_after_full_erase':sum(x!=0xff for x in new)}
def image_plan(port,image,recovery,out):
    new=Path(image).read_bytes()
    if len(new)!=FLASH_SIZE: raise ValueError('target must be exactly 128 KiB')
    rec=Path(recovery).read_bytes() if recovery else None
    if rec is not None and len(rec)!=FLASH_SIZE: raise ValueError('recovery must be exactly 128 KiB')
    print('Reading current target (128 KiB)...')
    cur=read_current(port); st=transition_stats(cur,new)
    plan={'mode':'DRYRUN_ONLY','current':{'crc32':hcrc(cur),'sha256':hsha(cur),'matches_proven_original':hsha(cur)==PROVEN_ORIGINAL_SHA256},'target':{'path':str(Path(image)),'crc32':hcrc(new),'sha256':hsha(new)},'transitions':st,'program_sequence':[['0x5555','0xAA'],['0x2AAA','0x55'],['0x5555','0xA0'],['TARGET_ADDR','TARGET_DATA']],'chip_erase_sequence':[['0x5555','0xAA'],['0x2AAA','0x55'],['0x5555','0x80'],['0x5555','0xAA'],['0x2AAA','0x55'],['0x5555','0x10']],'destructive_commands_sent':False}
    if rec is not None: plan['recovery']={'path':str(Path(recovery)),'crc32':hcrc(rec),'sha256':hsha(rec),'matches_proven_original':hsha(rec)==PROVEN_ORIGINAL_SHA256,'bytes_to_program_after_full_erase':sum(x!=0xff for x in rec)}
    print('Current SHA256 :',plan['current']['sha256']); print('Target  SHA256 :',plan['target']['sha256']); print('Baseline known :','YES' if plan['current']['matches_proven_original'] else 'NO')
    print('Unchanged      :',st['unchanged_bytes']); print('1->0 only      :',st['changed_1_to_0_only_bytes']); print('Needs 0->1     :',st['changed_with_0_to_1_bytes']); print('Chip erase     :','YES' if st['full_chip_erase_required'] else 'NO'); print('Program bytes after erase:',st['bytes_to_program_after_full_erase']); print('DESTRUCTIVE COMMANDS SENT: NO')
    if out: Path(out).write_text(json.dumps(plan,indent=2),encoding='utf-8'); print('Plan saved:',out)
    return 0
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('ports')
    p=sub.add_parser('info'); p.add_argument('port')
    p=sub.add_parser('id'); p.add_argument('port')
    p=sub.add_parser('planbyte'); p.add_argument('port'); p.add_argument('address'); p.add_argument('data')
    p=sub.add_parser('planerase'); p.add_argument('port')
    p=sub.add_parser('image-plan'); p.add_argument('port'); p.add_argument('image'); p.add_argument('--recovery'); p.add_argument('--out')
    a=ap.parse_args()
    if a.cmd=='ports': ports(); return 0
    if a.cmd=='info': info(a.port); return 0
    if a.cmd=='id': return idprobe(a.port)
    if a.cmd=='planbyte': print_plan(a.port,f'PLANBYTE {int(a.address,0):X} {int(a.data,0):X}'); return 0
    if a.cmd=='planerase': print_plan(a.port,'PLANERASE'); return 0
    if a.cmd=='image-plan': return image_plan(a.port,a.image,a.recovery,a.out)
    return 2
if __name__=='__main__': raise SystemExit(main())

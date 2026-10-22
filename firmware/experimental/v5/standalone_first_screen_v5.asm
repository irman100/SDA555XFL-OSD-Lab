; SDA555XFL first autonomous screen candidate v5
; Reference source corresponding to generated binaries.
; First bench should observe pin 19 HS/SC, pin 20 VS/P4.7, and pin 26 P3.5.
;
; Factory pointer/GDW bytes C400..C40F:
; 48 F4 10 C4 06 C4 07 00 00 00 00 58 09 66 41 08
; DRCS pointer bytes C470..C475:
; 76 C4 50 CC 16 CA
; DRCS #768 bytes C476..C484:
; FF F8 01 A0 59 09 89 18 61 89 19 09 A0 5F FF
;
; Display:
; black cell   = 00 03 00
; visible cell = 00 03 1C
;
; Exact machine bytes and branch displacements are in the .lst files.

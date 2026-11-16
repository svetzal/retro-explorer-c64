; Print a message with the KERNAL, then pass the `frame` label once in each frame.
; Replace this program with your own.
;
; Sources: Commodore 64 Programmer's Reference Guide, resources.json id c64-prg,
; PDF page numbers. 64tass manual, https://tass64.sourceforge.net/.

CHROUT  = $ffd2         ; prints the PETSCII character in A (PDF 291, PDF 297)
RASTER  = $d012         ; the raster line, low 8 bits (PDF 169)
BELOW   = 252           ; the first line below the display window, 51-251 (PDF 466)

; A BASIC line "2026 SYS 2061" at the start of BASIC memory, so that RUN
; starts the program. 64tass manual, "Usage tips" (BASIC loader).
*       = $0801
        .word (+), 2026
        .null $9e, format("%4d", start)
+       .word 0

start   ldx #0
next    lda message,x
        beq loop
        jsr CHROUT
        inx
        bne next

; The main loop. Wait for the line below the display window, then do the
; work of one frame. The check stops at `frame` after the screen is drawn.
loop    lda RASTER
        cmp #BELOW
        bne loop
wait    lda RASTER
        cmp #BELOW
        beq wait
frame   jmp loop                ; the check stops here (c64.toml checkpoint)

; 64tass converts this text to PETSCII. In its encoding, a to z give the
; codes 65 to 90 ($41-$5A), which the firmware's character set shows as
; capital letters (64tass manual, "The none encoding for Unicode"; PDF 398-399).
message .text "hello, world!", 13, 0

; Put known text and colours on the text screen, then hold the picture.
;
; The example has 3 parts. It sets the border and background colours (and,
; in the mixed-case variant, the character set), fills screen memory and
; colour memory, and writes two lines of text.
; The context is a BASIC line that starts the program, and a loop that
; holds the picture and passes the `shown` label once in each frame.
;
; Sources: Commodore 64 Programmer's Reference Guide (Commodore, 1982),
; resources.json id c64-prg, PDF page numbers.
; 64tass manual, https://tass64.sourceforge.net/ (BASIC loader, screen encoding).

MIXED_CASE :?= false    ; c64.toml variant mixed-case defines MIXED_CASE:=true

; --- CONTEXT: a BASIC line "2026 SYS 2061" at the start of BASIC memory, so
; that RUN starts the program. 64tass manual, "Usage tips" (BASIC loader).
*       = $0801
        .word (+), 2026
        .null $9e, format("%4d", start)
+       .word 0

; >>> EXAMPLE 1 of 3: the addresses and the values
SCREEN      = $0400     ; 1000 bytes, 40 columns x 25 rows (PDF 120, PDF 401)
COLOURS     = $d800     ; 1000 colour values, 4 bits each (PDF 120, PDF 402)
BORDER      = $d020     ; border colour register (PDF 342)
BACKGROUND  = $d021     ; background colour 0, shown where a dot is 0 (PDF 135-136)
CHARSET     = $d018     ; 53272: 21 selects set 1, 23 selects set 2 (PDF 395)
COLUMNS     = 40

BLACK       = 0         ; colour codes (PDF 402)
WHITE       = 1
BLUE        = 6
YELLOW      = 7
SPACE       = 32        ; screen code of a space (PDF 396)
SET_2       = 23        ; upper and lower case (PDF 395)

TITLE_ROW    = 11
TITLE_COLUMN = 10
NOTE_ROW     = 13
NOTE_COLUMN  = 14
; <<< END EXAMPLE

start
; >>> EXAMPLE 2 of 3: set the border and background colours, and the character set
        lda #BLUE
        sta BORDER
        lda #BLACK
        sta BACKGROUND
.if MIXED_CASE
        lda #SET_2              ; the main build keeps the set that the firmware selects
        sta CHARSET
.endif
; <<< END EXAMPLE

; >>> EXAMPLE 3 of 3: clear the screen, then write the text and its colours
        ldx #0
clear   lda #SPACE              ; 4 x 250 bytes = 1000 screen cells
        sta SCREEN,x
        sta SCREEN+250,x
        sta SCREEN+500,x
        sta SCREEN+750,x
        lda #WHITE
        sta COLOURS,x
        sta COLOURS+250,x
        sta COLOURS+500,x
        sta COLOURS+750,x
        inx
        cpx #250
        bne clear

        ldx #size(title)-1
-       lda title,x             ; screen codes, not PETSCII (PDF 395-397)
        sta SCREEN+TITLE_ROW*COLUMNS+TITLE_COLUMN,x
        dex
        bpl -                   ; colour memory already holds WHITE here

        ldx #size(note)-1
-       lda note,x
        sta SCREEN+NOTE_ROW*COLUMNS+NOTE_COLUMN,x
        lda #YELLOW
        sta COLOURS+NOTE_ROW*COLUMNS+NOTE_COLUMN,x
        dex
        bpl -
; <<< END EXAMPLE

; --- CONTEXT: hold the picture. Wait for raster line 252, the first line
; below the display window (51-251, PDF 466; raster register $D012, PDF 169),
; then pass `shown` once in each frame. A project replaces this loop.
frame   lda $d012
        cmp #252
        bne frame
wait    lda $d012
        cmp #252
        beq wait
shown   jmp frame               ; the check stops here (c64.toml checkpoint)

; 64tass converts the text to screen codes. In its screen encoding, a to z
; give the codes 1 to 26 and A to Z give 65 to 90. 64tass manual, "The screen
; encoding for Unicode". Set 1 shows 1 to 26 as capital letters. Set 2 shows
; 1 to 26 as small letters and 65 to 90 as capital letters (PDF 395-397).
        .enc "screen"
.if MIXED_CASE
title   .text "Hello, Commodore 64!"
note    .text "First screen"
.else
title   .text "hello, commodore 64!"
note    .text "first screen"
.endif

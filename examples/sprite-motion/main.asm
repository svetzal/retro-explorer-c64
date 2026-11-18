; Three example parts select artwork, place sprites and time their updates.
; The context draws a stationary arena and supplies repeatable actor paths.
; Source: Commodore 64 Programmer's Reference Guide, c64-prg, PDF 152-158, 161, 169.
SAMPLE_FIELD :?= 1
TIME_UPDATES :?= false
* = $0801
        .word (+),2026
        .null $9e,format("%4d",start)
+       .word 0

; --- CONTEXT: draw a character arena with a status line.
start   sei
        lda #0
        sta $d020
        lda #6
        sta $d021
        ldx #0
-       lda #32
        .for offset in [0,250,500,750]
        sta $0400+offset,x
        .endfor
        lda #14
        .for offset in [0,250,500,750]
        sta $d800+offset,x
        .endfor
        inx
        cpx #250
        bne -
        ldx #39
-       lda #$a0
        sta $0400+40,x
        sta $0400+960,x
        dex
        bpl -
        .for row in range(2,24)
        sta $0400+40*row
        sta $0400+40*row+39
        .endfor
        ldx #size(title)-1
-       lda title,x
        sta $0401,x
        dex
        bpl -

; >>> EXAMPLE 1 of 3: assign three shapes and their colours.
        ldx #2
-       lda pointers,x
        sta $07f8,x
        lda inks,x
        sta $d027,x
        dex
        bpl -
        lda #2
        sta $d025               ; shared red
        lda #7
        sta $d01c               ; multicolour mode for all three
        sta $d015               ; enable all three
; <<< END EXAMPLE
        .if TIME_UPDATES
        ; Check context only: CIA 1 timer A counts system clocks (c64-prg PDF 348-350).
        lda #0
        sta $dc0e
        lda #$ff
        sta $dc04
        sta $dc05
        lda #$11
        sta $dc0e
        .endif
        jsr position
        jsr field_end           ; synchronise before counting full fields
; >>> EXAMPLE 2 of 3: update once per two fields, below the display.
next    jsr field_end
        inc field
        lda field
        cmp #SAMPLE_FIELD       ; checkpoint selection only
        bne tick
sample  nop
tick    lda field
        lsr
        bcs next
        jsr position_next
        jmp next
field_end lda #252
-       cmp $d012
        bne -
-       cmp $d012
        beq -
        rts
; <<< END EXAMPLE

; --- CONTEXT: repeat a 32-step pass. The player moves down and right.
position_next
        .if TIME_UPDATES
        ; Record 32 update times in order, repeating after each pass.
        ldx step
-       lda $dc05
        ldy $dc04
        cmp $dc05
        bne -
        sta time_hi,x
        tya
        sta time_lo,x
        .endif
        inc step
        lda step
        and #31
        sta step
; >>> EXAMPLE 3 of 3: move independently and update the ninth X bits.
position lda step
        clc
        adc #255
        sta $d000
        lda #2                  ; robot X is always above 255
        adc #0                  ; carry from player X supplies bit zero
        sta $d010
        lda step
        clc
        adc #129
        sta $d001
        lda #50                 ; robot starts at hardware X=306
        sec
        sbc step
        sta $d002
        lda #105
        sta $d003
        lda step
        asl
        sta distance
        lda #250                ; shot travels up and left
        sec
        sbc distance
        sta $d004
        lda #127
        sec
        sbc distance
        sta $d005
        rts
; <<< END EXAMPLE
; --- CONTEXT: palette, paths and the CoCo player, grunt and diagonal shot.
field   .byte 0
step    .byte 0
distance .byte 0
pointers .byte player/64,grunt/64,shot/64
inks    .byte 7,5,7
        .enc "screen"
title   .text "arena blaster"
.if TIME_UPDATES
time_lo .fill 32,0
time_hi .fill 32,0
.endif
* = $2000
player
        .byte %00001010,%00000000,%00000000  ; ..YY..
        .byte %00001010,%00000000,%00000000  ; ..YY..
        .byte %00010101,%01000000,%00000000  ; .RRRR.
        .byte %10000101,%00100000,%00000000  ; Y.RR.Y
        .byte %10010101,%01100000,%00000000  ; YRRRRY
        .byte %00000101,%00000000,%00000000  ; ..RR..
        .byte %00000101,%00000000,%00000000  ; ..RR..
        .byte %00100000,%10000000,%00000000  ; .Y..Y.
        .byte %00100000,%10000000,%00000000  ; .Y..Y.
        .byte %10100000,%10100000,%00000000  ; YY..YY
        .fill 64-(*-player),0
grunt
        .byte %00101010,%10000000,%00000000  ; .GGGG.
        .byte %10011010,%01100000,%00000000  ; GRGGRG
        .byte %10101010,%10100000,%00000000  ; GGGGGG
        .byte %00100000,%10000000,%00000000  ; .G..G.
        .byte %10101010,%10100000,%00000000  ; GGGGGG
        .byte %10001010,%00100000,%00000000  ; G.GG.G
        .byte %10001010,%00100000,%00000000  ; G.GG.G
        .byte %00001010,%00000000,%00000000  ; ..GG..
        .byte %00100000,%10000000,%00000000  ; .G..G.
        .byte %10100000,%10100000,%00000000  ; GG..GG
        .fill 64-(*-grunt),0
shot
        .byte %10000000,%00000000,%00000000  ; Y..
        .byte %10000000,%00000000,%00000000  ; Y..
        .byte %00100000,%00000000,%00000000  ; .Y.
        .byte %00100000,%00000000,%00000000  ; .Y.
        .byte %00001000,%00000000,%00000000  ; ..Y
        .byte %00001000,%00000000,%00000000  ; ..Y
        .fill 64-(*-shot),0

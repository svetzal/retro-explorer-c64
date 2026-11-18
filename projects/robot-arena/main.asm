; Robot Arena. Commodore 64 Programmer's Reference Guide (c64-prg),
; PDF 113, 347-348: CIA keyboard ports; coordinates from VICE gtk3_sym.vkm.
; PDF 169: raster timing. PDF 342, 395, 401-402: border, screen and colours.
; $0400-$07e7 screen, $0801 onward code/tables, $2000 onward round state.
CHECK_INPUT :?= 0
CHECK_ROBOT_X :?= 30
CHECK_CHASE :?= 0
CHECK_EDGE :?= false
CHECK_REPLAY :?= false
screen = $0400
colours = $d800
blank = 32
* = $0801
        .word (+), 2026
        .null $9e, format("%4d",start)
+       .word 0
start   sei
        lda #$ff
        sta $dc02
        lda #0
        sta $dc03
        sta $d021
        lda #6
        sta $d020
        .if CHECK_REPLAY           ; test input timeline survives a round reset
        lda #0
        sta replay_tick
        .endif
        jsr reset
loop    lda $d012
        cmp #252
        bne loop
-       cmp $d012
        beq -
        jsr read_keys
        lda phase
        cmp #2
        bcc playable
        lda keys
        bne try_restart
        sta restart_lock
        beq end_update
try_restart lda restart_lock
        bne end_update
        jsr reset
        inc phase
        jsr banner
        jmp end_update
playable lda phase
        bne update
        lda keys
        beq end_update
        inc phase
        jsr banner
update  jsr erase
        jsr move_player
        jsr contact
        lda phase
        cmp #1
        bne paint
        jsr fire
        jsr chase
paint   jsr actors
end_update
        .if CHECK_REPLAY           ; take snapshots only after the replay inputs
        lda replay_tick
        cmp #4
        bcc loop
        .endif
frame   jmp loop

reset   ldx #state_end-state-1
        lda #0
-       sta state,x
        dex
        bpl -
        lda #20
        .if CHECK_EDGE             ; start at the left wall for the boundary check
        lda #1
        .endif
        sta px
        lda #CHECK_ROBOT_X          ; near starts only in check variants
        sta rx
        lda #12
        sta py
        sta ry
        lda #1
        sta restart_lock
        lda #18
        .if CHECK_CHASE            ; first chase step due immediately for checks
        lda #1
        .endif
        sta robot_wait
        ldx #0
-       lda #blank
        .for offset in [0,256,512,744]
        sta screen+offset,x
        .endfor
        lda #1
        .for offset in [0,256,512,744]
        sta colours+offset,x
        .endfor
        inx
        bne -
        ldx #39
-       lda title,x
        sta screen,x
        lda controls,x
        sta screen+40*24,x
        lda #35
        sta screen+40*2,x
        sta screen+40*22,x
        dex
        bpl -
        .for row in range(3,22)
        sta screen+40*row
        sta screen+40*row+39
        .endfor
        jsr banner
        jmp actors

banner  ldx phase
        lda message_offsets,x
        tay
        ldx #0
-       lda messages,y
        sta screen+40,x
        iny
        inx
        cpx #40
        bne -
        rts

read_keys lda #0
        sta keys
        ldx #7
-       lda columns,x
        sta $dc00
        lda $dc01
        and masks,x
        clc
        bne +
        sec
+       rol keys
        dex
        bpl -
        .if CHECK_INPUT           ; fixed decoded controls for emulator checks
        lda #CHECK_INPUT
        sta keys
        .endif
        .if CHECK_REPLAY           ; hit, hold, release, then start another round
        ldx replay_tick
        lda replay_input,x
        sta keys
        cpx #4
        beq +
        inc replay_tick
+       .endif
        rts

move_player lda move_wait
        beq move
        dec move_wait
        rts
move    lda keys
        and #15
        beq done
        jsr direction
        lda px
        clc
        adc dx,x
        cmp #1
        bcc done
        cmp #39
        bcs done
        tay
        lda py
        clc
        adc dy,x
        cmp #3
        bcc done
        cmp #22
        bcs done
        sta py
        sty px
        lda #4
        sta move_wait
done    rts
direction ldx #$ff                ; first set bit: up, left, down, right
-       inx
        lsr
        bcc -
        rts

fire    lda bullet
        bne in_flight
        lda keys
        lsr
        lsr
        lsr
        lsr
        beq done
        jsr direction
        stx heading
        lda px
        sta bx
        lda py
        sta by
        inc bullet
        bne advance
in_flight dec shot_wait
        bne done
advance ldx heading
        lda bx
        clc
        adc dx,x
        sta bx
        beq expire
        cmp #39
        beq expire
        lda by
        clc
        adc dy,x
        sta by
        cmp #2
        beq expire
        cmp #22
        beq expire
        lda #3
        sta shot_wait
shot_hit lda bx
        cmp rx
        bne done
        lda by
        cmp ry
        bne done
        lda #2
        sta phase
        jsr banner
expire  lda #0
        sta bullet
        rts

chase   lda phase
        cmp #1
        bne contact_done
        dec robot_wait
        bne contact_done
        lda #18
        sta robot_wait
        lda rx
        cmp px
        beq vertical
        bcc east
        dec rx
        jmp robot_moved
east    inc rx
        jmp robot_moved
vertical lda ry
        cmp py
        beq robot_moved
        bcc south
        dec ry
        jmp robot_moved
south   inc ry
robot_moved lda bullet
        beq contact
        jsr shot_hit
        lda phase
        cmp #1
        bne contact_done
contact lda px
        cmp rx
        bne contact_done
        lda py
        cmp ry
        bne contact_done
        lda #3
        sta phase
        jmp banner
contact_done rts

erase   lda #blank
        ldx px
        ldy py
        jsr plot
        lda #blank
        ldx rx
        ldy ry
        jsr plot
        lda bullet
        beq contact_done
        lda #blank
        ldx bx
        ldy by
        jmp plot

actors  lda phase
        cmp #2
        beq player
        lda #18                   ; R
        ldx rx
        ldy ry
        jsr plot
player  lda #43                   ; +
        ldx px
        ldy py
        jsr plot
        lda bullet
        beq contact_done
        lda #42                   ; *
        ldx bx
        ldy by
plot    pha
        lda row_lo,y
        sta cell+1
        sta ink+1
        lda row_hi,y
        sta cell+2
        clc
        adc #>(colours-screen)
        sta ink+2
        pla
cell    sta screen,x
        cmp #18
        beq red
        cmp #42
        beq yellow
        lda #1
        bne ink
red     lda #2
        bne ink
yellow  lda #7
ink     sta colours,x
        rts

row_lo  .for row in range(25)
        .byte <(screen+row*40)
        .endfor
row_hi  .for row in range(25)
        .byte >(screen+row*40)
        .endfor
columns .byte $fd,$fd,$fd,$fb,$ef,$ef,$df,$bf
masks   .byte 2,4,32,4,64,32,4,4
dx      .byte 0,255,0,1
dy      .byte 255,0,1,0
message_offsets .byte 0,40,80,120
        .enc "screen"
title   .text "robot arena"
        .fill 40-(*-title),32
controls .text "move: w a s d       fire: o k l ;"
        .fill 40-(*-controls),32
messages .text "press a control to start"
        .fill 40-(*-messages),32
        .text "destroy the robot"
        .fill 80-(*-messages),32
        .text "robot down!  release, then press to play"
        .text "caught!  release, then press to play"
        .fill 160-(*-messages),32
        .cerror * > $2000, "program overlaps round state"
* = $2000
state
px      .byte 0
py      .byte 0
rx      .byte 0
ry      .byte 0
bx      .byte 0
by      .byte 0
bullet  .byte 0
heading .byte 0
phase   .byte 0
keys    .byte 0
move_wait .byte 0
robot_wait .byte 0
shot_wait .byte 0
restart_lock .byte 0
state_end
        .if CHECK_REPLAY
replay_tick .byte 0
replay_input .byte 128,128,0,2,0
        .endif

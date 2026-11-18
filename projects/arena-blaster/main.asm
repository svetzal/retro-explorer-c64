; Arena Blaster, NTSC. VIC sprite formats and positions: c64-prg PDF 152-161.
; Raster and text arena: PDF 169, 342 and 401-402. Graphics in bank 0 at $2000.
; Sprite 0 is the player, 1-4 are grunts and 5-7 are shots.
TEST_TIMING :?= false
TEST_LEVEL :?= 1
TEST_KEYS :?= 0
TEST_PLAY :?= false
TEST_TARGET :?= 0
TEST_HIT :?= false
TEST_TOUCH :?= false
TEST_LAST :?= false
TEST_BONUS :?= false
TEST_EDGE :?= false
TEST_LIVES :?= 3
TEST_TIMER :?= 45
screen = $0400
TitlePhase = 0
ReadyPhase = 1
PlayPhase = 2
DeathPhase = 3
ClearPhase = 4
OverPhase = 5
* = $0801
        .word (+),2026
        .null $9e,format("%4d",start)
+       .word 0
start   sei
        lda #$ff
        sta $dc02
        sta $d01c
        lda #0
        sta $dc03
        sta $d020
        lda #6
        sta $d021
        lda #2
        sta $d025
        ldx #7
-       lda pointers,x
        sta $07f8,x
        sta $27f8,x
        sta $2bf8,x
        lda inks,x
        sta $d027,x
        dex
        bpl -
        ldx #0
-       lda #32
        .for offset in [0,250,500,750]
        sta screen+offset,x
        .endfor
        lda #14
        .for offset in [0,250,500,750]
        sta $d800+offset,x
        .endfor
        inx
        cpx #250
        bne -
        lda #160
        ldx #39
-       sta screen+80,x
        sta screen+920,x
        dex
        bpl -
        .for row in range(3,23)
        sta screen+row*40
        sta screen+row*40+39
        .endfor
        ldx #37
        lda #5
-       .for row in range(3,23)
        sta $d800+40*row+1,x
        .endfor
        dex
        bpl -
        .if TEST_TIMING
        ; Check only: CIA 1 timer A counts NTSC system clocks (c64-prg PDF 348-350).
        lda #0
        sta $dc0e
        lda #$ff
        sta $dc04
        sta $dc05
        lda #$11
        sta $dc0e
        .endif
        jsr setup_crowd_pages
        jsr new_game
        .if TEST_PLAY
        lda #PlayPhase
        .else
        lda #TitlePhase
        .endif
        sta phase
        jsr prepare_picture
        jsr draw
loop    jsr wait_field
        .if TEST_TIMING
        ldx tick
        cpx #9
        bcs +
-       lda $dc05
        ldy $dc04
        cmp $dc05
        bne -
        sta time_hi,x
        tya
        sta time_lo,x
+       cpx #6
        bcc read_input
frame   jmp read_input
        .else
frame
        .endif
read_input jsr read_keys
        .if TEST_KEYS       ; decoded controls for deterministic checks only
        lda #TEST_KEYS
        sta keys
        .endif
        lda keys
        and #$f0
        tax
        eor last_fire
        stx last_fire
        and last_fire
        sta pressed
        lda phase
        cmp #PlayPhase
        beq play
        cmp #TitlePhase
        beq title_input
        cmp #ClearPhase
        beq title_input
        dec timer
        bne painted
        lda phase
        cmp #ReadyPhase
        beq begin_wave
        cmp #OverPhase
        beq show_title
        dec lives
        beq game_over
        jsr spawn
        jmp painted
show_title lda #TitlePhase
        sta phase
        jmp painted
game_over lda #OverPhase
        sta phase
        lda #90
        sta timer
        jmp painted
begin_wave lda #PlayPhase
        sta phase
        jmp painted
title_input lda pressed
        beq painted
        jsr new_game
        jmp painted
play    inc tick
        jsr move
        jsr shots
        jsr grunts
painted jsr prepare_picture
        jsr wait_field
        jsr draw
        jmp loop
wait_field lda #252
-       cmp $d012
        bne -
-       cmp $d012
        beq -
        rts

new_game lda #TEST_LEVEL
        sta level
        lda #TEST_LIVES
        sta lives
        ldx #5
        lda #0
-       sta score,x
        dex
        bpl -
        .if TEST_BONUS
        lda #9
        sta score+3
        sta score+4
        .endif
spawn   lda #1
        sta enabled
        lda #15
        ldx level
        cpx #1
        beq +
        lda #255
+       sta enemy_mask
        .if TEST_LAST
        cpx #TEST_LEVEL
        bne +
        lda #(1 << TEST_TARGET)
        sta enemy_mask
+       .endif
        lda #0
        ldx level
        lda widths-1,x
        sta grunt_width
        clc
        adc #5
        sta contact_width
        lda grunt_width
        sec
        sbc #1
        sta grunt_last_x
        lda heights-1,x
        sta grunt_height
        clc
        adc #9
        sta contact_height
        lda grunt_height
        sec
        sbc #1
        sta grunt_last_y
        lda #0
        sta tick
        sta reload
        lda #80
        sta xpos
        lda #99
        sta ypos
        ldx #7
-       lda start_x,x
        sta enemy_x,x
        lda start_y,x
        sta enemy_y,x
        dex
        bpl -
        .if TEST_HIT
        lda level
        cmp #TEST_LEVEL
        bne +
        lda #87
        sta enemy_x+TEST_TARGET
        lda #99
        sta enemy_y+TEST_TARGET
+       .endif
        .if TEST_TOUCH
        lda xpos
        sta enemy_x
        lda ypos
        sta enemy_y
        .endif
        .if TEST_EDGE
        lda #4
        sta xpos
        .endif
        lda #ReadyPhase
        sta phase
        lda #60
        sta timer
        rts

move    lda keys
        and #15
        tax
        lda dx,x
        asl
        clc
        adc xpos
        cmp #4
        bcc move_y
        cmp #151
        bcs move_y
        sta xpos
move_y  lda dy,x
        asl
        asl
        clc
        adc ypos
        cmp #24
        bcc move_done
        cmp #175
        bcs move_done
        sta ypos
move_done rts

shots   lda reload
        beq aim
        dec reload
        jmp advance_all
aim     lda keys
        lsr
        lsr
        lsr
        lsr
        tay
        lda dx,y
        ora dy,y
        beq advance_all
        ldx #5
free    lda bits,x
        and enabled
        beq launch
        inx
        cpx #8
        bne free
        beq advance_all
launch  lda enabled
        ora bits,x
        sta enabled
        lda xpos
        clc
        adc #2
        sta xpos,x
        lda ypos
        clc
        adc #4
        sta ypos,x
        lda dx,y
        beq vertical_shot
        lda dy,y
        beq horizontal_shot
        cmp dx,y
        beq back_shot
        lda #shot_forward/64
        bne set_shape
back_shot lda #shot_back/64
        bne set_shape
vertical_shot lda #shot_vertical/64
        bne set_shape
horizontal_shot lda #shot/64
set_shape sta $07f8,x
        sta $27f8,x
        sta $2bf8,x
        tya
        sta headings-5,x
        lda #2
        sta reload
advance_all ldx #5
next_shot stx slot
        lda bits,x
        and enabled
        beq after_shot
        ldy headings-5,x
        lda dx,y
        asl
        asl
        clc
        adc xpos,x
        cmp #4
        bcc remove_shot
        cmp #153
        bcs remove_shot
        sta xpos,x
        lda dy,y
        asl
        asl
        asl
        clc
        adc ypos,x
        cmp #24
        bcc remove_shot
        cmp #183
        bcs remove_shot
        sta ypos,x
        ldy #0
test_grunt lda bits,y
        and enemy_mask
        beq next_target
        jsr overlap
        bcc next_target
        lda enemy_mask
        eor bits,y
        sta enemy_mask
        jsr ten_points
        ldx slot
        jmp remove_shot
next_target iny
        cpy #8
        bne test_grunt
        beq after_shot
remove_shot lda enabled
        eor bits,x
        sta enabled
after_shot inx
        cpx #8
        bne next_shot
        rts

; Coordinates use double-width horizontal pixels. Use the visible shot bounds.
overlap lda enemy_x,y
        clc
        adc grunt_width
        cmp xpos,x
        bcc miss
        beq miss
        lda enemy_y,y
        clc
        adc grunt_height
        cmp ypos,x
        bcc miss
        beq miss
        sty target
        lda $07f8,x
        sec
        sbc #shot/64
        tay
        lda xpos,x
        clc
        adc shot_width,y
        sta shot_right
        lda ypos,x
        clc
        adc shot_height,y
        ldy target
        cmp enemy_y,y
        bcc miss
        beq miss
        lda shot_right
        cmp enemy_x,y
        beq miss
        rts
miss    clc
        rts

ten_points ldx #4
carry_digit inc score,x
        lda score,x
        cmp #10
        bcc scored
        lda #0
        sta score,x
        dex
        bpl carry_digit
scored  cpx #$ff
        beq grant_life
        cpx #3
        bcs score_done
grant_life inc lives
score_done rts

grunts  lda enemy_mask
        bne chase
        lda level
        cmp #1
        bne wave_clear
        inc level
        jmp spawn
wave_clear lda #ClearPhase
        sta phase
        rts
chase   ldx #0
enemy   lda enemy_mask
        and bits,x
        beq next_enemy
        txa
        eor tick
        and #1
        beq contact
        lda enemy_x,x
        cmp xpos
        beq chase_y
        bcc right
        dec enemy_x,x
        jmp chase_y
right   inc enemy_x,x
chase_y lda enemy_y,x
        cmp ypos
        beq contact
        bcc down
        dec enemy_y,x
        lda enemy_y,x
        cmp ypos
        beq contact
        dec enemy_y,x
        jmp contact
down    inc enemy_y,x
        lda enemy_y,x
        cmp ypos
        beq contact
        inc enemy_y,x
contact lda enemy_x,x
        sec
        sbc xpos
        clc
        adc grunt_last_x
        cmp contact_width
        bcs next_enemy
        lda enemy_y,x
        sec
        sbc ypos
        clc
        adc grunt_last_y
        cmp contact_height
        bcs next_enemy
        lda #DeathPhase
        sta phase
        lda #TEST_TIMER
        sta timer
        rts
next_enemy inx
        cpx #8
        bne enemy
        rts

prepare_picture lda level
        cmp #2
        bne no_crowd
        lda phase
        beq no_crowd
        jmp prepare_crowd
no_crowd rts

draw    lda level
        cmp #2
        bne sprite_wave
        lda phase
        beq sprite_wave
        ldx page
        lda layouts,x
        sta $d018
        lda enabled
        jmp set_visible
sprite_wave lda #$14
        sta $d018
        ldx #3
-       lda enemy_x,x
        sta xpos+1,x
        lda enemy_y,x
        sta ypos+1,x
        dex
        bpl -
        lda enemy_mask
        asl
        ora enabled
set_visible sta visible
        lda #0
        sta ninth
        ldx #7
        ldy #14
position clc
        ; Add 12 logical pixels first to retain the ninth X bit.
        lda xpos,x
        adc #12
        asl
        sta $d000,y
        bcc +
        lda ninth
        ora bits,x
        sta ninth
+       lda ypos,x
        clc
        adc #50
        sta $d001,y
        dey
        dey
        dex
        bpl position
        lda ninth
        sta $d010
        lda visible
        ldx phase
        bne +
        lda #0
+       sta $d015
        lda level
        cmp #2
        bne normal_message
        cpx #ReadyPhase
        bne +
        ldx #6
+       cpx #PlayPhase
        bne normal_message
        ldx #7
normal_message lda message_lo,x
        sta copy+1
        lda message_hi,x
        sta copy+2
        ldx #39
copy    lda messages,x
        sta screen+40,x
        sta $2428,x
        sta $2828,x
        lda header,x
        sta screen,x
        sta $2400,x
        sta $2800,x
        dex
        bpl copy
        ldx #5
-       lda score,x
        ora #48
        sta screen+19,x
        sta $2413,x
        sta $2813,x
        dex
        bpl -
        lda lives
        ora #48
        sta screen+37
        sta $2425
        sta $2825
        rts

.include "keyboard.inc"
shot_width .byte 4,1,3,3
shot_height .byte 2,6,6,6
bits    .byte 1,2,4,8,16,32,64,128
pointers .byte player/64,grunt/64,grunt/64,grunt/64,grunt/64,shot/64,shot/64,shot/64
inks    .byte 7,5,5,5,5,7,7,7
widths .byte 6,4
heights .byte 10,8
start_x .byte 18,136,16,140,46,113,51,104
start_y .byte 34,48,160,153,43,164,152,34
        .enc "screen"
header  .text "arena blaster      000000      lives 3"
        .fill 40-(*-header),32
messages
m_title .text "shoot to start"
        .fill 40-(*-m_title),32
m_ready .text "level 1   shoot the grunts"
        .fill 40-(*-m_ready),32
m_play  .text "level 1"
        .fill 40-(*-m_play),32
m_death .text "caught!"
        .fill 40-(*-m_death),32
m_clear .text "wave clear!  shoot to play again"
        .fill 40-(*-m_clear),32
m_over  .text "game over"
        .fill 40-(*-m_over),32
m_ready2 .text "level 2   hold two keys for diagonals"
        .fill 40-(*-m_ready2),32
m_play2 .text "level 2"
        .fill 40-(*-m_play2),32
message_lo .byte <m_title,<m_ready,<m_play,<m_death,<m_clear,<m_over,<m_ready2,<m_play2
message_hi .byte >m_title,>m_ready,>m_play,>m_death,>m_clear,>m_over,>m_ready2,>m_play2
        .cerror * > $2000,"code overlaps sprite art"
* = $2000
.include "shapes.inc"
xpos    .fill 8,0
ypos    .fill 8,0
headings .fill 3,0
target  .byte 0
shot_right .byte 0
keys    .byte 0
last_fire .byte 0
pressed .byte 0
slot    .byte 0
enabled .byte 0
ninth   .byte 0
score   .fill 6,0
lives   .byte 0
tick    .byte 0
reload  .byte 0
phase   .byte 0
timer   .byte 0

enemy_x .fill 8,0
enemy_y .fill 8,0
enemy_mask .byte 0
level .byte 0
visible .byte 0
grunt_width .byte 0
grunt_height .byte 0
grunt_last_x .byte 0
grunt_last_y .byte 0
contact_width .byte 0
contact_height .byte 0
        .if TEST_TIMING
time_lo .fill 9,0
time_hi .fill 9,0
        .endif
        .cerror * > $2400,"state overlaps crowd screen"
* = $4000
.include "crowd.inc"

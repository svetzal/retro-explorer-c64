; Arena Blaster, NTSC. VIC sprite formats and positions: c64-prg PDF 152-161.
; Raster and text arena: PDF 169, 342 and 401-402. Graphics in bank 0 at $2000.
; Sprite 0 is the player, 1-4 are grunts and 5-7 are shots.
TEST_KEYS :?= 0
TEST_PLAY :?= false
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
        jsr new_game
        .if TEST_PLAY
        lda #PlayPhase
        .else
        lda #TitlePhase
        .endif
        sta phase
        jsr draw
loop    jsr wait_field
        jsr wait_field
frame   jsr read_keys
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
painted jsr draw
        jmp loop
wait_field lda #252
-       cmp $d012
        bne -
-       cmp $d012
        beq -
        rts

new_game lda #TEST_LIVES
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
spawn   lda #$1f
        .if TEST_LAST
        lda #3
        .endif
        sta enabled
        lda #0
        sta tick
        sta reload
        ldx #4
-       lda start_x,x
        sta xpos,x
        lda start_y,x
        sta ypos,x
        dex
        bpl -
        .if TEST_HIT
        lda #87
        sta xpos+1
        lda #99
        sta ypos+1
        .endif
        .if TEST_TOUCH
        lda xpos
        sta xpos+1
        lda ypos
        sta ypos+1
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
        ldy #1
test_grunt lda bits,y
        and enabled
        beq next_target
        jsr overlap
        bcc next_target
        lda enabled
        eor bits,y
        sta enabled
        jsr ten_points
        ldx slot
        jmp remove_shot
next_target iny
        cpy #5
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
overlap lda xpos,y
        clc
        adc #6
        cmp xpos,x
        bcc miss
        beq miss
        lda ypos,y
        clc
        adc #10
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
        cmp ypos,y
        bcc miss
        beq miss
        lda shot_right
        cmp xpos,y
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

grunts  lda enabled
        and #$1e
        bne chase
        lda #ClearPhase
        sta phase
        rts
chase   ldx #1
enemy   lda enabled
        and bits,x
        beq next_enemy
        txa
        eor tick
        and #1
        bne contact
        lda xpos,x
        cmp xpos
        beq chase_y
        bcc right
        dec xpos,x
        jmp chase_y
right   inc xpos,x
chase_y lda ypos,x
        cmp ypos
        beq contact
        bcc down
        dec ypos,x
        lda ypos,x
        cmp ypos
        beq contact
        dec ypos,x
        jmp contact
down    inc ypos,x
        lda ypos,x
        cmp ypos
        beq contact
        inc ypos,x
contact lda xpos,x
        sec
        sbc xpos
        clc
        adc #5
        cmp #11
        bcs next_enemy
        lda ypos,x
        sec
        sbc ypos
        clc
        adc #9
        cmp #19
        bcs next_enemy
        lda #DeathPhase
        sta phase
        lda #TEST_TIMER
        sta timer
        rts
next_enemy inx
        cpx #5
        bne enemy
        rts

draw    lda #0
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
        lda enabled
        ldx phase
        bne +
        lda #0
+       sta $d015
        lda message_lo,x
        sta copy+1
        lda message_hi,x
        sta copy+2
        ldx #39
copy    lda messages,x
        sta screen+40,x
        lda header,x
        sta screen,x
        dex
        bpl copy
        ldx #5
-       lda score,x
        ora #48
        sta screen+19,x
        dex
        bpl -
        lda lives
        ora #48
        sta screen+37
        rts

.include "keyboard.inc"
shot_width .byte 4,1,3,3
shot_height .byte 2,6,6,6
bits    .byte 1,2,4,8,16,32,64,128
pointers .byte player/64,grunt/64,grunt/64,grunt/64,grunt/64,shot/64,shot/64,shot/64
inks    .byte 7,5,5,5,5,7,7,7
start_x .byte 80,18,136,16,140
start_y .byte 99,34,48,160,153
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
message_lo .byte <m_title,<m_ready,<m_play,<m_death,<m_clear,<m_over
message_hi .byte >m_title,>m_ready,>m_play,>m_death,>m_clear,>m_over
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

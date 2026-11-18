; Two parts rebuild and present character cells under independent sprites.
; c64-prg PDF 121-123, 128-129: bank zero, screen and character pointers.
; PDF 152-158, 169: sprite pointers and raster. PDF 348-350: CIA timer A.
; --- CONTEXT: loader, arena, sprites and check instrumentation.
SAMPLE_UPDATE :?= 1
cell = $fb
glyph = $fd
* = $0801
        .word (+),2026
        .null $9e,format("%4d",start)
+       .word 0
        jmp start
* = $2000
pilot   .byte $18,0,0,$3c,0,0,$7e,0,0,$db,0,0,$3c,0,0,$24,0,0,$66,0,0
        .fill 64-(*-pilot),0
bolt    .byte $f0,0,0,$f0,0,0
        .fill 64-(*-bolt),0
* = $4000
start   sei
        lda #0
        sta $d020
        lda #6
        sta $d021
        ldx #0
-       lda #0
        .for base in [$0400,$0c00]
        .for col in [0,250,500,750]
        sta base+col,x
        .endfor
        .endfor
        lda #5
        .for offset in [0,250,500,750]
        sta $d800+offset,x
        .endfor
        inx
        cpx #250
        bne -
        ldx #39
        lda #1
-       sta $0428,x
        sta $07c0,x
        sta $0c28,x
        sta $0fc0,x
        dex
        bpl -
        ldx #7
-       lda #0
        sta $3000,x
        sta $3800,x
        lda #$ff
        sta $3008,x
        sta $3808,x
        dex
        bpl -
        ldx #2
-       lda shapes,x
        sta $07f8,x
        sta $0ff8,x
        lda inks,x
        sta $d027,x
        dex
        bpl -
        lda #7
        sta $d015
        lda #0
        sta $dc0e
        lda #$ff
        sta $dc04
        sta $dc05
        lda #$11
        sta $dc0e
        jsr prepare
sync    jsr edge
; >>> EXAMPLE 1 of 2: present the completed page and its sprites together.
present ldx page
        lda layout,x
        sta $d018
        lda phase
        clc
        adc #145
        sta $d000
        lda #139
        sta $d001
        lda phase
        asl
        clc
        adc #100
        sta $d002
        lda #142
        sta $d003
        lda #213
        sec
        sbc phase
        sta $d004
        lda #148
        sta $d005
        lda #0
        sta $d010
; <<< END EXAMPLE
        ldx phase
        jsr clock_read
        sta clock_hi,x
        tya
        sta clock_lo,x
        lda phase
        clc
        adc #1
        and #63
        sta phase
        jsr prepare
        lda phase
        sec
        sbc #1
        and #63
        tax
        jsr clock_read
        sta finish_hi,x
        tya
        sta finish_lo,x
        jsr edge
        inc updates
        lda updates
        cmp #SAMPLE_UPDATE
        bne sync
sample  jmp sync
edge    lda #252
-       cmp $d012
        bne -
-       cmp $d012
        beq -
        rts
clock_read lda $dc05
        ldy $dc04
        cmp $dc05
        bne clock_read
        rts

; >>> EXAMPLE 2 of 2: rebuild each touched cell, merging overlapping ink.
prepare lda page
        eor #1
        sta page
        tax
        lda dirty_base,x
        sta clean_end
        lda used,x
        tax
        beq clean_done
clean   dex
        txa
        clc
        adc clean_end
        tay
        lda dirty_lo,y
        sta wipe+1
        lda dirty_hi,y
        sta wipe+2
        lda #0
wipe    sta $ffff
        cpx #0
        bne clean
clean_done
        lda #2
        sta next_code
        lda #7
        sta actor
actor_loop ldx actor
        jsr coordinates
        lda xpos
        and #7
        asl
        asl
        asl
        sta x_shift
        lda ypos
        and #7
        ora x_shift
        tax
        lda shift_lo,x
        sta source+1
        lda shift_hi,x
        sta source+2
        lda ypos
        lsr
        lsr
        lsr
        tay
        lda xpos_hi
        lsr
        lda xpos
        ror
        lsr
        lsr
        clc
        adc row_lo,y
        sta cell
        ldx page
        lda row_hi,y
        adc screens,x
        sta cell+1
        lda #0
        sta quadrant
tile    ldx quadrant
        ldy offsets,x
        lda (cell),y
        bne reuse
        ; Save the cell address for the next use of this particular page.
        ldx page
        lda dirty_base,x
        clc
        adc next_code
        tax
        tya
        clc
        adc cell
        sta dirty_lo-2,x
        lda cell+1
        adc #0
        sta dirty_hi-2,x
        lda next_code
        sta (cell),y
        inc next_code
        tax
        jsr glyph_address
        lda source+1
        sta fresh+1
        lda source+2
        sta fresh+2
        ldy #7
fresh   lda shifted,y
        sta (glyph),y
        dey
        bpl fresh
        bmi next_tile
reuse   tax
        jsr glyph_address
merge   ldy #7
source  lda shifted,y
        ora (glyph),y
        sta (glyph),y
        dey
        bpl source
next_tile lda source+1
        clc
        adc #8
        sta source+1
        bcc +
        inc source+2
+       inc quadrant
        lda quadrant
        cmp #4
        bne tile
        dec actor
        bmi complete
        jmp actor_loop
complete lda next_code
        sec
        sbc #2
        ldx page
        sta used,x
        rts
glyph_address lda glyph_lo,x
        sta glyph
        lda glyph_hi,x
        ldx page
        clc
        adc fonts,x
        sta glyph+1
        rts
; <<< END EXAMPLE

; --- CONTEXT: four opposing pairs converge, cross, separate, then reverse.
coordinates lda phase
        cmp #33
        bcc +
        eor #63
        clc
        adc #1
+       sta travel
        txa
        and #1
        bne west
        lda start_lo,x
        clc
        adc travel
        sta xpos
        lda start_hi,x
        adc #0
        sta xpos_hi
        jmp vertical
west    lda start_lo,x
        sec
        sbc travel
        sta xpos
        lda start_hi,x
        sbc #0
        sta xpos_hi
vertical lda travel
        lsr
        clc
        adc lane,x
        sta ypos
        rts

layout  .byte $1c,$3e
screens .byte $04,$0c
fonts   .byte $30,$38
shapes  .byte pilot/64,bolt/64,bolt/64
inks    .byte 7,1,2
offsets .byte 0,1,40,41
starts = [46,78,90,122,134,166,244,276]
start_lo .for x0 in starts
        .byte <x0
        .endfor
start_hi .for x0 in starts
        .byte >x0
        .endfor
lane    .byte 84,87,86,89,88,91,90,93
row_lo  .for r in range(25)
        .byte <(r*40)
        .endfor
row_hi  .for r in range(25)
        .byte >(r*40)
        .endfor
glyph_lo .for c in range(34)
        .byte <(8*c)
        .endfor
glyph_hi .for c in range(34)
        .byte >(8*c)
        .endfor
shift_lo .for n in range(64)
        .byte <(shifted+n*32)
        .endfor
shift_hi .for n in range(64)
        .byte >(shifted+n*32)
        .endfor
; Eight source rows. Each offset has four eight-byte destination quadrants.
shape = [$7e,$db,$ff,$a5,$7e,$3c,$66,$c3]
shifted .for sx in range(8)
        .for sy in range(8)
        .for q in range(4)
        .for y in range(8)
srcrow  := (q >> 1)*8+y-sy
        .if srcrow >= 0 && srcrow < 8
        .byte ((shape[srcrow] << 8) >> sx >> (8*(1-(q & 1)))) & 255
        .else
        .byte 0
        .endif
        .endfor
        .endfor
        .endfor
        .endfor
dirty_base .byte 0,32
used    .byte 0,0
clean_end .byte 0
dirty_lo .fill 64,0
dirty_hi .fill 64,0
page    .byte 0
phase   .byte 0
actor   .byte 0
xpos    .byte 0
xpos_hi .byte 0
ypos    .byte 0
travel  .byte 0
next_code .byte 0
x_shift .byte 0
quadrant .byte 0
updates .byte 0
clock_lo .fill 64,0
clock_hi .fill 64,0
finish_lo .fill 64,0
finish_hi .fill 64,0

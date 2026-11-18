; Based on examples/crowd-rendering. Pages at $2400/$2800, glyphs at $3000/$3800.
; Commodore 64 Programmer's Reference Guide, PDF 121-123 and 129: bank 0 and ROM font access.
cell = $fb
glyph = $fd
setup_crowd_pages
        lda $01
        pha
        and #$fb
        sta $01
        ldx #0
-       .for offset in range(0,2048,256)
        lda $d000+offset,x
        sta $3000+offset,x
        sta $3800+offset,x
        .endfor
        inx
        bne -
        pla
        sta $01
        ldx #0
-       .for offset in [0,250,500,750]
        lda screen+offset,x
        sta $2400+offset,x
        sta $2800+offset,x
        .endfor
        inx
        cpx #250
        bne -
        rts
prepare_crowd lda page
        eor #1
        sta page
        tax
        lda dirty_base,x
        sta clean_end
        lda used,x
        beq clean_done
        clc
        adc clean_end
        tax
clean   dex
        lda dirty_lo,x
        sta wipe+1
        lda dirty_hi,x
        sta wipe+2
        lda #32
wipe    sta $ffff
        cpx clean_end
        bne clean
clean_done
        lda #2
        sta next_code
        lda level
        cmp #2
        beq +
        jmp complete
+       lda phase
        bne +
        jmp complete
+       lda #7
        sta actor
actor_loop ldx actor
        lda bits,x
        and enemy_mask
        bne active
        jmp advance_actor
active  lda enemy_x,x
        asl
        and #7
        asl
        asl
        asl
        sta x_shift
        lda enemy_y,x
        and #7
        ora x_shift
        tax
        lda shift_lo,x
        sta source+1
        lda shift_hi,x
        sta source+2
        ldx actor
        lda enemy_y,x
        lsr
        lsr
        lsr
        tay
        lda enemy_x,x
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
        cmp #160
        beq skip_wall
        cmp #32
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
        clc
        adc #190
        sta (cell),y
        lda next_code
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
skip_wall jmp next_tile
reuse   sec
        sbc #190
        tax
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
        beq advance_actor
        jmp tile
advance_actor dec actor
        bmi complete
        jmp actor_loop
complete lda phase
        beq +
        jsr draw_shots
+
        lda next_code
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

layouts .byte $9c,$ae
screens .byte $24,$28
fonts .byte $30,$38
offsets .byte 0,1,40,41
row_lo  .for r in range(25)
        .byte <(r*40)
        .endfor
row_hi  .for r in range(25)
        .byte >(r*40)
        .endfor
glyph_lo .for c in range(44)
        .byte <(8*(c+190))
        .endfor
glyph_hi .for c in range(44)
        .byte >(8*(c+190))
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
dirty_base .byte 0,42
used    .byte 0,0
clean_end .byte 0
dirty_lo .fill 84,0
dirty_hi .fill 84,0
page    .byte 0
actor   .byte 0
next_code .byte 0
x_shift .byte 0
quadrant .byte 0


; Even coordinates keep a two-pixel square inside a single character.
draw_shots lda #9
        sta slot
one_shot ldx slot
        lda headings,x
        bne +
        jmp skip_shot
+       lda shot_x,x
        sta px
        lda shot_y,x
dot     sta py
        lsr
        lsr
        lsr
        tay
        lda px
        lsr
        lsr
        clc
        adc row_lo,y
        sta cell
        ldx page
        lda row_hi,y
        adc screens,x
        sta cell+1
        ldy #0
        lda (cell),y
        cmp #32
        bne dot_reuse
        lda next_code
        inc next_code
        clc
        adc #190
        sta (cell),y
        ldx page
        lda dirty_base,x
        clc
        adc next_code
        tax
        lda cell
        sta dirty_lo-3,x
        lda cell+1
        sta dirty_hi-3,x
        ldx next_code
        dex
        jsr glyph_address
        lda #0
        .for n in range(8)
        ldy #n
        sta (glyph),y
        .endfor
        jmp ink
dot_reuse sec
        sbc #190
        tax
        jsr glyph_address
ink     lda px
        and #3
        tax
        lda py
        and #7
        tay
        lda masks2,x
        ora (glyph),y
        sta (glyph),y
        iny
        lda masks2,x
        ora (glyph),y
        sta (glyph),y
skip_shot dec slot
        bmi +
        jmp one_shot
+       rts
masks2 .byte $c0,$30,$0c,$03
px .byte 0
py .byte 0

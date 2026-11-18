; Three example parts configure the ports, read switches and map the keys.
; The context displays a star for each closed switch.
; Keyboard port addresses: Commodore 64 Programmer's Reference Guide, PDF 113.
; Key coordinates: VICE 3.10, C64/gtk3_sym.vkm.
; --- CONTEXT: BASIC loader and display setup (c64-prg PDF 342, 398-399).
* = $0801
        .word (+), 2026
        .null $9e, format("%4d", start)
+       .word 0

start   lda #5              ; white text
        jsr $ffd2
        lda #0
        sta $d021           ; black background
        lda #147
        jsr $ffd2           ; clear screen via CHROUT, PRG PDF 291, 398-399
; >>> EXAMPLE 1 of 3: take control of the keyboard ports.
        sei                 ; keep the firmware scan out of this experiment
        lda #$ff
        sta $dc02
        lda #0
        sta $dc03
; <<< END EXAMPLE
; --- CONTEXT: draw the labels.
        ldx #0
-       lda heading,x
        sta $0400,x
        inx
        cpx #heading_end-heading
        bne -
; >>> EXAMPLE 2 of 3: select each key and test its input bit.
loop    ldx #7
scan    lda select,x
        sta $dc00
        lda $dc01
        and sense,x
        beq held
; <<< END EXAMPLE
; --- CONTEXT: show the switch state and repeat the scan.
        lda #32
        bne show
held    lda #42
show    ldy position,x
        sta $0400+80,y
        dex
        bpl scan
frame   jmp loop

; >>> EXAMPLE 3 of 3: column selects and row masks in WASD OKL; order.
select  .byte $fd,$fd,$fd,$fb,$ef,$ef,$df,$bf
sense   .byte 2,4,32,4,64,32,4,4
; <<< END EXAMPLE
; --- CONTEXT: screen positions and labels.
position .byte 0,2,4,6,12,14,16,18
        .enc "screen"
heading .text "move        fire"
        .fill 40-(*-heading),32
        .text "w a s d     o k l ;"
heading_end

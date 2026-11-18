; CIA scan: c64-prg PDF 113, 347-348. VICE gtk3_sym.vkm supplies the key coordinates.
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
        rts
columns .byte $fd,$fd,$fd,$fb,$ef,$ef,$df,$bf
masks   .byte 2,4,32,4,64,32,4,4
; Index both axes with the full direction mask: up, left, down, right.
; Opposite keys cancel on their axis. 64tass emits signed unit steps.
dx      .for mask in range(16)
        .char ((mask >> 3) & 1) - ((mask >> 1) & 1)
        .endfor
dy      .for mask in range(16)
        .char ((mask >> 2) & 1) - (mask & 1)
        .endfor

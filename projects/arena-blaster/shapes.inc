; Arena Blaster artwork, adapted from the CoCo sprite definitions.
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
shot    .byte %10101010,0,0,%10101010,0,0
        .fill 64-(*-shot),0
shot_vertical
        .for row in range(6)
        .byte %10000000,0,0
        .endfor
        .fill 64-(*-shot_vertical),0
shot_back
        .for mask in [$80,$80,$20,$20,$08,$08]
        .byte mask,0,0
        .endfor
        .fill 64-(*-shot_back),0
shot_forward
        .for mask in [$08,$08,$20,$20,$80,$80]
        .byte mask,0,0
        .endfor
        .fill 64-(*-shot_forward),0

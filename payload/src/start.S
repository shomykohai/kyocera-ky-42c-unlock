.syntax unified

.code 32

.global start
.section .text.start
start:
    add r3, pc, #1
    bx r3

.thumb
    push {r4-r12, lr}
    bl main
    pop {r4-r12, lr}
    cbz r0, 1f
    bx r0
1:
    wfi
    b 1b

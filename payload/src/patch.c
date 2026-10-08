#include <types.h>
#include <libc.h>
#include <kyocera.h>
#include <mmio.h>

extern u8 __bss_start[], __bss_end[];

static u32 search_pattern(u32 start, u32 end, const u16* pattern, u32 plen, const u16* mask)
{
    for (u32 addr = start; addr < end; addr += 2) {
        u16 *curr = (u16 *)addr;
        u32 i = 0;

        while (i < plen) {
            u16 val = curr[i];
            u16 pat = pattern[i];

            if (mask) {
                if ((val & mask[i]) != (pat & mask[i]))
                    break;
            } else {
                if (val != pat)
                    break;
            }
            i++;
        }
        if (i == plen)
            return addr;
    }
    return 0;
}

__attribute__ ((section(".text.main"), used)) int main(void) {
    memset(__bss_start, 0, __bss_end - __bss_start);

    const u16 return_pattern[] = { 0xF500, 0x7000, 0x0000, 0xFE00 };
    const u16 return_mask[] = { 0xFFFF, 0xFFFF, 0x0000, 0xFF00 };

    u32 len = sizeof(return_pattern)/sizeof(return_pattern[0]);

    u32 ret = search_pattern(PL_BASE_ADDR, PL_END_ADDR, return_pattern, len, return_mask);

    // ?? b5 ?? ?? ?? 4? ?? 68 ?? 68
    const u16 sec_usbdl_pattern[] = { 0xB500, 0x0000, 0x4000 , 0x6800, 0x6800 };
    const u16 sec_usbdl_mask[] = { 0xFFFF, 0x0000, 0xF000, 0xFF00, 0xFF00 };

    len = sizeof(sec_usbdl_pattern)/sizeof(sec_usbdl_pattern[0]);

    u32 sec_usbdl = search_pattern(PL_BASE_ADDR, PL_END_ADDR, sec_usbdl_pattern, len, sec_usbdl_mask);

    if (ret && sec_usbdl) {
        volatile u16 *x = (volatile u16 *)sec_usbdl;
        x[0] = 0x2000; // mov r0, #0
        x[1] = 0x4770; // bx lr

        invalidate_icache_range(sec_usbdl, 4);

        __asm__ volatile (
            "mov lr, %0\n"
            "bx lr\n"
            : : "r"(ret) : "lr"
        );
    }



    for(;;)
        __asm__ volatile ("wfi" : : : "memory");
}

/*
 * SPDX-License-Identifier: AGPL-3.0-or-later
 * SPDX-FileCopyrightText: 2026 Shomy
 */

#include <stdbool.h>
#include <types.h>
#include <libc.h>
#include <debug.h>
#include <security/sej.h>
#include <drivers/uart.h>
#include <storage/mmc/mmc.h>
#include <crypto/sha256.h>
#include <kyocera.h>
#include <seccfg.h>
#include <gpt.h>

extern u8 __bss_start[], __bss_end[];

static int mmc_read_block_cb(u32 blk, void *buf, void *ctx) {
    return mmc_read_block((struct mmc_dev *)ctx, blk, buf);
}

static void platform_wdt_reset(void) {
    volatile u32 *wdt = (volatile u32 *)WDT_BASE_ADDR;
    wdt[6] = 0x1971;
    wdt[0] = 0x22000014;
    wdt[5] = 0x1209;
}

static struct mmc_dev g_mmc_dev;

__attribute__ ((section(".text.main"), used)) int main(void) {
    static struct gpt_context gpt;
    sej_param_t params = {0};
    SecCfgV4 seccfg = {0};
    u32 seccfg_start = 0;
    u8 hash[HASH_SZ];
    u8 chkcode_buf[MMC_BLOCK_SZ] __attribute__((aligned(64)));

    memset(__bss_start, 0, __bss_end - __bss_start);

    printf_register_cb(uart_putc);

    printf("\nHello from payload :)\n\n");
    printf("Copyright (C) 2026 Shomy\n");
    printf("SPDX-License-Identifier: AGPL-3.0-or-later\n\n");

    printf("Build date: %s %s (%s)\n", __DATE__, __TIME__, PAYLOAD_VERSION);

    sej_init(SEJ_BASE_ADDR);
    mmc_dev_setup(&g_mmc_dev, MSDC0_BASE_ADDR, 1, NULL);

    if (gpt_parse(&gpt, mmc_read_block_cb, &g_mmc_dev) != 0) {
        goto quit;
    }

    seccfg_start  = gpt_get_start(&gpt, "seccfg");

    if (seccfg_start == 0) {
        printf("seccfg partition not found\n");
        goto quit;
    }

    seccfg.magic = SECCFG_START_MAGIC;
    seccfg.version = 4;
    seccfg.size = SECCFG_SIZE;
    seccfg.lock_state = LKS_UNLOCK;
    seccfg.dm_verity = DM_VERITY_OK;
    seccfg.sboot_runtime = 0;
    seccfg.end_magic = SECCFG_END_MAGIC;

    sha256_hash(hash, (const u8 *)&seccfg, 0x1C);

    params.key_id = AES_SW_KEY;
    params.key_sz = AES_KEY_256;
    params.mode = AES_CBC_MODE;
    params.legacy = false;
    params.length = HASH_SZ;
    params.anti_clone = true;
    params.encrypt = true;

    sp_sej_enc(hash, hash, params);

    memcpy(seccfg.hash, hash, HASH_SZ);

    if (mmc_write_block(&g_mmc_dev, seccfg_start, &seccfg) != 0) {
        printf("Failed to write seccfg partition\n");
        goto quit;
    }

    printf("Unlocked!!\n");

    u32 chkcode_block = gpt_get_start(&gpt, "chkcode") + 4;

    if (mmc_read_block(&g_mmc_dev, chkcode_block, chkcode_buf)) {
        printf("Failed to read chkcode partition\n");
        goto quit;
    }


    *(u32 *)&chkcode_buf[0] = CHKCODE_MAGIC1;
    *(u32 *)&chkcode_buf[4] = CHKCODE_MAGIC2;

    if (mmc_write_block(&g_mmc_dev, chkcode_block, chkcode_buf)) {
        printf("Failed to write chkcode partition\n");
        goto quit;
    }

    printf("Patched chkcode partition\n");

    printf("All done!!\n");

quit:

    printf("Bye bye\n");

    platform_wdt_reset();

    for(;;);
}

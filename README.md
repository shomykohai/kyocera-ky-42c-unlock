# Bootloader unlock for Kyocera DIGNO Keitai 4 (KY-42C)

This is a bootloader unlock "exploit" for the Kyocera KY-42C, working on newer firmware versions (tested on 112.0.0153).
Furthermore, it unlocks fastboot (bootloader) cmds that were previously locked out by a "Forbidden" message.

On newer firmware versions, the Preloader has been patched against the crash to BROM method, and bootrom usbdl has been
disabled via the BROM SECCFG GFH. This means that BROM USBDL is not available, and no DA is available for this device.

> [!WARNING] 
> This is for educational purposes only. I am not responsible for any damage caused by using this code.
> Use at your own risk.

*If you only care about unlocking the bootloader, jump to the [Usage](#usage) section.*

## How does it work?

On older preloaders, MediaTek devices had a compile flag called `CFG_PRELOADER_AS_DA`, which enabled two cmds in the Preloader: `CMD_SEND_IMAGE` (0x70) and `CMD_BOOT_IMAGE` (0x71).

These cmds don't perform any sort of verification whatsoever, allowing anyone to run arbitrary code on the device.

```c
static void usbdl_send_image(void) {
	u32 img_addr = 0;
	u32 img_len = 0;
	image_index_t id;
	u16 status = 0;
	u8 img_name[64] = {0};
	u32 checksum32 = 0;
	u32 my_checksum32 = 0;

	usbdl_get_data(img_name, 64);
	usbdl_get_dword(&img_len);

  /* 
   *  For loop checking for a valid image name, we just pass "lk"
   * and the check will pass
   * ...
   */

	usbdl_put_word(status);

	// receive Image data
	usbdl_get_data((u8 *)img_addr, img_len);

	my_checksum32 = checksum_plain((u8 *)img_addr, img_len);
	usbdl_get_dword(&checksum32);

	if (my_checksum32 != checksum32) {
		pal_log_err("%s checksum mismatch!\n", MOD);
		return;
	}

  if(id == IMAGE_ATF_ID) {
      // Relocate ATF and TEE
  }
}
```

```c
static void usbdl_boot_image(void) {
	extern void bldr_jump(u32 addr, u32 arg1, u32 arg2);

	u8 img_name[64] = {0};
	u32 jump_arg;
	u16 status = 0;

	usbdl_get_data(img_name, 64);

	trustzone_pre_init();

	g_boot_mode = FASTBOOT;
	platform_set_boot_args();

	trustzone_post_init();

	jump_arg = (u32)&bootarg;

	if (!strcmp(img_name, lk)) {
		usbdl_put_word(status);
		pal_log_err("%s Jump to LK\n", MOD);
		bldr_jump(g_image_list[IMAGE_LK_ID].start_addr + PART_HDR_BUF_SIZE, jump_arg, sizeof(boot_arg_t));
	} else if (!strcmp(img_name, atf)) {
		usbdl_put_word(status);
		pal_log_err("%s Jump to ATF\n", MOD);
		bldr_jump64(g_image_list[IMAGE_LK_ID].start_addr + PART_HDR_BUF_SIZE, jump_arg, sizeof(boot_arg_t));
	} else {
		status = 1;
		usbdl_put_word(status);
		pal_log_err("%s Unknown Jump\n", MOD);
	}
}
```

This means, by crafting a payload with the correct layout (in this case, just prepending a 512 bytes empty header), we can get `EL3` code execution on the device.

This method has been already used in the past to unlock other devices, such as the [LG K10](https://github.com/arturkow2000/lgk10exploit) in Preloader mode.

# Usage

Prior to using the tool, you might need to perform some setup steps, depending on your OS.

## Windows 

Install MediaTek USB VCOM drivers (or default Serial Driver), and make sure to run the tool as Administrator.

## Linux

Add your user to the `dialout` group, and make sure to have `udev` rules for the device.

```bash
$ sudo usermod -aG dialout $USER
```

or just run the tool as root.

---

Then, run the tool:

```bash
# Unlock the bootloader
$ ./ky42c-unlock unlock

# Disable preloader security check for using a generic DA
$ ./ky42c-unlock patch 

# Dump partitions, save them to `dump/` directory
$ ./ky42c-unlock r boot,recovery,lk

# Write a partition back
$ ./ky42c-unlock w boot magisk.img
```


# Building

For building the payload, you'll need to install `arm-none-eabi-` toolchain and `make`.
If needed, export the `CROSS_COMPILE` variable to point to the toolchain.

```bash
$ export CROSS_COMPILE=arm-none-eabi-
$ ./build.sh
```

For building the tool, you'll need rust nightly toolchain, and `cargo` installed.

```bash
$ rustup install nightly
$ rustup default nightly
$ cargo build --release
```

Otherwise, you can use the old `python` script

# License

This project is licensed under `AGPL-3.0-or-later`. See [LICENSE](LICENSE) for details.

This project also includes third party code:
* [gpt](payload/src/gpt.c) by [@R0rt1z2], licensed under the `GPL-3.0-or-later` license.
* [penumbra](https://github.com/shomykohai/penumbra) by [@shomykohai]. The code used is licensed under the `AGPL-3.0-or-later` license.
* [mtk-payloads](https://github.com/shomykohai/mtk-payloads) by [@shomykohai]. The code used is licensed under the `MIT` license.

OUTPUT_FORMAT("elf32-littlearm", "elf32-bigarm", "elf32-littlearm")
OUTPUT_ARCH(arm)

ENTRY(start)

PHDRS
{
  text PT_LOAD FLAGS(5);
  data PT_LOAD FLAGS(6);
  bss PT_LOAD FLAGS(6);
}

SECTIONS
{


  . = 0x48000000;
  .text     : { KEEP(*(.text.start)) KEEP(*(.text.main)) *(.text .text.* .gnu.linkonce.t.*) } :text
  .rodata   : { *(.rodata .rodata.* .gnu.linkonce.r.*) } :text
  .data     : { *(.data .data.* .gnu.linkonce.d.*) } :data
  .bss      : { __bss_start = .; *(.bss .bss.* .gnu.linkonce.b.*) *(COMMON) __bss_end = .; } :bss
  . = ALIGN(4);

  /* Provide weak definitions for exception handling symbols referenced by libgcc */
  PROVIDE(__exidx_start = 0);
  PROVIDE(__exidx_end = 0);

  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes*) *(.interp) *(.dynsym) *(.dynstr) *(.hash) *(.dynamic) *(.comment) }
}

# Common code pulled in from mtk-payloads.
#
# Only the unlock payload needs any of it: patch.bin is a handful of Thumb
# instructions that links nothing.

ifeq ($(TARGET),unlock)
CONFIG_UART       := y

CONFIG_CRYPTO     := y
CONFIG_CRYPTO_SEJ := y

CONFIG_MMC        := y
endif

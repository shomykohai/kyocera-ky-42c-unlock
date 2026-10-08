MTK_DIR    := payload/mtk-payloads
BUILD_DIR  := $(CURDIR)/payload/build
RAW_DIR    := $(BUILD_DIR)/raw
OUTPUT_DIR ?= $(CURDIR)/bin

ARCH    := arm
TARGETS := unlock patch

PAYLOAD := ..

CROSS_COMPILE_arm ?= $(CROSS_COMPILE)

VERSION := $(shell git describe --always --dirty 2>/dev/null || echo unknown)

Q := $(if $(V),,@)

build := -C $(MTK_DIR) --no-print-directory -f scripts/Makefile.build \
	PAYLOAD=$(PAYLOAD) ARCH=$(ARCH) PAYLOAD_VERSION=$(VERSION) \
	CROSS_COMPILE_arm=$(CROSS_COMPILE_arm) \
	OUTPUT_DIR=$(RAW_DIR)

.PHONY: all clean $(TARGETS)

all: $(TARGETS)

$(TARGETS):
	@echo "=> $@"
	+$(Q)$(MAKE) $(build) TARGET=$@ OBJDIR=$(BUILD_DIR)/$@/$(ARCH)
	@mkdir -p $(OUTPUT_DIR)
	$(Q){ dd if=/dev/zero bs=512 count=1 status=none; cat $(RAW_DIR)/$@.bin; } > $(RAW_DIR)/$@.padded
	$(Q)cmp -s $(RAW_DIR)/$@.padded $(OUTPUT_DIR)/$@.bin || \
	    { mv -f $(RAW_DIR)/$@.padded $(OUTPUT_DIR)/$@.bin; echo "  IMAGE   $(OUTPUT_DIR)/$@.bin"; }
	$(Q)rm -f $(RAW_DIR)/$@.padded

clean:
	rm -rf $(BUILD_DIR)
	rm -f $(addprefix $(OUTPUT_DIR)/,$(addsuffix .bin,$(TARGETS)))

ifeq ($(TARGET),)
$(error TARGET is not set. Use the Makefile at the root of the repository)
endif

name     := $(TARGET)
arches   := arm
ldscript := $(PAYLOAD)/src/generic.ld

ifeq ($(TARGET),patch)
srcs-y := \
	$(PAYLOAD)/src/patch.c \
	$(srcs-y) \
	$(PAYLOAD)/src/start.S
else
cflags-y  += -fno-stack-protector -fPIE
ldflags-y += -Wl,-u,__aeabi_uidiv

srcs-y := \
	$(PAYLOAD)/src/main.c \
	$(PAYLOAD)/src/gpt.c \
	$(srcs-y) \
	$(PAYLOAD)/src/start.S
endif

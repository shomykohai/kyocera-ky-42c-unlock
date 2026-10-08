#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 R0rt1z2 <https://github.com/R0rt1z2>
import logging
from typing import Tuple, Union

import serial

from lib.commands import Command
from lib.utils import find_port, from_bytes, to_bytes


class Device:
    def __init__(self, port: str = '', baud: int = 115200, timeout: int = 5):
        self.dev: Union[serial.Serial, None] = None
        self.port = port
        self.baud = baud
        self.timeout = timeout

        if port:
            self.dev = serial.Serial(port, baud, timeout=timeout)

    @staticmethod
    def check(test: bytes, expected: bytes) -> bool:
        """
        Check if a test is successful.

        :param test: The test data.
        :param expected: The expected data.
        :return: True if the test is successful, otherwise False.
        """
        if test != expected:
            raise RuntimeError(f'Expected {expected}, got {test}')
        return True

    def find_device(
        self, vendor_id: int = 0x0E8D, product_id: int = 0x2000
    ) -> None:
        """
        Find the device by vendor ID and product ID.

        :param vendor_id: The vendor ID of the device.
        :param product_id: The product ID of the device.
        """
        if self.dev:
            logging.info('Device already found!')
            return

        self.port = find_port(vendor_id, product_id)

        if not self.port:
            raise RuntimeError('Device not found')

        logging.info(
            'Found device %04X:%04X at %s', vendor_id, product_id, self.port
        )

        self.dev = serial.Serial(self.port, self.baud, timeout=self.timeout)

    def echo(self, words, size=1) -> bool:
        """
        Send data to the device and check if the echo
        matches the sent data.

        :param words: The data to send.
        :param size: The number of bytes to read.
        :return: The data read.
        """
        self.dev.write(words)
        return self.check(self.dev.read(size), words)

    def wr(self, data: bytes, size: int = 1) -> bytes:
        """
        Write data to the device and read a response.

        :param data: The data to write.
        :param size: The number of bytes to read.
        """
        self.dev.write(data)
        return self.dev.read(size)

    def handshake(self) -> None:
        """
        Handshake with the device.
        """
        while True:
            self.dev.write(b'\xa0')
            response = self.dev.read(1)
            if response == b'\x5f':
                break
            self.dev.reset_input_buffer()

        self.check(self.wr(b'\x0a'), b'\xf5')
        self.check(self.wr(b'\x50'), b'\xaf')
        self.check(self.wr(b'\x05'), b'\xfa')

        logging.info('MediaTek Preloader handshake completed!')

    def get_hw_sw_ver(self) -> Tuple[int, int, int]:
        """
        Get the hardware and software version of the device.

        :return: The hardware and software version.
        """
        self.echo(to_bytes(Command.GET_HW_SW_VER.value, 1))

        hw_sub_code = self.dev.read(2)
        hw_ver = self.dev.read(2)
        sw_ver = self.dev.read(2)
        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

        return (
            from_bytes(hw_sub_code, 2),
            from_bytes(hw_ver, 2),
            from_bytes(sw_ver, 2),
        )

    def get_hw_code(self) -> int:
        """
        Get the hardware code of the device.

        :return: The hardware code.
        """
        self.echo(to_bytes(Command.GET_HW_CODE.value, 1))

        hw_code = self.dev.read(2)
        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

        return from_bytes(hw_code, 2)

    def get_me_id(self):
        """
        Get the ME ID of the device.

        :return: The ME ID.
        """
        self.echo(to_bytes(Command.GET_ME_ID.value, 1))

        length = from_bytes(self.dev.read(4), 4)
        if length == 0:
            raise RuntimeError('ME ID length is 0')
        me_id = self.dev.read(length)

        status = self.dev.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

        return me_id

    def get_soc_id(self):
        """
        Get the SOC ID of the device.

        :return: The SOC ID.
        """
        self.echo(to_bytes(Command.GET_SOC_ID.value, 1))

        length = from_bytes(self.dev.read(4), 4)
        if length == 0:
            raise RuntimeError('SOC ID length is 0')
        soc_id = self.dev.read(length)

        status = self.dev.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

        return soc_id

    def power_init(self, reg, val) -> None:
        """
        Initialize the power register.

        :param reg: The power register.
        :param val: The value to write.
        """
        logging.info(f'Init PMIC: 0x{reg:04X} (0x{val:04X})')
        self.echo(to_bytes(Command.PWR_INIT.value, 1))

        self.echo(to_bytes(reg, 4))
        self.echo(to_bytes(val, 4))

        status = self.dev.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

    def power_deinit(self) -> None:
        """
        Deinitialize PMIC.
        """
        logging.info('Deinit PMIC')
        self.echo(to_bytes(Command.PWR_DEINIT.value, 1))

        status = self.dev.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

    def get_preloader_version(self) -> int:
        self.dev.write(to_bytes(Command.GET_PL_VER.value, 1))

        pl_ver = self.dev.read(2)
        if pl_ver == 0xFE:
            logging.warning('Cannot get the Preloader version')

        return from_bytes(pl_ver, 1)

    def send_da(self, address, da_len, sig_len, da) -> int:
        """
        Uploads the Download Agent to the device.

        :param address: The address to upload the Download Agent to.
        :param da_len: The length of the Download Agent.
        :param sig_len: The length of the signature.
        :param da: The Download Agent to upload.

        :return: The checksum of the Download Agent.
        """
        logging.info(
            'Send DA to 0x%08X '
            '(%d bytes, %d bytes signature)' % (address, da_len, sig_len)
        )
        self.echo(to_bytes(Command.SEND_DA.value, 1))

        self.echo(to_bytes(address, 4), 4)
        self.echo(to_bytes(da_len, 4), 4)
        self.echo(to_bytes(sig_len, 4), 4)

        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError('status is 0x%04X' % from_bytes(status, 2))

        self.dev.write(da)

        checksum = from_bytes(self.dev.read(2), 2)
        status = from_bytes(self.dev.read(2), 2)

        if status != 0:
            raise RuntimeError('status is 0x%04X' % status)

        return checksum

    def read32(self, address: int, size: int) -> bytes:
        size_aligned = ((size + 3) // 4) * 4
        words = size_aligned // 4

        self.echo(bytes([Command.READ32.value]), 1)
        self.echo(address.to_bytes(4, 'big'), 4)
        self.echo(words.to_bytes(4, 'big'), 4)

        status = int.from_bytes(self.dev.read(2), 'big')
        if status != 0:
            if status == 0x1000:
                raise RuntimeError(
                    f'READ32 rejected at 0x{address:08X}: '
                    'status 0x1000 (READ_REGION_CHK_FAIL)'
                )
            raise RuntimeError(
                f'READ32 rejected at 0x{address:08X}: '
                f'status 0x{status:04X}'
            )

        out = bytearray()

        for _ in range(words):
            chunk = self.dev.read(4)
            val = int.from_bytes(chunk, 'big')
            out.extend(val.to_bytes(4, 'little'))

        status = int.from_bytes(self.dev.read(2), 'big')
        if status != 0:
            if status == 0x1000:
                raise RuntimeError(
                    f'READ32 completion failed at 0x{address:08X}: '
                    'status 0x1000 (READ_REGION_CHK_FAIL)'
                )
            raise RuntimeError(
                f'READ32 completion failed at 0x{address:08X}: '
                f'status 0x{status:04X}'
            )

        return bytes(out[:size])

    def write32(self, address: int, data: bytes | int) -> None:
        if isinstance(data, int):
            data = data.to_bytes(4)
        size = len(data)
        size_aligned = ((size + 3) // 4) * 4
        words = size_aligned // 4

        self.echo(bytes([Command.WRITE32.value]), 1)
        self.echo(address.to_bytes(4, 'big'), 4)
        self.echo(words.to_bytes(4, 'big'), 4)

        print(f'Writing {size} bytes to 0x{address:08X}')
        status = int.from_bytes(self.dev.read(2), 'big')
        if status != 0:
            if status == 0x1001:
                raise RuntimeError(
                    f'WRITE32 rejected at 0x{address:08X}: '
                    'status 0x1001 (WRITE_REGION_CHK_FAIL)'
                )
            raise RuntimeError(
                f'WRITE32 rejected at 0x{address:08X}: '
                f'status 0x{status:04X}'
            )

        for i in range(words):
            chunk = data[i * 4 : (i + 1) * 4]
            if len(chunk) < 4:
                chunk += b'\x00' * (4 - len(chunk))
            val = int.from_bytes(chunk, 'little')
            self.echo(val.to_bytes(4, 'big'), 4)

        print(f'Written {size} bytes to 0x{address:08X}')
        status = int.from_bytes(self.dev.read(2), 'big')
        print(f'Write status: 0x{status:04X}')
        if status != 0:
            if status == 0x1001:
                raise RuntimeError(
                    f'WRITE32 completion failed at 0x{address:08X}: '
                    'status 0x1001 (WRITE_REGION_CHK_FAIL)'
                )
            raise RuntimeError(
                f'WRITE32 completion failed at 0x{address:08X}: '
                f'status 0x{status:04X}'
            )

    def jump_da(self, address: int):
        """
        Jump to the Download Agent.

        :param address: The address of the Download Agent.
        """
        logging.info('Jump to DA at 0x%08X', address)
        self.echo(to_bytes(Command.JUMP_DA.value, 1))

        self.echo(to_bytes(address, 4))

        status = self.dev.read(2)

    def send_image(self, name: str, data: bytes) -> None:
        self.echo(to_bytes(Command.SEND_IMAGE.value, 1))

        name_bytes = name.encode('utf-8')[:64]
        name_bytes = name_bytes.ljust(64, b'\x00')
        logging.info('Sending partition name: %s', name)
        self.dev.write(name_bytes)

        img_len = len(data)
        logging.info('Sending image length: 0x%X (%d bytes)', img_len, img_len)
        self.dev.write(to_bytes(img_len, 4))

        status_bytes = self.dev.read(2)
        status = from_bytes(status_bytes, 2)
        if status != 0:
            raise RuntimeError(
                f'Device partition validation failed with status: 0x{status:04X}'
            )

        logging.info('Sending image data')
        self.dev.write(data)

        my_checksum32 = sum(data) & 0xFFFFFFFF
        logging.info('Sending checksum: 0x%08X', my_checksum32)

        self.dev.write(to_bytes(my_checksum32, 4))

        logging.info('Image transfer completed :)')

    def boot_image(self, name: str) -> None:
        self.echo(to_bytes(Command.BOOT_IMAGE.value, 1))

        name_bytes = name.encode('utf-8')[:64]
        name_bytes = name_bytes.ljust(64, b'\x00')
        logging.info('Sending partition name: %s', name)
        self.dev.write(name_bytes)
        status_bytes = self.dev.read(2)
        status = from_bytes(status_bytes, 2)

        if status != 0:
            raise RuntimeError(
                f'Device rejected boot command for "{name}" with status: 0x{status:04X}'
            )

        logging.info('Jumped to %s.', name)

    def stay_still(self):
        self.echo(to_bytes(0x80, 1))
        status = self.dev.read(2)

    def identify(self) -> None:
        """
        Identify the device.
        """
        hw_code = self.get_hw_code()
        hw_sub_code, hw_ver, sw_ver = self.get_hw_sw_ver()
        me_id = self.get_me_id()
        soc_id = self.get_soc_id()
        logging.info(f'HW Code: 0x{hw_code:04X}')
        logging.info(f'HW Sub-Code: 0x{hw_sub_code:04X}')
        logging.info(f'HW Version: 0x{hw_ver:04X}')
        logging.info(f'SW Version: 0x{sw_ver:04X}')
        logging.info(f'ME ID: {me_id.hex().upper()}')
        logging.info(f'SOC ID: {soc_id.hex().upper()}')

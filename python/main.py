#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Shomy
#

import argparse
import logging

from lib.device import Device


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-v',
        dest='verbose',
        action='store_true',
        help='Enable verbose output',
    )

    subparsers = parser.add_subparsers(
        dest='command', required=True, help='Command to execute'
    )

    subparsers.add_parser(
        'unlock', help='Unlock bootloader and fastboot capabilities'
    )

    subparsers.add_parser(
        'patch', help='Patch preloader to allow loading an unsigned DA'
    )

    args = parser.parse_args()

    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    path = '../bin/unlock.bin' if args.command == 'unlock' else '../bin/patch.bin'
    with open(path, 'rb') as f:
        data = f.read()
        logging.info(f'Using payload from {path}')

    device = Device(None)

    logging.info('Waiting for MediaTek Preloader device (0E8D:2000)...')

    device.find_device()
    device.handshake()
    device.identify()

    device.send_image('lk', data)
    device.boot_image('lk')


if __name__ == '__main__':
    main()

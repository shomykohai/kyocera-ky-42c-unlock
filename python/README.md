This is the old python script, kept for compatibility and archiving purposes.

# Usage

You'll need to install `python3` and the required dependencies.
Creating a venv is recommended.

## Linux

```bash
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

Make sure you are in the `dialout` 

```bash
$ sudo usermod -aG dialout $USER
```

## Windows

```powershell
> python -m venv venv
> .\venv\Scripts\activate
> pip install -r requirements.txt
```

You might also need to install MediaTek USB VCOM drivers.

---

Then, run the script:

```bash
$ python main.py unlock
```

Power off the device, and plug it in to connect into Preloader mode (port 0E8D:2000).

The device will automatically reboot and you should see a "Orange state" warning on the screen.

This **will not** automatically wipe your data, but it is recommended to perform a factory reset right after.
If you get a permission denied error, make sure to configure udev rules for the device, or run the script as root.

## Backup firmware

To perform a full backup, you'll need to install [penumbra](https://github.com/shomykohai/penumbra).
Once installed, you can run the following commands:

```bash
$ mkdir backup
$ python main.py patch
$ antumbra rl backup --skip userdata --da MTK_DA_V5.bin
```

You can get `MTK_DA_V5.bin` from [mtkclient repo](https://github.com/bkerler/mtkclient/raw/refs/heads/main/mtkclient/Loader/MTK_DA_V5.bin).

> [!NOTE]
> mtkclient is currently not compatible with this method, because of how it handles connecting on an already handshaked device.
> Any issue related to penumbra, should be reported to the [penumbra repo](https://github.com/shomykohai/penumbra).

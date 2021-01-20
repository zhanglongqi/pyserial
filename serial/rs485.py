#!/usr/bin/env python

# RS485 support
#
# This file is part of pySerial. https://github.com/pyserial/pyserial
# (C) 2015 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause

"""\
The settings for RS485 are stored in a dedicated object that can be applied to
serial ports (where supported).
NOTE: Some implementations may only support a subset of the settings.
"""

from __future__ import absolute_import

import time
import serial


class RS485Settings(object):
    def __init__(
            self,
            rts_level_for_tx=True,
            rts_level_for_rx=False,
            loopback=False,
            delay_before_tx=None,
            delay_before_rx=None,
            rts_gpio=None,
            rts_gpio_tx=1,
            rts_gpio_rx=0):
        self.rts_level_for_tx = rts_level_for_tx
        self.rts_level_for_rx = rts_level_for_rx
        self.loopback = loopback
        self.delay_before_tx = delay_before_tx
        self.delay_before_rx = delay_before_rx
        self.rts_gpio = rts_gpio
        self.rts_gpio_tx = rts_gpio_tx
        self.rts_gpio_rx = rts_gpio_rx


class RS485(serial.Serial):
    """\
    A subclass that replaces the write method with one that toggles RTS
    according to the RS485 settings.

    NOTE: This may work unreliably on some serial ports (control signals not
          synchronized or delayed compared to data). Using delays may be
          unreliable (varying times, larger than expected) as the OS may not
          support very fine grained delays (no smaller than in the order of
          tens of milliseconds).

    NOTE: Some implementations support this natively. Better performance
          can be expected when the native version is used.

    NOTE: The loopback property is ignored by this implementation. The actual
          behavior depends on the used hardware.

    Usage:

        ser = RS485(...)
        ser.rs485_mode = RS485Settings(...)
        ser.write(b'hello')
    """

    def __init__(self, *args, **kwargs):
        super(RS485, self).__init__(*args, **kwargs)
        self._alternate_rs485_settings = None

    def write(self, b):
        """Write to port, controlling RTS before and after transmitting."""
        if self._alternate_rs485_settings is not None:
            # apply level for TX and optional delay
            # self.setRTS(self._alternate_rs485_settings.rts_level_for_tx)
            if self._alternate_rs485_settings.delay_before_tx is not None:
                time.sleep(self._alternate_rs485_settings.delay_before_tx)
            if self._alternate_rs485_settings.rts_gpio is not None:
                self._alternate_rs485_settings.rts_gpio.set_value(self._alternate_rs485_settings.rts_gpio_tx)
            # write and wait for data to be written
            super(RS485, self).write(b)
            super(RS485, self).flush()
            # optional delay and apply level for RX
            if self._alternate_rs485_settings.delay_before_rx is not None:
                time.sleep(self._alternate_rs485_settings.delay_before_rx)
            if self._alternate_rs485_settings.rts_gpio is not None:
                self._alternate_rs485_settings.rts_gpio.set_value(self._alternate_rs485_settings.rts_gpio_rx)
            # self.setRTS(self._alternate_rs485_settings.rts_level_for_rx)
        else:
            super(RS485, self).write(b)

    # redirect where the property stores the settings so that underlying Serial
    # instance does not see them
    @property
    def rs485_mode(self):
        """\
        Enable RS485 mode and apply new settings, set to None to disable.
        See serial.rs485.RS485Settings for more info about the value.
        """
        return self._alternate_rs485_settings

    @rs485_mode.setter
    def rs485_mode(self, rs485_settings):
        self._alternate_rs485_settings = rs485_settings


if __name__ == '__main__':
    import gpiod

    line = gpiod.Chip('gpiochip0').get_line(34)
    line.request(consumer='rs485_rts_gpio', type=gpiod.LINE_REQ_DIR_OUT)
    rs485_settings = RS485Settings(rts_gpio=line, rts_gpio_tx=1, rts_gpio_rx=0)

    s = RS485(port='/dev/serial1', baudrate=115200)
    s.rs485_mode = rs485_settings
    import time
    while True:
        s.write(b'HI')
        time.sleep(0.01)
    s.read(2)

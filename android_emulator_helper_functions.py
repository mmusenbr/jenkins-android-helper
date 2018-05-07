#!/usr/bin/env python3

# This file is part of Jenkins-Android-Emulator Helper.
#    Copyright (C) 2018  Michael Musenbrock
#
# Jenkins-Android-Helper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Jenkins-Android-Helper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Jenkins-Android-Helper.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, re, subprocess, time

_OPWD = os.getcwd()
SCRIPT_DIR = os.path.realpath(__file__)

### assume that the script runs locally
if not 'WORKSPACE' in os.environ:
    print("It seems that the script runs outside Jenkins. WORKSPACE will be set to PWD [" + _OPWD + "]!")

WORKSPACE = os.getenv('WORKSPACE', _OPWD)
ANDROID_SDK_ROOT = os.getenv('ANDROID_SDK_ROOT', "")

ANDROID_EMULATOR_SERIAL = ""

ANDROID_ADB_PORTS_RANGE_START = 5554
ANDROID_ADB_PORTS_RANGE_END = 5584

ANDROID_SDK_TOOLS_BIN_ADB = os.path.join(ANDROID_SDK_ROOT, "platform-tools", "adb")
if os.name == "nt":
    ANDROID_SDK_TOOLS_BIN_ADB = ANDROID_SDK_TOOLS_BIN_ADB + ".exe"

## return codes
ERROR_CODE_WAIT_NO_AVD_CREATED = 1
ERROR_CODE_WAIT_AVD_CREATED_BUT_NOT_RUNNING = 2
ERROR_CODE_WAIT_EMULATOR_RUNNING_UNKNOWN_SERIAL = 3
ERROR_CODE_WAIT_EMULATOR_RUNNING_STARTUP_TIMEOUT = 4

def get_open_ports_for_process(pid_to_check):
    if os.name != "posix":
        raise NotImplementedError("get_open_ports_for_process not ported to windows")

    return subprocess.check_output("lsof -sTCP:LISTEN -i4 -P -p " + str(pid_to_check) + " -a | tail -n +2 | sed 's/  */ /g' | cut -f9 -d\" \" | cut -f2 -d: | sort -u", shell=True).decode(sys.stdout.encoding)

def android_emulator_detect_used_adb_port_by_pid(pid_to_check):
    for pos_port in range(ANDROID_ADB_PORTS_RANGE_START, ANDROID_ADB_PORTS_RANGE_END, 2):
        pos_port2 = pos_port + 1

        ports_used_by_pid = get_open_ports_for_process(pid_to_check)
        if re.search("^" + str(pos_port) + "$", ports_used_by_pid, re.MULTILINE) is not None and re.search("^" + str(pos_port2) + "$", ports_used_by_pid, re.MULTILINE) is not None:
            return pos_port

    # not found
    return -1

def android_emulator_serial_via_port_from_used_avd_name_single_run(emulator_pid):
    if emulator_pid <= 0:
        return ""

    android_adb_port_even = android_emulator_detect_used_adb_port_by_pid(emulator_pid)

    if android_adb_port_even >= 0:
        return "emulator-" + str(android_adb_port_even)
    else:
        return ""


def android_emulator_serial_via_port_from_used_avd_name(emulator_pid):
    if emulator_pid <= 0:
        return ""

    RETRIES = 10
    for i in range(1, RETRIES):
        emulator_serial = android_emulator_serial_via_port_from_used_avd_name_single_run(emulator_pid)
        if emulator_serial is not None and emulator_serial != "":
            return emulator_serial

        time.sleep(3)


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

ANDROID_AVD_NAME_UNIQUE_STORE = os.path.join(WORKSPACE, "last_unique_avd_name.tmp")
ANDROID_EMULATOR_SERIAL = ""

ANDROID_ADB_PORTS_RANGE_START = 5554
ANDROID_ADB_PORTS_RANGE_END = 5584

ANDROID_SDK_TOOLS_BIN_AVDMANAGER = os.path.join(ANDROID_SDK_ROOT, "tools", "bin", "avdmanager")
ANDROID_SDK_TOOLS_BIN_EMULATOR = os.path.join(ANDROID_SDK_ROOT, "emulator", "emulator")
ANDROID_SDK_TOOLS_BIN_ADB = os.path.join(ANDROID_SDK_ROOT, "platform-tools", "adb")
if os.name == "nt":
    ANDROID_SDK_TOOLS_BIN_AVDMANAGER = ANDROID_SDK_TOOLS_BIN_AVDMANAGER + ".exe"
    ANDROID_SDK_TOOLS_BIN_EMULATOR = ANDROID_SDK_TOOLS_BIN_EMULATOR + ".exe"
    ANDROID_SDK_TOOLS_BIN_ADB = ANDROID_SDK_TOOLS_BIN_ADB + ".exe"

## return codes
ERROR_CODE_WAIT_NO_AVD_CREATED = 1
ERROR_CODE_WAIT_AVD_CREATED_BUT_NOT_RUNNING = 2
ERROR_CODE_WAIT_EMULATOR_RUNNING_UNKNOWN_SERIAL = 3
ERROR_CODE_WAIT_EMULATOR_RUNNING_STARTUP_TIMEOUT = 4

ERROR_CODE_ADB_BINARY_NOT_FOUND = 100

## this shall only be called on avd creation, all other calls will reference this name
def generate_and_store_unique_avd_name():
    import uuid
    print(uuid.uuid4().hex, file=ANDROID_AVD_NAME_UNIQUE_STORE)

def read_unique_avd_name_from_store():
    try:
        with open(ANDROID_AVD_NAME_UNIQUE_STORE) as f:
            android_avd_name = f.readline()
    except:
        android_avd_name = ""

    return android_avd_name

def get_open_ports_for_process(pid_to_check):
    if os.name != "posix":
        raise NotImplementedError("get_open_ports_for_process not ported to windows")

    return subprocess.check_output("lsof -sTCP:LISTEN -i4 -P -p " + pid_to_check + " -a | tail -n +2 | sed 's/  */ /g' | cut -f9 -d\" \" | cut -f2 -d: | sort -u", shell=True).decode(sys.stdout.encoding)

def android_emulator_detect_used_adb_port_by_pid(pid_to_check):
    for pos_port in range(ANDROID_ADB_PORTS_RANGE_START, ANDROID_ADB_PORTS_RANGE_END, 2):
        pos_port2 = pos_port + 1

        ports_used_by_pid = get_open_ports_for_process(pid_to_check)
        if re.match("^" + str(pos_port) + "$", ports_used_by_pid) and re.match("^" + str(pos_port2) + "$", ports_used_by_pid):
            return pos_port

    # not found
    return -1

def android_emulator_get_pid(android_avd_name):
    if os.name != "posix":
        raise NotImplementedError("android_emulator_get_pid not ported to windows")

    return subprocess.check_output('pgrep -f "avd ' + android_avd_name + '"', shell=True).decode(sys.stdout.encoding).strip()

def android_emulator_serial_via_port_from_used_avd_name_single_run(android_avd_name):
    if android_avd_name is None or android_avd_name == '':
        return ""

    emulator_pid = android_emulator_get_pid(android_avd_name)
    if emulator_pid is None or emulator_pid == '':
        return ""

    android_adb_port_even = android_emulator_detect_used_adb_port_by_pid(emulator_pid)

    if android_adb_port_even >= 0:
        return "emulator-" + android_adb_port_even
    else:
        return ""


def android_emulator_serial_via_port_from_used_avd_name(android_avd_name):
    if android_avd_name is None or android_avd_name == '':
        return ""

    RETRIES = 10
    for i in range(1, RETRIES):
        emulator_serial = android_emulator_serial_via_port_from_used_avd_name_single_run(android_avd_name)
        if emulator_serial is not None and emulator_serial != '':
            return emulator_serial

        time.sleep(3)

def android_emulator_wait_for_emulator_start():
    if not os.access(ANDROID_SDK_TOOLS_BIN_ADB, os.X_OK):
        print("adb binary [" + ANDROID_SDK_TOOLS_BIN_ADB + "] not found or not an executable")
        return ERROR_CODE_ADB_BINARY_NOT_FOUND

    android_avd_name = read_unique_avd_name_from_store()
    if android_avd_name is None or android_avd_name == '':
        print("It seems that an AVD was never created! Nothing to wait for!")
        return ERROR_CODE_WAIT_NO_AVD_CREATED

    EMU_MAX_STARTUP_WAIT_TIME_BOOT_FIN = 300
    EMU_MAX_STARTUP_WAIT_FOR_PROC = 10
    EMU_STARTUP_TIME = 0

    while True:
        emulator_pid = android_emulator_get_pid(android_avd_name)
        if emulator_pid is not None and emulator_pid != '':
            break

        if EMU_STARTUP_TIME == EMU_MAX_STARTUP_WAIT_FOR_PROC:
            print("AVD with the name [" + android_avd_name + "] does not seem to run! Startup failure? Nothing to wait for!")
            return ERROR_CODE_WAIT_AVD_CREATED_BUT_NOT_RUNNING

        time.sleep(1)
        EMU_STARTUP_TIME = EMU_STARTUP_TIME + 1

    ANDROID_EMULATOR_SERIAL = android_emulator_serial_via_port_from_used_avd_name()
    if ANDROID_EMULATOR_SERIAL is None or ANDROID_EMULATOR_SERIAL == '':
        print("Could not detect ANDROID_EMULATOR_SERIAL for emulator [PID: '" + emulator_pid + "', AVD: '" + android_avd_name + "']! Can't properly wait!")
        return ERROR_CODE_WAIT_EMULATOR_RUNNING_UNKNOWN_SERIAL

    while True:
        bootanim_output = subprocess.check_output(ANDROID_SDK_TOOLS_BIN_ADB + ' -s "' + ANDROID_EMULATOR_SERIAL + '" shell getprop init.svc.bootanim', shell=True)
        if bootanim_output == "stopped":
            break

        time.sleep(5)

        if EMU_STARTUP_TIME == EMU_MAX_STARTUP_WAIT_TIME_BOOT_FIN:
            print("AVD with the name [" + android_avd_name + "] seems to run, but startup does not finish within " + EMU_MAX_STARTUP_WAIT_TIME_BOOT_FIN + " seconds!")
            return ERROR_CODE_WAIT_EMULATOR_RUNNING_STARTUP_TIMEOUT

        time.sleep(1)
        EMU_STARTUP_TIME = EMU_STARTUP_TIME + 1

def android_emulator_kill_emulator():
    if not os.access(ANDROID_SDK_TOOLS_BIN_ADB, os.X_OK):
        print("adb binary [" + ANDROID_SDK_TOOLS_BIN_ADB + "] not found or not an executable")
        return ERROR_CODE_ADB_BINARY_NOT_FOUND

    android_avd_name = read_unique_avd_name_from_store()
    if android_avd_name is None or android_avd_name == '':
        print("It seems that an AVD was never created! Nothing to do here!")
        return 0

    emulator_pid = android_emulator_get_pid(android_avd_name)
    if emulator_pid is None or emulator_pid == '':
        print("AVD with the name [" + android_avd_name + "] does not seem to run. Nothing to do here!")
        return 0

    ANDROID_EMULATOR_SERIAL = android_emulator_serial_via_port_from_used_avd_name_single_run(android_avd_name)
    if ANDROID_EMULATOR_SERIAL is None or ANDROID_EMULATOR_SERIAL == '':
        print("Could not detect ANDROID_EMULATOR_SERIAL for emulator [PID: '" + emulator_pid + "', AVD: '" + android_avd_name + "']")
        print("  > skip sending 'emu kill' command and proceed with sending kill signals")
    else:
        subprocess.run([ANDROID_SDK_TOOLS_BIN_ADB, '-s', ANDROID_EMULATOR_SERIAL, 'emu', 'kill'])

    emulator_kill_wait = 0

    while True:
        emulator_pid = android_emulator_get_pid(android_avd_name)
        if emulator_pid is None or emulator_pid == '':
            # Emulator is stopped
            break

        # send kill after 5 seconds
        if emulator_kill_wait == 5:
            subprocess.run(['kill', emulator_pid])

        # send kill after 15 seconds, and exit
        if emulator_kill_wait == 15:
            subprocess.run(['kill', '-9', emulator_pid])
            break

        time.sleep(1)

        emulator_kill_wait = emulator_kill_wait + 1

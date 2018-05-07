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

## ANDROID_SDK_ROOT needs to be set to the Android SDK

import os
import sys
import tempfile
import subprocess
import re
import uuid
import time

import jenkins_android_helper_commons
import ini_helper_functions
import android_emulator_helper_functions

#TODO:
ERROR_CODE_WAIT_NO_AVD_CREATED = 1
ERROR_CODE_WAIT_AVD_CREATED_BUT_NOT_RUNNING = 2
ERROR_CODE_WAIT_EMULATOR_RUNNING_UNKNOWN_SERIAL = 3
ERROR_CODE_WAIT_EMULATOR_RUNNING_STARTUP_TIMEOUT = 4

class AndroidSDK:
    # SDK paths
    ## root SDK directory, avd home and workspace will be read from environment
    __sdk_directory = ""
    __avd_home_directory = ""
    __workspace_directory = ""

    ## all other are relative to the root and can be retrievied via __get_full_sdk_path
    ANDROID_SDK_TOOLS_DIR = "tools"
    ANDROID_SDK_TOOLS_SRC_PROPS = os.path.join(ANDROID_SDK_TOOLS_DIR, "source.properties")
    ANDROID_SDK_TOOLS_BIN_SDKMANAGER = os.path.join(ANDROID_SDK_TOOLS_DIR, "bin", "sdkmanager")
    ANDROID_SDK_TOOLS_BIN_AVDMANAGER = os.path.join(ANDROID_SDK_TOOLS_DIR, "bin", "avdmanager")
    ANDROID_SDK_TOOLS_BIN_EMULATOR = os.path.join("emulator", "emulator")
    ANDROID_SDK_TOOLS_BIN_ADB = os.path.join("platform-tools", "adb")

    ### Info: This package shall support the platforms: linux, windows, cygwin and mac, therefore
    ### a general check is done in the constructor, and all further system dependent calls rely
    ### on a support for those platforms and no further checks are done
    ### the variables PLATFORM_ID_... shall correspond to sys.platform

    PLATFORM_ID_LINUX = "linux"
    PLATFORM_ID_MAC = "darwin"
    PLATFORM_ID_WIN = "win32"
    PLATFORM_ID_CYGWIN = "cygwin"
    SUPPORTED_PLATFORMS = [ PLATFORM_ID_LINUX, PLATFORM_ID_MAC, PLATFORM_ID_WIN, PLATFORM_ID_CYGWIN ]

    # SDK URLs and version
    ANDROID_SDK_TOOLS_ARCHIVE = { PLATFORM_ID_LINUX: "sdk-tools-linux-4333796.zip", PLATFORM_ID_MAC: "sdk-tools-darwin-4333796.zip", PLATFORM_ID_WIN: "sdk-tools-windows-4333796.zip", PLATFORM_ID_CYGWIN: "sdk-tools-windows-4333796.zip" }
    ANDROID_SDK_TOOLS_ARCHIVE_SHA256_CHECKSUM = { PLATFORM_ID_LINUX: "92ffee5a1d98d856634e8b71132e8a95d96c83a63fde1099be3d86df3106def9", PLATFORM_ID_MAC: "TODO", PLATFORM_ID_WIN: "TODO", PLATFORM_ID_CYGWIN: "TODO" }
    ANDROID_SDK_TOOLS_VERSION = "26.1.1"
    ANDROID_SDK_TOOLS_URL = "https://dl.google.com/android/repository"

    ANDROID_SDK_BUILD_TOOLS_VERSION_DEFAULT = "27.0.1"
    ANDROID_SDK_PLATFORM_VERSION_DEFAULT = "27"

    ### tools versions and properties contents
    ANDROID_SDK_TOOLS_PROP_NAME_PKG_REV = "Pkg.Revision"
    ANDROID_SDK_TOOLS_PROP_VAL_PKG_REV = ANDROID_SDK_TOOLS_VERSION
    ANDROID_SDK_TOOLS_PROP_NAME_PKG_PATH = "Pkg.Path"
    ANDROID_SDK_TOOLS_PROP_VAL_PKG_PATH = "tools"
    ANDROID_SDK_TOOLS_PROP_NAME_PKG_DESC = "Pkg.Desc"
    ANDROID_SDK_TOOLS_PROP_VAL_PKG_DESC = "Android SDK Tools"

    ## sdk licenses
    ANDROID_SDK_ROOT_LICENSE_DIR = "licenses"
    ANDROID_SDK_ROOT_LICENSE_STANDARD_FILE = os.path.join(ANDROID_SDK_ROOT_LICENSE_DIR, "android-sdk-license")
    ANDROID_SDK_ROOT_LICENSE_PREVIEW_FILE = os.path.join(ANDROID_SDK_ROOT_LICENSE_DIR, "android-sdk-preview-license")
    ANDROID_SDK_ROOT_LICENSE_STANDARD_HASH = "d56f5187479451eabf01fb78af6dfcb131a6481e"
    ANDROID_SDK_ROOT_LICENSE_PREVIEW_HASH = "84831b9409646a918e30573bab4c9c91346d8abd"

    ## sdk modules, platform-tools are always installed
    ANDROID_SDK_MODULE_PLATFORM_TOOLS = "platform-tools"
    ANDROID_SDK_MODULE_NDK = "ndk-bundle"
    ANDROID_SDK_MODULE_EMULATOR = "emulator"

    ANDROID_SDK_SYSTEM_IMAGE_IDENTIFIER = "system-images"


    __download_if_neccessary = False

    # Emulator functionality
    emulator_avd_name = ""
    emulator_pid = "0"

    ANDROID_EMULATOR_SWITCH_NO_WINDOW = "-no-window"
    ANDROID_EMULATOR_SWITCH_WIPE_DATA = "-wipe-data"

    AVD_NAME_UNIQUE_STORE_FILENAME = "last_unique_avd_name.tmp"
    EMULATOR_PID_FILENAME = "last_started_emulator.pid"

    def __init__(self):
        self.__sdk_directory = os.getenv('ANDROID_SDK_ROOT', "")
        if self.__sdk_directory is None or self.__sdk_directory == "":
            raise Exception("Environment variable ANDROID_SDK_ROOT needs to be set")

        self.__avd_home_directory = os.getenv('ANDROID_AVD_HOME', "")
        if self.__avd_home_directory is None or self.__avd_home_directory == "":
            raise Exception("Environment variable ANDROID_AVD_HOME needs to be set")

        self.__workspace_directory = os.getenv('WORKSPACE', "")
        if self.__workspace_directory is None or self.__workspace_directory == "":
            raise Exception("Environment variable WORKSPACE needs to be set")

        self.emulator_read_avd_name()
        self.__emulator_read_pid()

        if not sys.platform in self.SUPPORTED_PLATFORMS:
            raise Exception("Unsupported platform: " + sys.platform)

    def get_sdk_directory(self):
        return self.__sdk_directory

    def __get_full_sdk_path(self, relative, executable=False):
        full_path = os.path.join(self.__sdk_directory, relative)
        if executable and (sys.platform == self.PLATFORM_ID_WIN or sys.platform == self.PLATFORM_ID_CYGWIN):
            full_path = full_path + ".exe"
        return full_path

    def __get_android_sdk_download_url(self):
        return self.ANDROID_SDK_TOOLS_URL + "/" + self.ANDROID_SDK_TOOLS_ARCHIVE[sys.platform]

    def download_if_neccessary(self):
        self.__download_if_neccessary = True

    def are_sdk_tools_installed(self, verbose=False):
        if not os.path.isdir(self.__sdk_directory):
            if verbose:
                print("[%s] is not a directory" % self.__sdk_directory)
            return False

        # validate current tools
        tools_src_props_path = self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_SRC_PROPS)
        if not os.access(tools_src_props_path, os.R_OK):
            if verbose:
                print("[%s] is not readable" % tools_src_props_path)
            return False

        sdk_manager_bin = self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_BIN_SDKMANAGER, executable=True)
        if not os.access(sdk_manager_bin, os.X_OK):
            if verbose:
                print("[%s] is not executable" % sdk_manager_bin)
            return False

        if not ini_helper_functions.ini_file_helper_check_key_for_value(self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_SRC_PROPS), self.ANDROID_SDK_TOOLS_PROP_NAME_PKG_REV, self.ANDROID_SDK_TOOLS_PROP_VAL_PKG_REV):
            if verbose:
                print("TODO: ini check 1 failed")
            return False

        if not ini_helper_functions.ini_file_helper_check_key_for_value(self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_SRC_PROPS), self.ANDROID_SDK_TOOLS_PROP_NAME_PKG_PATH, self.ANDROID_SDK_TOOLS_PROP_VAL_PKG_PATH):
            if verbose:
                print("TODO: ini check 2 failed")
            return False

        if not ini_helper_functions.ini_file_helper_check_key_for_value(self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_SRC_PROPS), self.ANDROID_SDK_TOOLS_PROP_NAME_PKG_DESC, self.ANDROID_SDK_TOOLS_PROP_VAL_PKG_DESC):
            if verbose:
                print("TODO: ini check 3 failed")
            return False

        return True

    def validate_or_download_sdk_tools(self):
        if not self.are_sdk_tools_installed():
            self.download_and_install_sdk_tools()

        if not self.are_sdk_tools_installed(verbose=True):
            sys.exit(ERROR_CODE_SDK_TOOLS_INVALID)

    def download_and_install_sdk_tools(self):
        if not os.path.isdir(self.__sdk_directory):
            try:
                os.makedirs(self.__sdk_directory, exist_ok=True)
            except:
                raise Exception("Directory [%s] was not existent and could not be created!!" % self.__sdk_directory)

        if not os.access(self.__sdk_directory, os.W_OK):
            raise Exception("Directory [%s] is not writable!!" % self.__sdk_directory)

        # remove tools dir, if already exists
        jenkins_android_helper_commons.remove_file_or_dir(self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_DIR))

        with tempfile.TemporaryDirectory() as tmp_download_dir:
            dest_file_name = os.path.join(tmp_download_dir, self.ANDROID_SDK_TOOLS_ARCHIVE[sys.platform])
            jenkins_android_helper_commons.download_file(self.__get_android_sdk_download_url(), dest_file_name)

            # check archive
            COMPUTED_CHECKSUM = jenkins_android_helper_commons.sha256sum(dest_file_name)
            if COMPUTED_CHECKSUM != self.ANDROID_SDK_TOOLS_ARCHIVE_SHA256_CHECKSUM[sys.platform]:
                sys.exit(ERROR_CODE_SDK_TOOLS_ARCHIVE_CHKSUM_MISMATCH)

            try:
                jenkins_android_helper_commons.unzip(dest_file_name, self.get_sdk_directory())
            except ValueError:
                sys.exit(ERROR_CODE_SDK_TOOLS_ARCHIVE_EXTRACT_ERROR)

    def download_sdk_modules(self, build_tools_version="", platform_version="", ndk=False, system_image="", additional_modules=[]):
        sdkmanager_command = [ self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_BIN_SDKMANAGER, executable=True) ]

        sdkmanager_command = sdkmanager_command + [ self.ANDROID_SDK_MODULE_PLATFORM_TOOLS ]

        # install ndk if requested
        if ndk:
            sdkmanager_command = sdkmanager_command + [ self.ANDROID_SDK_MODULE_NDK ]

        # always install the build tools, if the given version does look bogus, fallback to default
        build_tools_version_str = self.ANDROID_SDK_BUILD_TOOLS_VERSION_DEFAULT
        if build_tools_version is not None and build_tools_version != "":
            if re.match("^[0-9]+\.[0-9]+\.[0-9]+$", build_tools_version):
                build_tools_version_str = build_tools_version
            else:
                print("Given build-tools version [" + build_tools_version + "] does not look like a valid version number")
                print("Fallback to default version [" + build_tools_version_str + "]")
        sdkmanager_command = sdkmanager_command + [ "build-tools;" + build_tools_version_str ]

        # always install a platform, if the given version does look bogus, fallback to default
        platform_version_str = self.ANDROID_SDK_PLATFORM_VERSION_DEFAULT
        if platform_version is not None and platform_version != "":
            if re.match("^[0-9]+$", platform_version):
                platform_version_str = platform_version
            else:
                print("Given platform version [" + platform_version + "] does not look like a valid version number")
                print("Fallback to default version [" + platform_version_str + "]")
        sdkmanager_command = sdkmanager_command + [ "platforms;android-" + platform_version_str ]

        # System image in form of system-images;android-24;default;x86
        # if a system image is set, also install the emulator package
        if system_image is not None and system_image != "":
            system_image_type = jenkins_android_helper_commons.split_string_and_get_part(system_image, ";", 0)
            system_image_platform = jenkins_android_helper_commons.split_string_and_get_part(system_image, ";", 1)
            system_image_vendor = jenkins_android_helper_commons.split_string_and_get_part(system_image, ";", 2)

            if system_image_type == self.ANDROID_SDK_SYSTEM_IMAGE_IDENTIFIER:
                sdkmanager_command = sdkmanager_command + [ self.ANDROID_SDK_MODULE_EMULATOR ]
                sdkmanager_command = sdkmanager_command + [ system_image ]

                ## between api level 15 and 24 there is an explicit add-ons package for google apis listed
                try:
                    system_image_api_level = int(system_image_platform.split("-")[1])
                    if system_image_vendor == "google_apis" and system_image_api_level >= 15 and system_image_api_level <= 24:
                        sdkmanager_command = sdkmanager_command + [ "add-ons;addon-google_apis-google-" + str(system_image_api_level) ]
                except:
                    pass

        sdkmanager_command = sdkmanager_command + additional_modules

        ## remove empty entries
        sdkmanager_command = list(filter(None, sdkmanager_command))

        print('echo y | ' + ' '.join(sdkmanager_command))
        subprocess.run(sdkmanager_command, input="y", encoding="utf-8", stdout=None, stderr=None)

    def create_avd(self, android_system_image, additional_properties=[]):
        if android_system_image is None or android_system_image == "":
            raise ValueError("An android emulator image needs to be set!")

        avdmanager_command = [ self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_BIN_AVDMANAGER, executable=True) ]

        avdmanager_command = avdmanager_command + [ "create", "avd", "-f", "-c", "100M", "-n", self.emulator_avd_name, "-k", android_system_image ]

        ## remove empty entries
        avdmanager_command = list(filter(None, avdmanager_command))

        print('echo no | ' + ' '.join(avdmanager_command))
        subprocess.run(avdmanager_command, input="no", encoding="utf-8", stdout=None, stderr=None).check_returncode()

        # write the additional properties to the avd config file
        avd_home_directory = os.path.join(self.__avd_home_directory, self.emulator_avd_name + ".avd")
        avd_config_file = os.path.join(avd_home_directory, "config.ini")

        for keyval in additional_properties:
            ini_helper_functions.ini_file_helper_add_or_update_key_value(avd_config_file, keyval)

    def emulator_start(self, skin="", lang="", country="", show_window=False, keep_user_data=False, additional_cli_opts=[]):
        emulator_command = [ self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_BIN_EMULATOR, executable=True) ]

        emulator_command = emulator_command + [ "-avd", self.emulator_avd_name ]

        if skin is not None and skin != "":
            emulator_command = emulator_command + [ "-skin", skin ]

        if lang is not None and lang != "":
            emulator_command = emulator_command + [ "-prop", "persist.sys.language=" + lang ]

        if country is not None and country != "":
            emulator_command = emulator_command + [ "-prop", "persist.sys.country=" + country ]

        if not show_window:
            emulator_command = emulator_command + [ self.ANDROID_EMULATOR_SWITCH_NO_WINDOW ]

        if not keep_user_data:
            emulator_command = emulator_command + [ self.ANDROID_EMULATOR_SWITCH_WIPE_DATA ]

        emulator_command = emulator_command + additional_cli_opts

        ## remove empty entries
        emulator_command = list(filter(None, emulator_command))

        print(' '.join(emulator_command))
        proc = subprocess.Popen(emulator_command, stdout=None, stderr=None, stdin=None)

        # wait a few seconds and check if the process is still running before storing the PID
        time.sleep(5)
        proc.poll()
        if proc.returncode is None:
            self.__emulator_store_pid(proc.pid)
        else:
            raise Exception("Emulator start has failed, do not write PID-file")

    def emulator_wait_for_start(self):
        emulator_wait_command = [ self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_BIN_ADB, executable=True) ]

        if self.emulator_avd_name is None or self.emulator_avd_name == '':
            print("It seems that an AVD was never created! Nothing to do here!")
            return ERROR_CODE_WAIT_NO_AVD_CREATED

        if self.emulator_pid is None or self.emulator_pid == 0:
            print("AVD with the name [" + self.emulator_avd_name + "] does not seem to run! Startup failure? Nothing to wait for!")
            return ERROR_CODE_WAIT_AVD_CREATED_BUT_NOT_RUNNING

        EMU_MAX_STARTUP_WAIT_TIME_BOOT_FIN = 300
        EMU_MAX_STARTUP_WAIT_FOR_PROC = 10
        EMU_STARTUP_TIME = 0

        ANDROID_EMULATOR_SERIAL = android_emulator_helper_functions.android_emulator_serial_via_port_from_used_avd_name(self.emulator_pid)
        if ANDROID_EMULATOR_SERIAL is None or ANDROID_EMULATOR_SERIAL == '':
            print("Could not detect ANDROID_EMULATOR_SERIAL for emulator [PID: '" + self.emulator_pid + "', AVD: '" + self.emulator_avd_name + "']! Can't properly wait!")
            return ERROR_CODE_WAIT_EMULATOR_RUNNING_UNKNOWN_SERIAL

        emulator_wait_command = emulator_wait_command + [ "-s", ANDROID_EMULATOR_SERIAL, "shell", "getprop", "init.svc.bootanim" ]

        while True:
            bootanim_output = subprocess.check_output(emulator_wait_command).decode(sys.stdout.encoding).strip()
            if bootanim_output == "stopped":
                break

            time.sleep(5)

            if EMU_STARTUP_TIME == EMU_MAX_STARTUP_WAIT_TIME_BOOT_FIN:
                print("AVD with the name [" + self.emulator_avd_name + "] seems to run, but startup does not finish within " + EMU_MAX_STARTUP_WAIT_TIME_BOOT_FIN + " seconds!")
                return ERROR_CODE_WAIT_EMULATOR_RUNNING_STARTUP_TIMEOUT

            time.sleep(1)
            EMU_STARTUP_TIME = EMU_STARTUP_TIME + 1

    def emulator_kill(self):
        emulator_kill_command = [ self.__get_full_sdk_path(self.ANDROID_SDK_TOOLS_BIN_ADB, executable=True) ]

        if self.emulator_avd_name is None or self.emulator_avd_name == '':
            print("It seems that an AVD was never created! Nothing to do here!")
            return 0

        if self.emulator_pid is None or self.emulator_pid == 0:
            print("AVD with the name [" + self.emulator_avd_name + "] does not seem to run. Nothing to do here!")
            return 0

        ANDROID_EMULATOR_SERIAL = android_emulator_helper_functions.android_emulator_serial_via_port_from_used_avd_name_single_run(self.emulator_pid)
        if ANDROID_EMULATOR_SERIAL is None or ANDROID_EMULATOR_SERIAL == '':
            print("Could not detect ANDROID_EMULATOR_SERIAL for emulator [PID: '" + self.emulator_pid + "', AVD: '" + self.emulator_avd_name + "']")
            print("  > skip sending 'emu kill' command and proceed with sending kill signals")
        else:
            emulator_kill_command = emulator_kill_command + [ '-s', ANDROID_EMULATOR_SERIAL, 'emu', 'kill' ]
            subprocess.run(emulator_kill_command)

        jenkins_android_helper_commons.kill_process_by_pid_with_force_try(int(self.emulator_pid), wait_before_kill=5, time_to_force=15)

    def run_command_with_android_serial_set(self, command=[]):
        android_emulator_serial = android_emulator_helper_functions.android_emulator_serial_via_port_from_used_avd_name(self.emulator_pid)
        return subprocess.run(command, env=dict(os.environ, ANDROID_SERIAL=android_emulator_serial)).returncode

    def write_license_files(self):
        license_dir = self.__get_full_sdk_path(self.ANDROID_SDK_ROOT_LICENSE_DIR)
        try:
            if not jenkins_android_helper_commons.is_directory(license_dir):
                os.mkdir(license_dir)
        except OSError:
            print("Directory [" + license_dir + "] was not existent and could not be created!!")
            sys.exit(ERROR_CODE_SDK_TOOLS_LICENSE_DIR_DOES_NOT_EXIST_AND_CANT_CREATE)

        with open(self.__get_full_sdk_path(self.ANDROID_SDK_ROOT_LICENSE_STANDARD_FILE), 'w') as licensefile:
            licensefile.write("\n")
            licensefile.write(self.ANDROID_SDK_ROOT_LICENSE_STANDARD_HASH)

        with open(self.__get_full_sdk_path(self.ANDROID_SDK_ROOT_LICENSE_PREVIEW_FILE), 'w') as licensefile:
            licensefile.write("\n")
            licensefile.write(self.ANDROID_SDK_ROOT_LICENSE_PREVIEW_HASH)

    def __get_unique_avd_file_name(self):
        return os.path.join(self.__workspace_directory, self.AVD_NAME_UNIQUE_STORE_FILENAME)

    def __get_last_emulator_pid_file_name(self):
        return os.path.join(self.__workspace_directory, self.EMULATOR_PID_FILENAME)

    ## this shall only be called on avd creation, all other calls will reference this name
    def generate_unique_avd_name(self):
        with open(self.__get_unique_avd_file_name(), 'w') as avdnamestore:
            print(uuid.uuid4().hex, file=avdnamestore)

        self.emulator_read_avd_name()

    def emulator_read_avd_name(self):
        try:
            with open(self.__get_unique_avd_file_name()) as f:
                self.emulator_avd_name = f.readline().strip()
        except:
            self.emulator_avd_name = ""

    ## this shall only be called on emulator start
    def __emulator_store_pid(self, pid):
        with open(self.__get_last_emulator_pid_file_name(), 'w') as pidstore:
            print(str(pid), file=pidstore)

        self.emulator_read_avd_name()

    def __emulator_read_pid(self):
        try:
            with open(self.__get_last_emulator_pid_file_name()) as pidstore:
                 self.emulator_pid = pidstore.readline().strip()
        except:
             self.emulator_pid = "0"

    def info(self):
        print("Current SDK directory: " + self.__sdk_directory)

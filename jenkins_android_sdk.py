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

import jenkins_android_helper_commons
import ini_helper_functions

class AndroidSDK:
    # SDK paths
    ## root SDK directory, will be configured
    __sdk_directory = ""
    ## all other are relative to the root and can be retrievied via __get_full_sdk_path
    ANDROID_SDK_TOOLS_DIR = "tools"
    ANDROID_SDK_TOOLS_SRC_PROPS = os.path.join(ANDROID_SDK_TOOLS_DIR, "source.properties")
    ANDROID_SDK_TOOLS_BIN_SDKMANAGER = os.path.join(ANDROID_SDK_TOOLS_DIR, "bin", "sdkmanager")

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


    def __init__(self):
        self.__sdk_directory = os.getenv('ANDROID_SDK_ROOT', "")

        if self.__sdk_directory is None or self.__sdk_directory == "":
            raise Exception("Environment variable ANDROID_SDK_ROOT needs to be set")

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


    def info(self):
        print("Current SDK directory: " + self.__sdk_directory)

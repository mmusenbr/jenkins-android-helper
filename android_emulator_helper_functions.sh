#!/usr/bin/env sh

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

ANDROID_AVD_NAME_UNIQUE_STORE="${WORKSPACE}/last_unique_avd_name.tmp"
ANDROID_EMULATOR_SERIAL=""

ANDROID_ADB_PORTS_RANGE_START=5554
ANDROID_ADB_PORTS_RANGE_END=5584

ANDROID_ADB_PORT_EVEN=""
ANDROID_ADB_PORT_UNEVEN=""

ANDROID_AVD_NAME=

ANDROID_SDK_TOOLS_BIN_AVDMANAGER="${ANDROID_SDK_ROOT}/tools/bin/avdmanager"
ANDROID_SDK_TOOLS_BIN_EMULATOR="${ANDROID_SDK_ROOT}/emulator/emulator"
ANDROID_SDK_TOOLS_BIN_ADB="${ANDROID_SDK_ROOT}/platform-tools/adb"

ERROR_CODE_ADB_BINARY_NOT_FOUND=100

## this shall only be called on avd creation, all other calls will reference this name
generate_and_store_unique_avd_name() {
	UUID_UTIL=`command -v uuidgen || true`
	if [ -z "${UUID_UTIL}" ]; then
		UUID_UTIL=`command -v uuid || true`
	fi

	if [ -z "${UUID_UTIL}" ]; then
		echo "Could not find a util to generate a unique id (uuid, uuidgen)"
		exit ${ERROR_CODE_NO_UUID_TOOL}
	fi

	"${UUID_UTIL}" | tr -d "-" > "${ANDROID_AVD_NAME_UNIQUE_STORE}"
}

read_unique_avd_name_from_store() {
	ANDROID_AVD_NAME=`cat "${ANDROID_AVD_NAME_UNIQUE_STORE}"`
}

android_emulator_detect_used_adb_port_by_pid() {
	local PID_TO_CHECK="${1}"
	for pos_port in `seq ${ANDROID_ADB_PORTS_RANGE_START} 2 ${ANDROID_ADB_PORTS_RANGE_END}`; do
		pos_port2=$((pos_port+1))

		local TMP_NR_PORTS_USED=`lsof -sTCP:LISTEN -i4 -P -p ${PID_TO_CHECK} -a | tail -n +2 | sed 's/  */ /g' | cut -f9 -d" " | cut -f2 -d: | sort -u | grep -e ^${pos_port}$ -e ^${pos_port2}$ | wc -l`
		if [ ${TMP_NR_PORTS_USED} -eq 2 ]; then
			ANDROID_ADB_PORT_EVEN=${pos_port}
			ANDROID_ADB_PORT_UNEVEN=${pos_port2}
			break
		fi
	done
}

android_emulator_get_pid() {
	pgrep -f "avd ${ANDROID_AVD_NAME}" || true
}

android_emulator_serial_via_port_from_used_avd_name_single_run() {
	ANDROID_ADB_PORT_EVEN=""
	ANDROID_ADB_PORT_UNEVEN=""
	ANDROID_EMULATOR_PORT=""
	ANDROID_EMULATOR_SERIAL=""

	EMULATOR_PID=`android_emulator_get_pid`
	if [ -n "${EMULATOR_PID}" ]; then
		android_emulator_detect_used_adb_port_by_pid "${EMULATOR_PID}"

		if [ -n "${ANDROID_ADB_PORT_EVEN}" ]; then
			ANDROID_EMULATOR_PORT=${ANDROID_ADB_PORT_EVEN}
			ANDROID_EMULATOR_SERIAL="emulator-${ANDROID_EMULATOR_PORT}"
		fi
	fi
}

android_emulator_serial_via_port_from_used_avd_name() {
	RETRIES=10
	for i in `seq 1 ${RETRIES}`; do
		ANDROID_EMULATOR_PORT=""
		android_emulator_serial_via_port_from_used_avd_name_single_run
		if [ -n "${ANDROID_EMULATOR_PORT}" ]; then
			break
		fi
		sleep 20
	done
}

android_emulator_kill_emulator() {
	if [ ! -x "${ANDROID_SDK_TOOLS_BIN_ADB}" ]; then
		echo "adb binary [${ANDROID_SDK_TOOLS_BIN_ADB}] not found or not an executable"
		return ${ERROR_CODE_ADB_BINARY_NOT_FOUND}
	fi

	read_unique_avd_name_from_store
	if [ -z "${ANDROID_AVD_NAME}" ]; then
		echo "It seems that an AVD was never created! Nothing to do here!"
		return 0
	fi

	EMULATOR_PID=`android_emulator_get_pid`
	if [ -z "${EMULATOR_PID}" ]; then
		echo "AVD with the name [${ANDROID_AVD_NAME}] does not seem to run. Nothing to do here!"
		return 0
	fi

	android_emulator_serial_via_port_from_used_avd_name_single_run
	if [ -z "${ANDROID_EMULATOR_SERIAL}" ]; then
		echo "Could not detect ANDROID_EMULATOR_SERIAL for emulator [PID: '${EMULATOR_PID}', AVD: '${ANDROID_AVD_NAME}']"
		echo "  > skip sending 'emu kill' command and proceed with sending kill signals"
	else
		${ANDROID_SDK_TOOLS_BIN_ADB} -s "${ANDROID_EMULATOR_SERIAL}" emu kill || true
	fi

	local EMU_KILL_TIME=0

	while true; do
		EMULATOR_PID=`android_emulator_get_pid`
		if [ -z "${EMULATOR_PID}" ]; then
			# Emulator is stopped
			break
		fi

		# send kill after 5 seconds
		if [ ${EMU_KILL_TIME} -eq 5 ]; then
			kill ${EMULATOR_PID} || true
		fi

		# send kill after 15 seconds, and exit
		if [ ${EMU_KILL_TIME} -eq 15 ]; then
			kill -9 ${EMULATOR_PID} || true
			break
		fi

		sleep 1

		EMU_KILL_TIME=$((EMU_KILL_TIME+1))
	done
}

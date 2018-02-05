ANDROID_AVD_NAME_UNIQUE_STORE="${WORKSPACE}/last_unique_avd_name.tmp"
ANDROID_EMULATOR_SERIAL="unknown"

ANDROID_ADB_PORTS_RANGE_START=5554
ANDROID_ADB_PORTS_RANGE_END=5584

ANDROID_ADB_PORT_EVEN=""
ANDROID_ADB_PORT_UNEVEN=""

ANDROID_AVD_NAME=

ANDROID_SDK_TOOLS_BIN_AVDMANAGER="${ANDROID_SDK_ROOT}/tools/bin/avdmanager"
ANDROID_SDK_TOOLS_BIN_EMULATOR="${ANDROID_SDK_ROOT}/emulator/emulator"
ANDROID_SDK_TOOLS_BIN_ADB="${ANDROID_SDK_ROOT}/platform-tools/adb"

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
		echo "adb binary [${ANDROID_SDK_TOOLS_BIN_ADB}] not found or not executable"
		exit ${ERROR_CODE_ADB_BINARY_NOT_FOUND}
	fi

	${ANDROID_SDK_TOOLS_BIN_ADB} -s "${ANDROID_EMULATOR_SERIAL}" emu kill || true

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

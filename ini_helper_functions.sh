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

ini_file_helper_check_key_for_value() {
	local INI_FILE_NAME="${1}"
	local INI_KEY="${2}"
	local INI_VAL_EXPECT="${3}"

	if [ ! -f ${INI_FILE_NAME} ]; then
		return 1
	fi

	if [ -z ${INI_KEY} ]; then
		return 1
	fi

	local INI_VAL="`grep "^${INI_KEY}=" ${INI_FILE_NAME} | cut -f2- -d=`"

	if [ "x${INI_VAL_EXPECT}" = "x${INI_VAL}" ]; then
		return 0
	else
		return 1
	fi
}

ini_file_helper_add_or_update_key_value() {
	local INI_FILE_NAME="${1}"
	local INI_KEY_VAL_PAIR="${2}"

	if [ ! -f ${INI_FILE_NAME} ]; then
		return 1
	fi

	if [ -z ${INI_KEY_VAL_PAIR} ]; then
		return 1
	fi

	local KEY_TO_REPLACE="`echo "${INI_KEY_VAL_PAIR}" | cut -f1 -d:`"
	local VAL_TO_REPLACE="`echo "${INI_KEY_VAL_PAIR}" | cut -f2- -d:`"

	## remove 'old' key
	sed -i "/^${KEY_TO_REPLACE}=/d" "${INI_FILE_NAME}"
	## append to end
	echo "${KEY_TO_REPLACE}=${VAL_TO_REPLACE}" >> "${INI_FILE_NAME}"
}

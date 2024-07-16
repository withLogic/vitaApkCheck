import os
import fnmatch
import math
import shutil
import subprocess
import sys
from zipfile import ZipFile
from pyaxmlparser import APK

# Where to find the APKs and what patterns to match
SOURCE_FOLDER = ''
APK_PATTERN   = '*.apk'
SO_PATTERN    = '*.so'

# Where to find the VITA_SDK binaries needed to examine elf files
BIN_DIRECTORY = 'C:\\msys64\\usr\\local\\vitasdk\\arm-vita-eabi\\bin\\'
READ_ELF_EXE  = 'readelf.exe'
READ_ELF_PATH = BIN_DIRECTORY + READ_ELF_EXE
OBJDUMP_EXE   = 'objdump.exe'
OBJDUMP_PATH  = BIN_DIRECTORY + OBJDUMP_EXE
FINDSTR_EXE   = 'findstr.exe'

# Just some search strings
FINDSTR_JC_STRING = "Java_"
FINDSTR_OPENSLES_STRINGS = ['SL_IID_ANDROIDEFFECT','SL_IID_ANDROIDEFFECTCAPABILITIES', 'SL_IID_ANDROIDEFFECTSEND', 'SL_IID_ANDROIDCONFIGURATION', 'SL_IID_ANDROIDSIMPLEBUFFERQUEUE']

# Terminal colors
x  = '\033[0m'  # reset
gr = '\033[90m' # grey
lr = '\033[91m' # light red
lg = '\033[92m' # light green
ly = '\033[93m' # light yellow
mg = '\033[95m' # magenta
cy = '\033[96m' # cyan
w  = '\033[97m' # white

# borrowed from somewhere on StackOverflow
def convert_size(size_bytes):
	if size_bytes == 0:
		return "0B"
	size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
	i = int(math.floor(math.log(size_bytes, 1024)))
	p = math.pow(1024, i)
	s = round(size_bytes / p, 2)

	return "%s %s" % (s, size_name[i])

def update_spreadsheet(list_of_data):
	attempt_successful = 0
	attempt = 1

	while attempt_successful == 0:
		try:
			worksheet.append_row( list_of_data )
			attempt_successful = 1
		except gspread.exceptions.APIError as e:
			if e.response.status_code == 429:  # Rate limit error
				attempt += 1
				sleep_time = (2 ** attempt) + (random.randint(0, 1000) / 1000)
				print(f"Sleeping for {sleep_time} seconds before retrying...")
				time.sleep(sleep_time)

def checkApk(check_apk_path):
	apk_files = []

	if os.path.isfile(check_apk_path):
		SOURCE_FOLDER = os.path.dirname(check_apk_path)
		apk_files.append( os.path.basename(check_apk_path) )
	elif os.path.isdir(check_apk_path):
		SOURCE_FOLDER = check_apk_path
		files = os.listdir(SOURCE_FOLDER)
		apk_files = fnmatch.filter(files, apk_pattern)
	else:
		print("An error has occurred.")
		return

	for apk_file in apk_files:
		apk_path = os.path.join(SOURCE_FOLDER, apk_file)
		apk_file_name, apk_file_extension = os.path.splitext(os.path.basename(apk_path))

		print(f"Processing APK: {lg}{apk_path}{x}")

		'''
		if apk_file in apks_in_spreadsheet:
			print(f" ... APK found in spreadsheet: {cy}{apk_file}{x}")
			continue	
		'''

		possible_port_has_armv7 = 0
		possible_port_has_armv6 = 0
		possible_port_has_unity = 0
		possible_port_has_gdx = 0
		possible_port_has_glesv3 = 0
		data_frame_list = []

		try:
			game_information = {}
			game_information["game_apk"] = apk_file

			apk_info =  APK(apk_path)
			if apk_info:
				game_information["game_name"] = apk_info.application
				game_information["game_package"] = apk_info.package
				game_information["game_url"] = "https://play.google.com/store/apps/details?id=" + apk_info.package
				game_information["game_version_name"] = apk_info.version_name
				game_information["game_version_code"] = apk_info.version_code
			else:
				game_information["game_name"] = " "
				game_information["game_package"] = " "
				game_information["game_version_name"] = " "
				game_information["game_version_code"] = " "

			game_information["port_verdict"] = "Possible"
			game_information["port_verdict_reason"] = " "
			port_verdict_reason_list = []

			with ZipFile(apk_path) as zip_archive:
				za_lib_list = []
				extracted_so_file = None

				for file_name in zip_archive.namelist():
					if file_name[:3] == 'lib':
						za_file_information = zip_archive.getinfo(file_name)
						za_file_size = convert_size(za_file_information.file_size)

						za_lib_list.append(file_name)

						# pull out any libunity files
						if 'libunity' in file_name:
							print(f"...{lr}{file_name}...{za_file_size}{x}")
							possible_port_has_unity = 1
							port_verdict_reason_list.append("Found libunity")

						# pull out any libgdx files
						elif 'libgdx' in file_name:
							print(f"...{lr}{file_name}...{za_file_size}{x}")
							possible_port_has_gdx = 1
							port_verdict_reason_list.append("Found libgdx")

						else:
							print(f"...{cy}{file_name}...{za_file_size} {x}")

						# for any armv7 games, let's extract the .so files
						if 'armeabi-v7a' in file_name:
							possible_port_has_armv7 = 1

							if not os.path.exists(SOURCE_FOLDER + apk_file_name):
								os.makedirs(SOURCE_FOLDER + apk_file_name)

							extracted_so_file = file_name.split('/')[-1]
							extracted_so_path = SOURCE_FOLDER + apk_file_name
							extracted_so_full_path = SOURCE_FOLDER + apk_file_name + "\\" + extracted_so_file

							with zip_archive.open(file_name) as zf, open(extracted_so_full_path, 'wb') as f:
								shutil.copyfileobj(zf, f)
						elif 'lib/armeabi/' in file_name and not possible_port_has_armv7:
							possible_port_has_armv6 = 1

							if not os.path.exists(SOURCE_FOLDER + apk_file_name):
								os.makedirs(SOURCE_FOLDER + apk_file_name)

							extracted_so_file = file_name.split('/')[-1]
							extracted_so_path = SOURCE_FOLDER + apk_file_name
							extracted_so_full_path = SOURCE_FOLDER + apk_file_name + "\\" + extracted_so_file

							with zip_archive.open(file_name) as zf, open(extracted_so_full_path, 'wb') as f:
								shutil.copyfileobj(zf, f)

				if not possible_port_has_armv7 and not possible_port_has_armv6:
					port_verdict_reason_list.append("Didn't find armeabi-v7a or armeabi")

				if len(port_verdict_reason_list):
					game_information["port_verdict"] = "Unportable"

				game_information["libs"] = "\r\n".join(za_lib_list)

				#  le's do some deeper examination of the extracted .so files
				if extracted_so_file:
					files = os.listdir(extracted_so_path)
					so_files = fnmatch.filter(files, SO_PATTERN)

					for so_file in so_files:
						print(f"Checking {lg}{so_file}{x}")
						so_file_information = {}

						so_file_information["so_file"] = so_file

						read_elf_arg = extracted_so_path + "\\" + so_file

						output = subprocess.Popen([READ_ELF_PATH, "-d", read_elf_arg], stdout=subprocess.PIPE).communicate()[0]

						output_list = output.split(b"\r\n")
						
						needed_lib_list = []

						for unfiltered_lib in output_list:
							if b"NEEDED" in unfiltered_lib:
								unfiltered_lib_string = str(unfiltered_lib)
								lib_string = unfiltered_lib_string[unfiltered_lib_string.find('[')+len('['):unfiltered_lib_string.rfind(']')]

								needed_lib_list.append(lib_string)
						
						if needed_lib_list:
							print(f"...Found the following {mg}NEEDED{x} libs")
							so_file_information["so_file_needed_libs"] = "\r\n".join(needed_lib_list)
							for lib_string in needed_lib_list:
								if 'libGLESv3' in lib_string and game_information["port_verdict"] != "Unportable":
									game_information["port_verdict"] = "Maybe possible"
									port_verdict_reason_list.append("Found libGLESv3")

								print(f"......{lib_string}")
						else:
							so_file_information["so_file_needed_libs"] = " "

						# Check for JavaCom
						check_call_string = OBJDUMP_PATH + " -T -C " + read_elf_arg + " | findstr " + FINDSTR_JC_STRING
						script = f"{check_call_string}"
						val = subprocess.Popen(['powershell', '-Command', script], stdout=subprocess.PIPE).communicate()[0]

						filtered_javacom_list = []
						val_list = val.split(b"\r\n")
						for unfiltered_javacom in val_list:
							unfiltered_javacom_string = str(unfiltered_javacom)
							filtered_javacom = unfiltered_javacom_string[unfiltered_javacom_string.find(FINDSTR_JC_STRING):-1]
							if filtered_javacom:
								filtered_javacom_list.append(filtered_javacom)

						so_file_information["so_file_found_java_count"] = len(filtered_javacom_list)
						if len(filtered_javacom_list):
							print(f"...Found {mg}{len(filtered_javacom_list)} Java_com{x} functions")
							if len(filtered_javacom_list) >= 100 and game_information["port_verdict"] != "Unportable":
								game_information["port_verdict"] = "Maybe possible"
								port_verdict_reason_list.append("Found large number of Java reqs")

						so_file_information["so_file_found_java"] = "\r\n".join(filtered_javacom_list)
						for javacom in filtered_javacom_list:
							print(f"......{cy}{javacom}{x}")

						# check for OpenSLES
						if "fmod" not in so_file:
							found_opensles_symbols = []
							for findstr_opensles_string in FINDSTR_OPENSLES_STRINGS:
								check_call_string = OBJDUMP_PATH + " -T -C " + read_elf_arg + " | findstr " + findstr_opensles_string
								script = f"{check_call_string}"
								opensles_val = subprocess.Popen(['powershell', '-Command', script], stdout=subprocess.PIPE).communicate()[0]

								opensles_val_string = str(opensles_val)
								filtered_opensles_val_string = opensles_val_string[opensles_val_string.find(findstr_opensles_string):-1]

								if(filtered_opensles_val_string):
									found_opensles_symbols.append(findstr_opensles_string)
									print(f"...Found {lr}{findstr_opensles_string}{x} symbol")
							so_file_information["open_sles_found"] = "\r\n".join(found_opensles_symbols)

							if(len(so_file_information["open_sles_found"])):
								port_verdict_reason_list.append("Found unsupported opensles symbols")
								game_information["port_verdict"] = "Unportable"
						else:
							so_file_information["open_sles_found"] = " "

						game_information["port_verdict_reason"] = "\r\n".join(port_verdict_reason_list)
						
						combined_information = {}
						combined_information.update(game_information)
						combined_information.update(so_file_information)
						
						data_frame_list.append(combined_information)
				else:
					game_information["so_file"] = " "
					game_information["so_file_needed_libs"] = " "
					game_information["so_file_found_java_count"] = " "
					game_information["so_file_found_java"] = " "
					game_information["open_sles_found"] = " "
					game_information["port_verdict_reason"] = "\r\n".join(port_verdict_reason_list)
					data_frame_list.append(game_information)

				# this is where I should update the info
				'''
				for row in data_frame_list:
					update_spreadsheet( list(row.values()) )
					print(f"... Wrote to spreadsheet")
				'''

		except Exception as error:
			print(f"{error}")
			pass
	 
		if possible_port_has_armv7 and not possible_port_has_unity and not possible_port_has_glesv3 and not possible_port_has_gdx:
			print(f"...{lg}POSSIBLE PORT{x}")
		else:
			print(f"...{lr}UNABLE TO BE PORTED{x}")

if __name__ == "__main__":
	if(len(sys.argv) == 2):
		check_apk_path = sys.argv[-1]
		checkApk(check_apk_path)
	else:
		print("First argument should be an APK or folder with APKs")
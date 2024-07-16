# vitaApkCheck

Python script to analyze an Android APK file to help determine if the Android game is a good candidate to be ported to the PlayStation Vita or not. 

### Requirements ###
* Python 3.x with the following libraries
    * os
    * fnmatch
    * math
    * shutil
    * subprocess
    * sys
    * ZilFile
    * APK
* VitaSDK

This script is provided as is.

**Note:** This script assumes that VitaSDK is installed using MSYS2 and at the following location, `C:\msys64\usr\local\vitasdk\`. 

### Usage ###
Run the following command, `python .\vitaApkCheck.py` with the first argument being a directory of APK files or a single APK file.

The script will analyze the file and display the findings.
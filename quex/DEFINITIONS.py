# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
import os
import sys

QUEX_VERSION = '0.71.2'

try:
    QUEX_INSTALLATION_DIR = os.environ["QUEX_PATH"]
    # Note, that windows can also deal with backslashes.
    QUEX_INSTALLATION_DIR = QUEX_INSTALLATION_DIR.replace("\\", "/")
except:
    print("error: environment variable 'QUEX_PATH' is not defined.")
    if os.name == "posix":
        print("error: your system is 'posix'.")
        print("error: if you are using bash-shell, append the following line")
        print("error: to your '~/.bashrc' file:")
        print("error:")
        print("error: export QUEX_PATH=directory-where-quex-has-been-installed")

    elif os.name == "nt":
        print("error: Right click on [MyComputer]")
        print("error:                  -> [Properties]")
        print("error:                       -> Tab[Advanced]")
        print("error:                            -> [Environment Variables]")
        print("error: and from there it is obvious.")

    else:
        print("error: for your system '%s' it is not known how to set environment" % os.name)
        print("error: variables. if you find out, please, send an email to")
        print("error: <fschaef@users.sourceforge.net>")
    sys.exit(-1) # sys.exit(-1) is acceptable

QUEX_PATH          = QUEX_INSTALLATION_DIR
QUEX_CODEC_DB_PATH = QUEX_PATH + "/quex/engine/codec_db/database"

sys.path.insert(0, QUEX_INSTALLATION_DIR)

def check():
    global QUEX_INSTALLATION_DIR

    # -- Try to acces the file 'quex-exe.py' in order to verify
    if os.access(QUEX_INSTALLATION_DIR + "/quex-exe.py", os.F_OK) == False:
        print("error: Environment variable 'QUEX_PATH' does not point to")
        print("error: a valid installation directory of quex.")
        print("error: current setting of 'QUEX_PATH':")
        print("error:", QUEX_INSTALLATION_DIR)
        sys.exit(-1) # sys.exit(-1) is acceptable


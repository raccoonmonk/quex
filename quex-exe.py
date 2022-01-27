#! /usr/bin/env python3
# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 

import sys
import os

import quex.engine.misc.exception_checker as exception_checker

if sys.version_info[0] < 3:
    print("error: This version of quex requires Python >= 3.0")
    print("error: Detected Python %s.%s", (sys.version_info[0], sys.version_info[1]))
    sys.exit(-1)

if "QUEX_PATH" not in os.environ:
    print("Environment variable QUEX_PATH has not been defined.")
else:
    sys.path.insert(0, os.environ["QUEX_PATH"])

try:
    exception_checker.do_on_import(sys.argv)
    import quex.DEFINITIONS
    import quex.input.command_line.core  as command_line
    import quex.core                     as core

except BaseException as instance:
    exception_checker.handle(instance)

try:
    pass
    # import psyco
    # psyco.full()
except:
    pass

if __name__ == "__main__":
    try:
        quex.DEFINITIONS.check()

        # (*) Test Exceptions __________________________________________________
        if   exception_checker.do(sys.argv):
            # Done: Tests about exceptions have been performed
            pass

        # (*) The Job __________________________________________________________
        elif command_line.do(sys.argv):
            # To do: Interpret input files and generate code or drawings.
            core.do()

    except BaseException as instance:
        exception_checker.handle(instance)



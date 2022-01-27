# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.misc.error as error

def tail(OnlyCommonF, CommonF, Name0, Sr0, Name1, Sr1):
    """Exits with error if: 

    Two state machines have some common tail, but not completely.
    """
    if not CommonF: return 
    if OnlyCommonF: return

    error.log("%s definition matches partly the\n" % Name0, 
              Sr0, DontExitF=True)
    error.log("tail of a %s, but not completely.\n" % Name1
              + "(either match completely or not at all)", Sr1)


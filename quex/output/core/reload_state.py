# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.output.core.state.entry as     entry
from   quex.output.core.variable_db import variable_db
from   quex.blackboard              import Lng
from   quex.constants               import E_StateIndices

def do(TheReloadState):
    assert TheReloadState.index in (E_StateIndices.RELOAD_FORWARD, \
                                    E_StateIndices.RELOAD_BACKWARD)
    assert TheReloadState.entry.size() != 0

    forward_f = (TheReloadState.index == E_StateIndices.RELOAD_FORWARD)

    txt, post_txt = entry.do(TheReloadState)
    txt.extend(
        Lng.RELOAD_PROCEDURE(forward_f, TheReloadState.entry.dial_db, variable_db)
    )
    txt.extend(post_txt)
    return txt


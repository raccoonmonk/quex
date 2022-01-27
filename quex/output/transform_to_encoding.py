# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.blackboard         import setup as Setup
from   quex.input.setup        import NotificationDB
import quex.engine.misc.error  as     error

def do(sm, OriginalSmList=None):
    backup_id = sm.get_id()
    ok_f, sm = Setup.buffer_encoding.do_state_machine(sm) 
    if not ok_f:
        _warn_transformation_incomplete(sm.sr, OriginalSmList)
    sm.set_id(backup_id)
    return sm

def _warn_transformation_incomplete(Sr, OriginalSmList):
    if not OriginalSmList: 
        error.warning("Pattern contains elements not found in engine codec '%s'.\n" % Setup.buffer_encoding.name \
                      + "(Buffer element size is %s [byte])" % Setup.lexatom.size_in_byte,
                      Sr, 
                      SuppressCode=NotificationDB.warning_pattern_contains_elements_beyond_encoding)
        return

    # Find out which pattern violated the encoding
    for sm_orig in OriginalSmList:
        ok_f, dummy = Setup.buffer_encoding.do_state_machine(sm_orig)
        if ok_f: continue
        _warn_transformation_incomplete(sm_orig.sr, None)


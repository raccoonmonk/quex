# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""This file defines commands that appear in 'single entry state machines'. 
They are NOT immutable. Thus, they are NOT subject to 'fly-weight-ing'.

Commands of single entry state machines should never appear together with
commands of multi-entry state machines. 

(C) Frank-Rene Schaefer
"""
from quex.engine.misc.tools import typed
from quex.engine.misc.quex_enum import QuexEnum

from quex.constants import E_AcceptanceCondition, \
                           E_AcceptanceConditionSet_string, \
                           E_IncidenceIDs, \
                           E_PostContextIDs, \
                           E_R
from functools import reduce

class SeOp:
    def __init__(self, AcceptanceId):
        self.__acceptance_id = AcceptanceId

    def set_acceptance_id(self, AcceptanceId):
        if self.__acceptance_id == E_IncidenceIDs.BAD_LEXATOM: return
        self.__acceptance_id = AcceptanceId

    def acceptance_id(self):
        return self.__acceptance_id

    def acceptance_id_is_specific(self):
        if   self.__acceptance_id == E_IncidenceIDs.MATCH_FAILURE: return False
        elif self.__acceptance_id == E_IncidenceIDs.BAD_LEXATOM:   return False
        else:                                                      return True

    def _string_annotate(self, Str):
        if self.__acceptance_id == E_PostContextIDs.NONE: return Str
        # Is the following 'if' still necessary? (fschaef9 15y03m19d)
        if self.__acceptance_id == E_IncidenceIDs.MATCH_FAILURE: return Str
        return "%s%s" % (Str, self.__acceptance_id)

    def assigned_variable_ids(self):
        assert False, "Must be implemented by derived class!"

    def required_variable_ids(self, VariableId):
        assert False, "Must be implemented by derived class!"

    def __eq__(self, Other):
        return self.__acceptance_id == Other.__acceptance_id

    def __ne__(self, Other):
        """This function implements '__ne__' for all derived classes. It relies
        on the possibly overwritten '__eq__' operator.
        """
        return not self.__eq__(self, Other)

class SeAccept(SeOp):
    def __init__(self, 
                 AcceptanceId             = E_IncidenceIDs.MATCH_FAILURE, 
                 AccConditionId           = None, 
                 RestorePositionRegisterF = False):

        SeOp.__init__(self, AcceptanceId)

        if AccConditionId is None: 
            self.__acceptance_condition_set = set()
        else:
            self.__acceptance_condition_set = set([AccConditionId])

        self.__restore_position_register_f = RestorePositionRegisterF

    def clone(self, ReplDbPreContext=None, ReplDbAcceptance=None):
        result = SeAccept()
        if ReplDbAcceptance is None: result.set_acceptance_id(self.acceptance_id())
        else:                        result.set_acceptance_id(ReplDbAcceptance[self.acceptance_id()])
        if ReplDbPreContext is None: 
            # Acceptance conditions *must* be copied upon cloning!
            result.__acceptance_condition_set = set(self.__acceptance_condition_set)
        else:                        
            if self.__acceptance_condition_set:
                # '.acceptance_condition_set()' returns a tuple which can serve 
                # as a key for the dict.
                result.__acceptance_condition_set = set()
                for acceptance_condition_id in self.__acceptance_condition_set:
                    replacement = ReplDbPreContext.get(acceptance_condition_id)
                    assert    acceptance_condition_id in E_AcceptanceCondition \
                           or replacement is not None
                    if replacement is not None: acceptance_condition_id = replacement
                    result.__acceptance_condition_set.add(acceptance_condition_id)

        result.__restore_position_register_f = self.__restore_position_register_f
        return result

    def set_acceptance_condition_id(self, PatternId):
        if PatternId is None:
            self.__acceptance_condition_set.clear()
        else:
            self.__acceptance_condition_set.add(PatternId)

    def acceptance_condition_set(self):
        return tuple(sorted(self.__acceptance_condition_set, key=QuexEnum.general_key))

    def set_restore_position_register_f(self):
        self.__restore_position_register_f = True

    def restore_position_register_f(self):
        return self.__restore_position_register_f
    
    def position_register_id(self):
        if self.restore_position_register_f() or self.__acceptance_condition_set: 
            return self.acceptance_id()
        else:
            return E_IncidenceIDs.CONTEXT_FREE_MATCH

    def assigned_variable_ids(self):
        return (
            E_R.AcceptanceRegister, 
            (E_R.PositionRegister, self.position_register_id())
        )

    def required_variable_ids(self):
        if not self.__acceptance_condition_set: 
            return ()
        else:
            return (E_R.PreContextVerdict, self.acceptance_condition_set())

    def __eq__(self, Other):
        if   not Other.__class__ == SeAccept:                     return False
        elif not SeOp.__eq__(self, Other):                        return False
        elif not self.__acceptance_condition_set == Other.__acceptance_condition_set: return False
        return self.__restore_position_register_f == Other.__restore_position_register_f

    def __str__(self):
        acceptance_id_txt = ""
        pre_txt           = ""
        restore_txt       = ""
        if self.acceptance_id() != E_IncidenceIDs.MATCH_FAILURE:
            acceptance_id_txt = repr(self.acceptance_id()).replace("L", "")

        pre_txt = E_AcceptanceConditionSet_string(self.__acceptance_condition_set)

        if self.__restore_position_register_f: 
            restore_txt = self._string_annotate("R")

        txt = [ x for x in (acceptance_id_txt, pre_txt, restore_txt) if x ]
        if txt: return "A(%s)" % reduce(lambda x, y: "%s,%s" % (x,y), txt)
        else:   return "A"

class SeStoreInputPosition(SeOp):
    @typed(RegisterId=int)
    def __init__(self, RegisterId=E_PostContextIDs.NONE):
        SeOp.__init__(self, RegisterId)

    def clone(self, ReplDbPreContext=None, ReplDbAcceptance=None):
        result = SeStoreInputPosition()
        if ReplDbAcceptance is None: result.set_acceptance_id(self.acceptance_id())
        else:                        result.set_acceptance_id(ReplDbAcceptance[self.acceptance_id()])
        return result

    def assigned_variable_ids(self):
        return ((E_R.PositionRegister, self.position_register_id()),)

    def required_variable_ids(self):
        return ()

    def position_register_id(self):
        return self.acceptance_id()

    def __eq__(self, Other):
        if   Other.__class__ != SeStoreInputPosition: return False
        return SeOp.__eq__(self, Other)

    def __str__(self):
        return self._string_annotate("S")

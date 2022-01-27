# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.code.base                       import CodeFragment, CodeFragment_NULL
from   quex.engine.analyzer.door_id_address_label import DoorID
from   quex.engine.analyzer.state.core            import Processor
from   quex.engine.analyzer.state.entry           import Entry
import quex.engine.state_machine.index            as     index
from   quex.engine.misc.tools                     import typed
from   quex.engine.state_machine.character_counter import SmLineColumnCountInfo
from   quex.engine.operations.operation_list      import Op
from   quex.blackboard import Lng

from   quex.constants import E_IncidenceIDs

from   copy  import copy

#__________________________________________________________________________
#
# TerminalState:
#                    .-------------------------------------------------.
#  .-----.           |                                                 |
#  | 341 |--'accept'--> input_p = position[2]; --->---+---------.      |
#  '-----'           |  set terminating zero;         |         |      |
#  .-----.           |                                |    .---------. |
#  | 412 |--'accept'--> column_n += length  ------>---+    | pattern | |
#  '-----'           |  set terminating zero;         |    |  match  |--->
#  .-----.           |                                |    | actions | |
#  | 765 |--'accept'--> line_n += 2;  ------------>---'    '---------' |
#  '-----'           |  set terminating zero;                          |
#                    |                                                 |
#                    '-------------------------------------------------'
# 
# A terminal state prepares the execution of the user's pattern match 
# actions and the start of the next analysis step. For this, it computes
# line and column numbers, sets terminating zeroes in strings and resets
# the input pointer to the position where the next analysis step starts.
#__________________________________________________________________________
class Terminal(Processor):
    @typed(Name=(str,str), Code=CodeFragment)
    def __init__(self, Code, Name, IncidenceId=None, RequiredRegisterSet=None,
                 RequiresLexemeBeginF=False, RequireLexemeTerminatingZeroF=False, 
                 dial_db=None,
                 PureCode=None):
        assert dial_db is not None
        assert    isinstance(IncidenceId, int) \
               or IncidenceId is None \
               or IncidenceId in E_IncidenceIDs
        Processor.__init__(self, index.get(), Entry(dial_db))
        if IncidenceId is not None: 
            self.__incidence_id = IncidenceId
            self.__door_id      = DoorID.incidence(IncidenceId, dial_db)
        else:                       
            self.__incidence_id = None
            self.__door_id      = None

        self.__code = Code
        self.__pure_code = PureCode
        if self.__pure_code is None: 
            self.__pure_code = Code.get_code()
        self.__name = Name
        if RequiredRegisterSet is not None:
            self.__required_register_set = RequiredRegisterSet
        else:
            self.__required_register_set = set()
        self.__requires_lexeme_terminating_zero_f = RequireLexemeTerminatingZeroF
        self.__requires_lexeme_begin_f            = RequiresLexemeBeginF

    @property
    def door_id(self):
        assert self.__incidence_id is not None
        assert self.__door_id is not None
        return self.__door_id

    def clone(self, NewIncidenceId=None):
        # TODO: clone manually
        result = Terminal(Code        = copy(self.__code),
                          Name        = self.__name,
                          IncidenceId = NewIncidenceId if NewIncidenceId is None \
                                                       else self.__incidence_id,
                          RequiredRegisterSet           = self.__required_register_set,
                          RequiresLexemeBeginF          = self.__requires_lexeme_begin_f,
                          RequireLexemeTerminatingZeroF = self.__requires_lexeme_terminating_zero_f,
                          dial_db                       = self.entry.dial_db, 
                          PureCode                      = self.__pure_code)
        result.__door_id = self.__door_id

        if NewIncidenceId is not None:
            result.set_incidence_id(NewIncidenceId, ForceF=True)
        return result

    def incidence_id(self):
        return self.__incidence_id

    def set_incidence_id(self, IncidenceId, ForceF=False):
        assert ForceF or self.__incidence_id is None
        self.__incidence_id = IncidenceId
        self.__door_id      = DoorID.incidence(IncidenceId, self.entry.dial_db)

    def name(self):
        return self.__name

    def code(self, dial_db):
        return self.__code.get_code()

    def pure_code(self):
        return self.__pure_code

    def requires_lexeme_terminating_zero_f(self):
        return self.__requires_lexeme_terminating_zero_f

    def requires_lexeme_begin_f(self):
        return self.__requires_lexeme_begin_f

    def required_register_set(self):
        return self.__required_register_set

class TerminalCmdList(Terminal):
    def __init__(self, IncidenceId, CmdList, Name, dial_db, RequiredRegisterSet=None):
        Terminal.__init__(self, CodeFragment_NULL, Name, IncidenceId=IncidenceId, 
                          dial_db=dial_db, RequiredRegisterSet=RequiredRegisterSet) 
        self.__cmd_list = CmdList

    def code(self, dial_db):
        return Lng.COMMAND_LIST(self.__cmd_list, dial_db)

class TerminalGotoDoorId(TerminalCmdList):
    def __init__(self, DoorId, IncidenceId, LCCI, Name, RequiredRegisterSet, terminal_factory, ExtraCmdList=None):
        if LCCI:
            run_time_counter_f, \
            cmd_list            = SmLineColumnCountInfo.get_OpList(LCCI, 
                                                                   ModeName=terminal_factory.mode_name)
            terminal_factory.run_time_counter_required_f |= run_time_counter_f
        else:
            cmd_list            = []

        if ExtraCmdList: cmd_list.extend(ExtraCmdList)
        cmd_list.append(Op.GotoDoorId(DoorId)) 

        TerminalCmdList.__init__(self, IncidenceId, cmd_list, Name, 
                                 terminal_factory.dial_db, 
                                 RequiredRegisterSet=RequiredRegisterSet)



# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.operations.operation_list          import Op, OpList
from   quex.engine.analyzer.terminal.core             import TerminalCmdList
from   quex.engine.misc.tools                         import typed
import quex.engine.state_machine.algorithm.beautifier as     beautifier
from   quex.engine.analyzer.terminal.factory          import CountCmdFactory
import quex.engine.analyzer.builder                   as     analyzer_generator
import quex.engine.analyzer.engine_supply_factory     as     engine
from   quex.constants                                 import E_R

import quex.blackboard as blackboard
from   quex.blackboard import setup as Setup

def dfa_code_list_to_analyzer(DfaCodeList, DfaIndex, OnReloadFailureDoorId, ReloadState, 
                              dial_db, OnBeforeEntry=None, OnBeforeReload=None, Engine=None,
                              ForgetLexemeUponReloadF=False, ModeName=None):
    if Engine is None: Engine = engine.Class_FORWARD()

    def _get_dfa_list(DfaCodeList):
        result = [ dfa for dfa, name, code in DfaCodeList ]
        assert not any(dfa.has_orphaned_states() for dfa in result)
        assert all(dfa.is_DFA_compliant() for dfa in result)
        return result

    dfa_list = _get_dfa_list(DfaCodeList)

    on_before_reload, \
    register_set      = _get_OnBeforeReload(Engine, dfa_list, ModeName, ForgetLexemeUponReloadF)

    analyzer, \
    state_indices_before_transformation \
        = analyzer_generator.do(dfa_list, 
                                Engine, 
                                ReloadStateExtern      = ReloadState, 
                                dial_db                = dial_db,
                                StateMachineId         = DfaIndex,
                                OnBeforeEntry          = OnBeforeEntry,
                                OnBeforeReload         = on_before_reload,
                                OnReloadFailureDoorId  = OnReloadFailureDoorId,
                                ReturnStateIndicesOfUntransformedSmF = True,
                                AlllowInitStateAcceptF = True,
                                CutF                   = OnReloadFailureDoorId is None)

    if Engine.is_CHARACTER_COUNTER():
        _append_GotoDropOutOnLexemeEnd_to_original_entries(analyzer, 
                                                           state_indices_before_transformation, 
                                                           dial_db)

    if E_R.LoopRestartP in register_set:
        cmd = Op.Assign(E_R.LoopRestartP, E_R.InputP)
        _append_Op_to_original_entries(analyzer, cmd, state_indices_before_transformation)

    assert analyzer.state_machine_id == DfaIndex
    return analyzer, register_set

def _get_on_before_reload_OpList(ModeName, UseLoopRestartF):
    register_set = set()
    if blackboard.required_counter():
        if not UseLoopRestartF:
            cmd_list = OpList(
                # Count from '_lexeme_start_p' to where reload is going to happen
                # Temporarily set 'InputP' to the end position).
                # Set '_lexeme_start_p' to position where new content is to be filled.
                # Reset InputP to its old position.
                Op.PasspartoutCounterCall(ModeName, E_R.InputP),
                Op.Assign(E_R.LexemeStartP, E_R.InputP),
            )
        else:
            cmd_list = OpList(
                # Count from '_lexeme_start_p' to where reload is going to happen
                # Temporarily set 'InputP' to the end position).
                # Set '_lexeme_start_p' to position where new content is to be filled.
                # Reset InputP to its old position.
                Op.Assign(E_R.BackupP, E_R.InputP), 
                Op.PasspartoutCounterCall(ModeName, E_R.LoopRestartP),
                Op.Assign(E_R.LexemeStartP, E_R.LoopRestartP), 
                Op.Assign(E_R.InputP, E_R.BackupP), 
            )
            register_set.add(E_R.LoopRestartP)
            register_set.add(E_R.BackupP)

    else:
        cmd_list = OpList(
            Op.Assign(E_R.LexemeStartP, E_R.InputP)
        )

    return cmd_list, register_set

def _get_OnBeforeReload(Engine, dfa_list, ModeName, ForgetLexemeUponReloadF):
    if Engine.is_CHARACTER_COUNTER() or not ForgetLexemeUponReloadF:
        result       = None
        register_set = set()
    else:
        use_LoopRestartP_f = any(Setup.buffer_encoding.lexatom_n_per_character_in_state_machine(dfa) != 1 
                                 for dfa in dfa_list)
        result,      \
        register_set = _get_on_before_reload_OpList(ModeName, use_LoopRestartP_f)

    return result, register_set

def _append_GotoDropOutOnLexemeEnd_to_original_entries(analyzer, 
                                                       state_indices_before_transformation,
                                                       dial_db):
    """Only act on 'untransformed states'. During transformation of the DFA 
    to a specific encoding extra states may have been introduced. However, the
    original states represent the borders of characters. The are the places
    where character-related operations shall happen.
    """
    # Sometimes, it is not possible to implement all characters in an encoding.
    # The according states of un-implemented characters were then removed upon 
    # transformation into encoding. 
    # States that correlate to implemented character transitions always remain!
    iterable = [
        (si, analyzer.state_db[si].entry)
        for si in state_indices_before_transformation
        if si in analyzer.state_db
    ]
    for si, entry in iterable:
        door_id = analyzer.drop_out_DoorID(si)
        cmd     = Op.GotoDoorIdIfInputPEqualPointer(door_id, E_R.LexemeEnd)
        entry.append_Op_on_all(cmd.clone())

def _append_Op_to_original_entries(analyzer, cmd, state_indices_before_transformation):
    """Only act on 'untransformed states'. During transformation of the DFA 
    to a specific encoding extra states may have been introduced. However, the
    original states represent the borders of characters. The are the places
    where character-related operations shall happen.
    """
    # Sometimes, it is not possible to implement all characters in an encoding.
    # The according states of un-implemented characters were then removed upon 
    # transformation into encoding. 
    # States that correlate to implemented character transitions always remain!
    iterable = [
        analyzer.state_db[si].entry
        for si in state_indices_before_transformation
        if si in analyzer.state_db
    ]
    for entry in iterable:
        entry.append_Op_on_all(cmd.clone())

@typed(count_cmd_factory=CountCmdFactory)
def insertCountCmdList(count_cmd_factory, DfaCodeList, BeatifyF=True):
    """For each entry in 'DfaCodeList' add the column-line number counting commands
    to the list which are appropriate for the according DFA. 

    The third element of the list tells whether count commands need to be inserted.
    """
    #___________________________________________________________________________
    # NOTE 'AllowConstTermsF=False':
    # Reload ignores and resets the lexeme start position. A counting expression 
    # that states something like:
    #
    #                 dfa matches => column_n + 5
    #
    # is wrong because on the way to the lexeme match a reload may have happened
    # which already incremented the column_n to an extend. For example, if the 
    # reload happend after the third character, then before reload 'column_n += 3'. 
    # If upon match the 'column_n += 5', the total increment of 8 would have been
    # applied. This is wrong.
    #
    # However, an expression that respects the new position of lexeme start, such
    # as 'column_n += (current position - lexeme start) * const.' is fine.
    #___________________________________________________________________________
    def _do(dfa, name, insert_count_commands_f, cmd_list):
        if insert_count_commands_f:
            cmd_list[:0] = count_cmd_factory.get(dfa)
        if BeatifyF: return beautifier.do(dfa), name, cmd_list
        else:        return dfa, name, cmd_list

    if not blackboard.required_counter():
        return [
            (dfa, name, cmd_list)
            for dfa, name, insert_count_commands_f, cmd_list in DfaCodeList
        ]
    else:
        return [
            _do(dfa, name, insert_count_commands_f, cmd_list)
            for dfa, name, insert_count_commands_f, cmd_list in DfaCodeList
        ]

def dfa_code_list_terminals(code_list_iterable, dial_db):
    return [
        TerminalCmdList(dfa.get_id(), code, name, dial_db)
        for dfa, name, code in code_list_iterable
    ]


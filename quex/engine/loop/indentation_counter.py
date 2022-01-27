# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.analyzer.door_id_address_label           import DoorID
from   quex.engine.analyzer.terminal.factory                import CountCmdFactory
from   quex.engine.loop.common                              import dfa_code_list_to_analyzer, \
                                                                   insertCountCmdList, \
                                                                   dfa_code_list_terminals
from   quex.engine.misc.tools                               import typed
from   quex.engine.operations.operation_list                import Op, OpList
from   quex.engine.state_machine.core                       import DFA
from   quex.engine.state_machine.index                      import get_state_machine_id
import quex.engine.state_machine.algebra.union              as     union
from   quex.engine.counter                                  import IndentationCount_Pre, \
                                                                   CountActionMap
from   quex.constants                                       import E_R

from   itertools import chain

@typed(CaMap=CountActionMap, IndentationSetup=IndentationCount_Pre)
def do(ModeName, CaMap, IndentationSetup, ReloadState, dial_db):
    """________________________________________________________________________
    Counting whitespace at the beginning of a line.

    TODO: Rewrite --------------------

    An indentation counter is a single state that iterates to itself as long
    as whitespace occurs. During that iteration the column counter is adapted.
    There are two types of adaption:

       -- 'normal' adaption by a fixed delta. This adaption happens upon
          normal space characters.

       -- 'grid' adaption. When a grid character occurs, the column number
          snaps to a value given by a grid size parameter.

    When a newline occurs the indentation counter exits and restarts the
    lexical analysis. If the newline is not followed by a newline suppressor
    the analyzer will immediately be back to the indentation counter state.
    ___________________________________________________________________________
    """
    def _get_finalized_sm(P, CaMap):
        if P is None: return
        else:         return P.finalize(CaMap).sm

    whitespace         = _get_finalized_sm(IndentationSetup.pattern_whitespace, CaMap)
    suspend_list       = [ _get_finalized_sm(p, CaMap) for p in IndentationSetup.pattern_suspend_list ]
    suspend_list       = [ sm for sm in suspend_list if sm is not None ]
    newline            = _get_finalized_sm(IndentationSetup.pattern_newline, CaMap)
    suppressed_newline = _get_finalized_sm(IndentationSetup.pattern_suppressed_newline, CaMap)
    badspace           = _get_finalized_sm(IndentationSetup.pattern_badspace, CaMap)

    # 'whitespace' must accept on empty
    whitespace.get_init_state().set_acceptance(True)

    # ENTRY:
    #   indentation = 0
    #   GOTO INDENTATION
    #
    # INDENTATION:
    #   badspace   -> CALL 'on_indentation_bad' handler
    #   whitespace -> AFTER_INDENTATION
    #
    # AFTER_INDENTATION:
    #   suspend        -> SEEK before suspend
    #                     EXIT
    #   accept_nothing -> SEEK before suspend
    #                     CALL indentation_handler(indenation)
    #                     EXIT
    INDENTATION_sm_idx        = get_state_machine_id()
    INDENTATION_door_id       = DoorID.state_machine_entry(INDENTATION_sm_idx, dial_db)
    AFTER_INDENTATION_sm_idx  = get_state_machine_id()
    AFTER_INDENTATION_door_id = DoorID.state_machine_entry(AFTER_INDENTATION_sm_idx, dial_db)
    ON_RELOAD_FAILURE_door_id = None # Nothing special to be done

    count_cmd_factory = CountCmdFactory(ModeName, CaMap, AllowConstTermsF=False)

    INDENTATION_dfa_code_list       = _until_first_non_whitspace(badspace, whitespace, 
                                                                 ModeName, AFTER_INDENTATION_door_id, 
                                                                 count_cmd_factory, dial_db)

    AFTER_INDENTATION_dfa_code_list = _on_first_non_whitespace(newline, suppressed_newline, suspend_list,
                                                               ModeName, INDENTATION_door_id, 
                                                               count_cmd_factory, dial_db)

    on_before_entry = OpList(Op.Assign(E_R.LexemeStartP, E_R.InputP))
    count_cmd_factory.run_time_counter_f = True # See PasspartoutCounterCall

    reload_state = ReloadState
    # If the reload state is created, all analyzers shall use the same
    INDENTATION_analyzer, register_set0       = dfa_code_list_to_analyzer(INDENTATION_dfa_code_list, INDENTATION_sm_idx, 
                                                           ON_RELOAD_FAILURE_door_id,
                                                           reload_state, dial_db, 
                                                           OnBeforeEntry           = on_before_entry,
                                                           ForgetLexemeUponReloadF = True,
                                                           ModeName                = ModeName)
    reload_state               = INDENTATION_analyzer.reload_state
    AFTER_INDENTATION_analyzer, register_set1 = dfa_code_list_to_analyzer(AFTER_INDENTATION_dfa_code_list, AFTER_INDENTATION_sm_idx, 
                                                           ON_RELOAD_FAILURE_door_id,
                                                           reload_state, dial_db, 
                                                           ModeName=ModeName)

    analyzer_list = [ INDENTATION_analyzer, AFTER_INDENTATION_analyzer ]
    terminal_list = dfa_code_list_terminals(
        chain(INDENTATION_dfa_code_list, AFTER_INDENTATION_dfa_code_list), dial_db)

    return analyzer_list, terminal_list, \
           register_set0.union(register_set1), \
           count_cmd_factory.run_time_counter_f
        
def _until_first_non_whitspace(badspace, whitespace, ModeName, AFTER_INDENTATION_door_id, count_cmd_factory, dial_db):
    result = []
    if badspace:
        result.append((badspace, "<bad indentation_character>", True, [
             Op.IndentationBadHandlerCall(ModeName),
             Op.Assign(E_R.LexemeStartP, E_R.InputP),
             Op.ReturnFromLexicalAnalysis()]))

    result.append((whitespace, "<whitespace>", True, [
        Op.Assign(E_R.LexemeStartP, E_R.InputP),
        Op.GotoDoorId(AFTER_INDENTATION_door_id)]))
    dial_db.mark_address_as_gotoed(AFTER_INDENTATION_door_id.related_address)

    return insertCountCmdList(count_cmd_factory, result)

def _on_first_non_whitespace(newline, suppressed_newline, suspend_list,
                             ModeName, INDENTATION_door_id, 
                             count_cmd_factory, dial_db):
    accept_nothing = DFA.Nothing()
    result = [
        (accept_nothing, "<accept_on_nothing>", False, [
            # No counting required; input pointer is reset.
            Op.IndentationHandlerCall(ModeName),
            Op.Assign(E_R.LexemeStartP, E_R.InputP),
            Op.GotoDoorId(DoorID.continue_without_on_after_match(dial_db))
         ])
    ]
    result.append(
        (newline, "<newline>", True, [
             Op.GotoDoorId(INDENTATION_door_id)
         ])
    )

    if suppressed_newline:
        result.append(
            (suppressed_newline, "<suppressed_newline>", True, [
                 Op.GotoDoorId(INDENTATION_door_id)
            ])
        )
    
    if suspend_list:
        result.append(
            (union.do(suspend_list), "<union_of_suspend_list>", False, [
                # No counting required; input pointer is reset.
                Op.Assign(E_R.InputP, E_R.LexemeStartP),
                Op.GotoDoorId(DoorID.continue_without_on_after_match(dial_db))
             ])
        )

    return insertCountCmdList(count_cmd_factory, result)


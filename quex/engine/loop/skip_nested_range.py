# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# PURPOSE: Skipper for range limitted regions in the input stream
#
# This module generates skippers which are determined by patterns that open
# and close nested ranges of skipped characters.
#
# Skipping can happen either from an opening delimiter to a closing delimiter
# (e.g '/*' to '*/' in the C-Language), or even nested ranges are admissible.
# Without nesting, only closing delimiters are considered and the skipping ends
# as soon as such a closing delimiter is found.  With nested ranges, opening 
# delimiters are detected and increment the 'nesting level'. Closing delimiters
# decrement the nesting level. With nested range skipping, the skipping only 
# stops when the nesting level is zero.
#
# Additionally, 'suppressor' patterns can be specified. If a 'suppressor'
# pattern appears before an opener or a closer, it is ignored. For example
# given a suppressor '\' and a closer '\n' (newline), skipping only stops
# at newline, if and only if it is not preceeded by '\'.
#
# (C) Frank-Rene Schaefer; Licence MIT
#______________________________________________________________________________
from   quex.engine.analyzer.terminal.factory                import CountCmdFactory
from   quex.engine.analyzer.door_id_address_label           import DoorID
from   quex.engine.loop.common                              import dfa_code_list_to_analyzer, \
                                                                   dfa_code_list_terminals, \
                                                                   insertCountCmdList
from   quex.engine.counter                                  import CountActionMap
from   quex.engine.operations.operation_list                import Op, OpList
from   quex.engine.state_machine.cut.operations_on_lexemes  import first_complement
import quex.engine.state_machine.construction.sequentialize as     sequentialize
import quex.engine.state_machine.construction.repeat        as     repeat
from   quex.engine.state_machine.index                      import get_state_machine_id
import quex.engine.state_machine.algorithm.beautifier       as     beautifier
import quex.engine.state_machine.algebra.complement_variants as    complement_variants
import quex.engine.state_machine.algebra.union               as    union
from   quex.engine.misc.tools                               import typed
from   quex.blackboard                                      import setup as Setup, Lng
from   quex.constants                                       import E_R, E_IncidenceIDs

from   itertools import chain

@typed(CaMap=CountActionMap)
def do(ModeName, CaMap, 
       OpenerPattern,           CloserPattern, 
       OpenerSuppressorPattern, CloserSuppressorPattern,
       DoorIdExit, ReloadState, dial_db, 
       NestedF=True):
    """
    RETURNS: [0][0] Analyzer that eats the first character of an opener/closer
                     or iterates on remaining characters.
             [0][1] Analyzer that detects delimiters. 
             [1] Terminals
             [2] Required set of registers
             [3] Flag, indiciating whether dynamic run-time counting is required.
    """

    if NestedF: Lng.debug_unit_name_set("%s:skip_nested_range" % ModeName)
    else:       Lng.debug_unit_name_set("%s:skip_range" % ModeName)

    def _get_finalized_sm(P, CaMap):
        if P is None: return
        else:         return P.finalize(CaMap).sm

    opener            = _get_finalized_sm(OpenerPattern, CaMap)
    closer            = _get_finalized_sm(CloserPattern, CaMap)
    closer_suppressor = _get_finalized_sm(CloserSuppressorPattern, CaMap)
    opener_suppressor = _get_finalized_sm(OpenerSuppressorPattern, CaMap)


    UNTIL_FIRST_sm_idx  = get_state_machine_id()
    UNTIL_FIRST_door_id = DoorID.state_machine_entry(UNTIL_FIRST_sm_idx, dial_db)
    DELIMITER_sm_idx    = get_state_machine_id()
    DELIMITER_door_id   = DoorID.state_machine_entry(DELIMITER_sm_idx, dial_db)

    ON_RELOAD_FAILURE_door_id = DoorID.incidence(E_IncidenceIDs.SKIP_RANGE_OPEN,
                                                 dial_db)


    count_cmd_factory  = CountCmdFactory(ModeName, CaMap, AllowConstTermsF=False)

    UNTIL_FIRST_dfa_code_list = _until_first_delimiter_character(opener, closer, 
                                                                 opener_suppressor, closer_suppressor, 
                                                                 DELIMITER_door_id,
                                                                 count_cmd_factory, dial_db)

    DELIMITER_dfa_code_list = _delimiters(opener, closer, opener_suppressor, closer_suppressor, 
                                          UNTIL_FIRST_door_id, DoorIdExit, 
                                          count_cmd_factory, dial_db, NestedF)

    # 'OpList_on_before_reload_if_lexeme_is_not_maintained()'
    # => calls 'Op.PasspartoutCounterCall()'
    count_cmd_factory.run_time_counter_f = True

    on_before_entry = OpList(Op.Assign(E_R.LexemeStartP, E_R.InputP))

    UNTIL_FIRST_analyzer, \
    register_set0         = dfa_code_list_to_analyzer(UNTIL_FIRST_dfa_code_list, UNTIL_FIRST_sm_idx, 
                                                      ON_RELOAD_FAILURE_door_id,
                                                      ReloadState, dial_db, 
                                                      OnBeforeEntry           = on_before_entry,
                                                      ForgetLexemeUponReloadF = True,
                                                      ModeName                = ModeName)

    reload_state        = UNTIL_FIRST_analyzer.reload_state
    DELIMITER_analyzer, \
    register_set1       = dfa_code_list_to_analyzer(DELIMITER_dfa_code_list, DELIMITER_sm_idx, 
                                                    ON_RELOAD_FAILURE_door_id,
                                                    reload_state, dial_db, 
                                                    OnBeforeEntry = on_before_entry, 
                                                    ModeName      = ModeName)

    terminal_list = dfa_code_list_terminals(
        chain(UNTIL_FIRST_dfa_code_list, DELIMITER_dfa_code_list), dial_db)

    required_register_set = register_set0.union(register_set1)
    if NestedF: required_register_set.add(E_R.Counter)

    return [ UNTIL_FIRST_analyzer, DELIMITER_analyzer ], \
           terminal_list, \
           required_register_set, \
           count_cmd_factory.run_time_counter_f

def _until_first_delimiter_character(opener, closer, opener_suppressor, closer_suppressor, 
                                     DELIMITER_door_id,
                                     count_cmd_factory, dial_db):
    not_first_repeated_sm = beautifier.do(
        repeat.do(first_complement([opener, closer, opener_suppressor, closer_suppressor], 
                                   Setup.buffer_encoding.source_set), 
                  min_repetition_n=0)
    )

    result = [
        (not_first_repeated_sm, "<not first repeated>", True, [
                Op.Assign(E_R.LexemeStartP, E_R.InputP),
                Op.GotoDoorId(DELIMITER_door_id)]),
    ]
    return insertCountCmdList(count_cmd_factory, result, BeatifyF=False)

def _delimiters(opener, closer, opener_suppressor, closer_suppressor, 
                UNTIL_FIRST_door_id, DoorIdExit, count_cmd_factory, dial_db, NestedF):

    dfa_code_list = []
    if NestedF: # Todo: pass as argument!
        dfa_code_list.extend([
            (opener, "<opener>", True, [
                    Op.Increment(E_R.Counter),
                    Op.GotoDoorId(UNTIL_FIRST_door_id)]),
            (closer, "<closer>", True, [
                    Op.Decrement(E_R.Counter),
                    Op.GotoDoorIdIfCounterEqualZero(DoorIdExit),
                    Op.GotoDoorId(UNTIL_FIRST_door_id)])
        ])
    else:
        dfa_code_list.append(
            (closer, "<closer>", True, [
                    Op.GotoDoorId(DoorIdExit)])
        )

    if not closer_suppressor.is_Empty():
        closer_suppressor_closer = beautifier.do(sequentialize.do([closer_suppressor, closer]))
        dfa_code_list.append(
            (closer_suppressor_closer, "<closer suppressor + closer>", True, [
                Op.GotoDoorId(UNTIL_FIRST_door_id)]))

    if not opener_suppressor.is_Empty():
        opener_suppressor_opener = beautifier.do(sequentialize.do([opener_suppressor, opener]))
        dfa_code_list.append(
            (opener_suppressor_opener, "<opener suppressor + opener>", True, [ 
                Op.GotoDoorId(UNTIL_FIRST_door_id)]))

    delimiter_union_tnot = union.do([
        complement_variants.acceptance_inversion(dfa)
        for dfa, x, x, x in dfa_code_list
    ])

    dfa_code_list.append(
        (delimiter_union_tnot, "<no delimiter match>", True, [
            Op.GotoDoorId(UNTIL_FIRST_door_id)
         ]))

    return insertCountCmdList(count_cmd_factory, dfa_code_list, BeatifyF=False)

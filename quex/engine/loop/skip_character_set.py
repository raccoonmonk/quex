# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: Efficient character set skipper / Character-related counting

Given a character set, this module generates an analyzer and according
terminals to perform efficient character set skipping. Related counting
actions are also performed.

AUTHOR: (C) Frank-Rene Schaefer; MIT-License.
"""
from   quex.engine.state_machine.index            import get_state_machine_id
from   quex.engine.state_machine.core             import DFA
from   quex.engine.operations.operation_list      import Op, OpList
from   quex.engine.analyzer.terminal.factory      import CountCmdFactory
from   quex.engine.analyzer.door_id_address_label import DoorID
from   quex.engine.counter                        import CountActionMap
from   quex.engine.misc.tools                     import typed
from   quex.engine.loop.common                    import insertCountCmdList, \
                                                         dfa_code_list_to_analyzer, \
                                                         dfa_code_list_terminals
                                                         
from   quex.blackboard import Lng
from   quex.constants  import E_R, \
                              E_CharacterCountType

@typed(CaMap=CountActionMap)
def do(ModeName, CaMap, CharacterSet, ReloadState, dial_db, 
       EngineType=None, EXIT_door_id=None, EnforceConstCountTermsF=False):
    """Generate analyzer and according terminals for skipping/counting
    the given character set.

    CharacterSet: set of characters to be skipped.
    CaMap:        count-action map, i.e. what character has to be counted how.

    RETURNS: [0] list of analyzers (size = 1)
             [1] list of terminals
             [2] list of character sets involved
             [3] set of required registers for computation
    """
    if EngineType is not None:
        engine_type = EngineType
    else:
        if ReloadState: engine_type = ReloadState.engine_type
        else:           engine_type = None

    Lng.debug_unit_name_set("%s:skip" % ModeName)
    if engine_type is None or not engine_type.is_CHARACTER_COUNTER():
        name = "skip_character_set"
    else:
        name = "column_line_counter"

    LOOP_sm_id                = get_state_machine_id()
    LOOP_door_id              = DoorID.state_machine_entry(LOOP_sm_id, dial_db)
    ON_RELOAD_FAILURE_door_id = None # Nothing special to be done
    # If nothing matches, leave the skipping loop.
    if EXIT_door_id is None:
        EXIT_door_id = DoorID.continue_without_on_after_match(dial_db)

    multi_step_character_set_list, \
    single_step_character_set_list = _sort_character_sets(CaMap, CharacterSet, 
                                                          EnforceConstCountTermsF)

    dfa_code_list = _get_dfa_code_list(multi_step_character_set_list,
                                       single_step_character_set_list,
                                       LOOP_door_id,
                                       EXIT_door_id,
                                       name)

    dfa_code_list = _insert_counting_commands(dfa_code_list, CaMap, engine_type, 
                                              EnforceConstCountTermsF,
                                              ModeName)

    on_before_entry = OpList(Op.Assign(E_R.LexemeStartP, E_R.InputP))

    analyzer, \
    register_set = dfa_code_list_to_analyzer(dfa_code_list, LOOP_sm_id, 
                                             ON_RELOAD_FAILURE_door_id,
                                             ReloadState, dial_db, 
                                             OnBeforeEntry            = on_before_entry,
                                             ForgetLexemeUponReloadF  = True,
                                             ModeName                 = ModeName,
                                             Engine                   = engine_type)

    if multi_step_character_set_list and EnforceConstCountTermsF:
        register_set.add(E_R.CountReferenceP)

    return [ analyzer ], \
           dfa_code_list_terminals(dfa_code_list, dial_db), \
           multi_step_character_set_list + single_step_character_set_list, \
           register_set

def _sort_character_sets(CaMap, CharacterSet, EnforceConstCountTermsF):
    """Seperates the given 'CharacterSet' into easy-to-digest character sets
    for column and line number counting:

      (1) Separate character set into sets of characters that can be counted
          by the exact counting action (e.g. column += 1).

      (2a) Character sets, where the increment to column/line number is
           independent of the current value of column or line nubers.

      (2b) Character sets, where the increment can only be computed at run-time
           when the current value of column/line is known, i.e. 'grid steps' 
           such as tabulators.

    RETURNS: [0] Charactre sets of (2a).
                 Those sets can be implemented as REPETITION.
             [1] The character sets of (2b)
                 Those sets CANNOT be implemented as REPETITION.
    """
    # Sets of characters of same counting actions
    iterable = [ x for x in CaMap.iterable_in_sub_set(CharacterSet) ]

    #
    if not EnforceConstCountTermsF:
        multi_step_character_set_list = [
            number_set for number_set, count_action in iterable
        ]
        single_step_character_set_list = [
        ]
    else:
        allows_const_increment = (E_CharacterCountType.COLUMN, E_CharacterCountType.LINE)
        multi_step_character_set_list = [
            number_set
            for number_set, count_action in iterable
            if count_action in allows_const_increment
        ]
        single_step_character_set_list = [
            number_set
            for number_set, count_action in iterable
            if count_action not in allows_const_increment
        ]

    return multi_step_character_set_list, \
           single_step_character_set_list

def _get_dfa_code_list(multi_step_character_set_list, 
                       single_step_character_set_list, 
                       LOOP_door_id,
                       EXIT_door_id, 
                       name):
    """Generate a list of (dfa, name, count_flag, cmd_list)
    """
    def _one_or_any_repetition(CharacterSet):
        dfa = DFA()
        si  = dfa.add_transition(dfa.init_state_index, CharacterSet, AcceptanceF=True)
        dfa.add_transition(si, CharacterSet, si)
        return dfa

    # Repeat as much as possible on the same character set with the same
    # character count action (e.g. 'column += constant * lexeme_length')
    dfa_code_list = [
        # 'True', because 'cmd_list' cannot be applied. Here, a count action
        # for the repeated character set is required.
        (_one_or_any_repetition(character_set), "<TERMINAL %s (multi step)>" % name, True, [
            Op.Assign(E_R.LexemeStartP, E_R.InputP),
            Op.GotoDoorId(LOOP_door_id)
        ])
        for character_set in multi_step_character_set_list
    ] 
    dfa_code_list.extend([
        # 'True', because 'cmd_list' cannot be applied. Here, a count action
        # for the repeated character set is required.
        (DFA.from_character_set(character_set), "<TERMINAL %s (single step)>" % name, True, [
            Op.Assign(E_R.LexemeStartP, E_R.InputP),
            Op.GotoDoorId(LOOP_door_id)
        ])
        for character_set in single_step_character_set_list
    ])

    # 'False': Lexeme has zero-length => no counting required.
    dfa_code_list.append((DFA.Nothing(), "<TERMINAL %s exit>" % name, False, [
                          Op.GotoDoorId(EXIT_door_id)]))

    return dfa_code_list

def _insert_counting_commands(dfa_code_list, CaMap, engine_type, EnforceConstCountTermsF, ModeName):
    shift_commands_f  = not engine_type or not engine_type.is_CHARACTER_COUNTER()
    count_cmd_factory = CountCmdFactory(ModeName, CaMap, 
                                        AllowConstTermsF=EnforceConstCountTermsF,
                                        InsertShiftCommandsF=shift_commands_f)
    dfa_code_list     = insertCountCmdList(count_cmd_factory, dfa_code_list, 
                                           BeatifyF=True)

    if EnforceConstCountTermsF:
        for dfa, name, cmd_list in dfa_code_list:
            assert not any(cmd.id == Op.PasspartoutCounterCall for cmd in cmd_list)

    # 'OpList_on_before_reload_if_lexeme_is_not_maintained()'
    # => calls 'Op.PasspartoutCounterCall()'
    if not EnforceConstCountTermsF:
        count_cmd_factory.run_time_counter_f = True

    return dfa_code_list


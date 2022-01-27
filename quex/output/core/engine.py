# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# (C) Frank-Rene Schaefer
#______________________________________________________________________________
from   quex.engine.analyzer.door_id_address_label import get_plain_strings
from   quex.engine.misc.tools                     import all_isinstance, \
                                                         typed, \
                                                         flatten
from   quex.output.core.variable_db               import variable_db
import quex.output.core.base                      as     generator
import quex.output.counter.run_time               as     run_time_counter

from   quex.blackboard import setup as Setup, \
                              Lng
from   quex.constants  import E_IncidenceIDs
from   operator import attrgetter

@typed(ModeNameList = [str])
def do(Mode, ModeNameList):
    """RETURNS: The analyzer code for a mode defined in 'Mode'.
    """
    variable_db.init() 

    function_body,       \
    variable_definitions = do_core(Mode) 

    function_txt = wrap_up(Mode.name, function_body, variable_definitions, 
                           ModeNameList, Mode.dial_db)

    return function_txt

def do_with_counter(Mode, ModeNameList):
    txt = []
    if Mode.ca_map_for_run_time_counter is not None:
        variable_db.init()
        Lng.debug_unit_name_set("Counter:%s" % Mode.name)
        txt.append(
            run_time_counter.get(Mode.ca_map_for_run_time_counter, Mode.name)
        )

    analyzer_txt = do(Mode, ModeNameList)
    assert isinstance(analyzer_txt, list)
    txt.extend(analyzer_txt)
    return txt

def do_core(Mode):
    """Produces main code for an analyzer function which can detect patterns given in
    the 'PatternList' and has things to be done mentioned in 'TerminalDb'. 

    RETURN: Code implementing the lexical analyzer.

    The code is not embedded in a function and required definitions are not provided.
    This happens through function 'wrap_up()'.
    """
    # Prepare the combined state machines and terminals 
    TerminalDb         = Mode.terminal_db
    ReloadStateForward = Mode.reload_state_forward
    OnAfterMatchCode   = Mode.incidence_db.get(E_IncidenceIDs.AFTER_MATCH)
    dial_db            = Mode.dial_db

    variable_db.require_registers(flatten(
        terminal.required_register_set()
        for terminal in TerminalDb.values()
    ))

    # (*) Pre Context DFA
    #     (If present: All pre-context combined in single backward analyzer.)
    Lng.debug_unit_name_set("%s:Pre-Context:%s")
    pre_context,         \
    pre_analyzer         = generator.do_pre_context(Mode.pre_context_sm_to_be_reversed_list,
                                                    Mode.pre_context_sm_id_list,
                                                    dial_db)
    # assert all_isinstance(pre_context, (IfDoorIdReferencedCode, int, str, unicode))

    # (*) Backward input position detection
    #     (Seldomly present -- only for Pseudo-Ambiguous Post Contexts)
    Lng.debug_unit_name_set("%s:Backward-Input-Position-Detection" % Mode.name)
    bipd                 = generator.do_backward_read_position_detectors(Mode.bipd_sm_to_be_reversed_db,
                                                                         dial_db)
    # assert all_isinstance(bipd, (IfDoorIdReferencedCode, int, str, unicode))

    # (*) Main DFA -- try to match core patterns
    #     Post-context handling is webbed into the main state machine.
    Lng.debug_unit_name_set("%s:Core" % Mode.name)
    main, \
    main_analyzer        = generator.do_main(Mode.core_sm_list, ReloadStateForward, 
                                             dial_db)
    Lng.debug_unit_name_set("%s:Extra" % Mode.name)
    # assert all_isinstance(main, (IfDoorIdReferencedCode, int, str, unicode))
    extra                = generator.do_analyzer_list(Mode.extra_analyzer_list)

    # (*) Terminals
    #     (BEFORE 'Reload procedures' because some terminals may add entries
    #      to the reloader.)
    Lng.debug_unit_name_set("%s:Terminals" % Mode.name)

    terminals            = generator.do_terminals(list(TerminalDb.values()), 
                                                  main_analyzer, 
                                                  dial_db)

    # (*) Reload procedures
    reload_procedure_fw  = generator.do_reload_procedure(main_analyzer)
    reload_procedure_bw  = generator.do_reload_procedure(pre_analyzer)

    # assert all_isinstance(reload_procedures, (IfDoorIdReferencedCode, int, str, unicode))

    # (*) Re-entry preparation
    Lng.debug_unit_name_set("%s:Re-Entry-Preparation" % Mode.name)
    reentry_preparation  = generator.do_reentry_preparation(Mode.pre_context_sm_id_list,
                                                            OnAfterMatchCode, 
                                                            dial_db)

    # (*) State Router
    #     (Something that can goto a state address by an given integer value)
    state_router         = generator.do_state_router(dial_db)
    # assert all_isinstance(state_router, (IfDoorIdReferencedCode, int, str, unicode))

    # (*) Variable Definitions
    #     (Code that defines all required variables for the analyzer)
    variable_db.require_registers(Mode.required_register_set)
    variable_definitions = generator.do_variable_definitions()
    # assert all_isinstance(variable_definitions, (IfDoorIdReferencedCode, int, str, unicode))

    # (*) Putting it all together
    function_body = []
    function_body.extend(pre_context)         # implementation of pre-contexts (if there are some)
    function_body.extend(main)                # main pattern matcher
    function_body.extend(extra)               # extra state machines (from 'Loopers')
    function_body.extend(bipd)                # (seldom != empty; only for pseudo-ambiguous post contexts)
    function_body.extend(terminals)           
    function_body.extend(state_router)        # route to state by index (only if no computed gotos)
    function_body.extend(reload_procedure_fw)
    function_body.extend(reload_procedure_bw)
    function_body.extend(reentry_preparation)   

    return function_body, variable_definitions

def wrap_up(ModeName, FunctionBody, VariableDefs, ModeNameList, dial_db):
    txt_function = Lng.ANALYZER_FUNCTION(ModeName, Setup, VariableDefs, 
                                         FunctionBody, dial_db, ModeNameList) 
    txt_header   = Lng.HEADER_DEFINITIONS(dial_db) 
    assert isinstance(txt_header, str)

    txt_analyzer = get_plain_strings(txt_function, dial_db)
    assert all_isinstance(txt_analyzer, str)

    return [ txt_header ] + txt_analyzer

def comment_match_behavior(ModeIterable):
    """Generate comment that documents the matching behavior of the
    given mode.
    """
    if not Setup.comment_mode_patterns_f: return ""

    txt = "".join(
        mode.documentation.get_string()
        for mode in sorted(ModeIterable, key=attrgetter("name"))
    )
    return Lng.ML_COMMENT("BEGIN: MODE PATTERNS\n" + \
                          txt                      + \
                          "\nEND: MODE PATTERNS")



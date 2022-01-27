# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.files.specifier.mode                import Mode_Prep, ModeParsed
from   quex.input.setup                               import NotificationDB
import quex.engine.state_machine.check.superset       as     superset_check
import quex.engine.state_machine.algebra.is_disjoint  as     is_disjoint
import quex.engine.state_machine.check.outrun         as     outrun_checker
import quex.engine.misc.error                         as     error
from   quex.engine.misc.tools                         import typed
import quex.blackboard                                as     blackboard
from   quex.blackboard                                import setup as Setup
import quex.token_db                                  as     token_db
from   quex.constants                                 import E_IncidenceIDs

@typed(ModePrepList=[Mode_Prep])
def do(ModePrepList):
    """Consistency check of mode database

       -- Are there applicable modes?
       -- Start mode:
          -- specified (more than one applicable mode req. explicit specification)?
          -- is defined as mode?
          -- start mode is not inheritable only?
       -- Entry/Exit transitions are allows?
    """
    assert not Setup.token_class_only_f
    assert ModePrepList

    mode_name_list = sorted([m.name for m in ModePrepList]) 

    # (*) If a conversion or a codec engine is specified, then the 
    #     'on_bad_lexatom' handler must be specified in every mode.
    if Setup.buffer_encoding.bad_lexatom_possible():
        _check_on_bad_lexatom_handler_implemented(ModePrepList)

    # (*) on_n_dedent 
    for mode in ModePrepList:
        _check_token_repetition_enabled(mode, token_db)

    # (*) Entry/Exit Transitions
    for mode in ModePrepList:
        if not mode.implemented_f(): continue
        __entry_transitions(mode, ModePrepList, mode_name_list)
        __exit_transitions(mode, ModePrepList, mode_name_list)

    for mode in ModePrepList:
        # (*) [Optional] Warnings on Outrun
        if Setup.warning_on_outrun_f:
             _check_low_priority_outruns_high_priority_pattern(mode)

        # (*) Special Patterns shall not match on same lexemes
        if NotificationDB.error_on_special_pattern_same not in Setup.suppressed_notification_list:
            _check_match_same(mode, NotificationDB.error_on_special_pattern_same)

        # (*) Special Patterns (skip, indentation, etc.) 
        #     shall not be outrun by another pattern.
        if NotificationDB.error_on_special_pattern_outrun not in Setup.suppressed_notification_list:
            _check_special_incidence_outrun(mode, NotificationDB.error_on_special_pattern_outrun)

        # (*) Special Patterns shall not have common matches with patterns
        #     of higher precedence.
        if NotificationDB.error_on_special_pattern_subset not in Setup.suppressed_notification_list:
            _check_higher_priority_matches_subset(mode, NotificationDB.error_on_special_pattern_subset)

        # (*) Check for dominated patterns
        if NotificationDB.error_on_dominated_pattern not in Setup.suppressed_notification_list:
            _check_dominated_pattern(mode, NotificationDB.error_on_dominated_pattern)

def _check_special_incidence_outrun(mode, ErrorCode):
    for high, low in mode.unique_pattern_pair_iterable():
        if     high.pattern_string() not in Mode_Prep.focus \
           and low.pattern_string()  not in Mode_Prep.focus: 
            continue
        
        elif not outrun_checker.do(high.sm, low.sm):                  
            continue

        error.log_consistency_issue(high, low, ExitF=False, 
                        ThisComment  = "has higher precedence but",
                        ThatComment  = "may outrun it",
                        SuppressCode = ErrorCode)
                             
def _check_higher_priority_matches_subset(mode, ErrorCode):
    """Checks whether a higher prioritized pattern matches a common subset
       of the ReferenceSM. For special patterns of skipper, etc. this would
       be highly confusing.
    """
    global special_pattern_list
    for high, low in mode.unique_pattern_pair_iterable():
        if     high.pattern_string() not in Mode_Prep.focus \
           and low.pattern_string() not in Mode_Prep.focus: continue

        if not superset_check.do(high.sm, low.sm):             
            continue

        error.log_consistency_issue(high, low, ExitF=True, 
                        ThisComment  = "has higher precedence and",
                        ThatComment  = "matches a subset of",
                        SuppressCode = ErrorCode)

def _check_dominated_pattern(mode, ErrorCode):
    for high, low in mode.unique_pattern_pair_iterable():
        # 'low' comes after 'high' => 'i' has precedence
        # Check for domination.
        if superset_check.do(high, low):
            error.log_consistency_issue(high, low, 
                            ThisComment  = "matches a superset of what is matched by",
                            EndComment   = "The former has precedence and the latter can never match.",
                            ExitF        = True, 
                            SuppressCode = ErrorCode)

def _check_match_same(mode, ErrorCode):
    """Special patterns shall never match on some common lexemes."""
    for high, low in mode.unique_pattern_pair_iterable():
        if     high.pattern_string() not in Mode_Prep.focus \
           and low.pattern_string() not in Mode_Prep.focus: continue

        # A superset of B, or B superset of A => there are common matches.
        if is_disjoint.do(high.sm, low.sm): continue

        # The 'match what remains' is exempted from check.
        if high.pattern_string() == "." or low.pattern_string() == ".":
            continue

        error.log_consistency_issue(high, low, 
                        ThisComment  = "matches on some common lexemes as",
                        ThatComment  = "",
                        ExitF        = True,
                        SuppressCode = ErrorCode)

def _check_low_priority_outruns_high_priority_pattern(mode):
    """Warn when low priority patterns may outrun high priority patterns.
    Assume that the pattern list is sorted by priority!
    """
    for high, low in mode.unique_pattern_pair_iterable():
        if outrun_checker.do(high.sm, low.sm):
            error.log_consistency_issue(low, high, ExitF=False, ThisComment="may outrun")

def initial_mode(ModePrepList, initial_mode):
    # (*) Start mode specified?
    mode_name_list, \
    implemented_mode_name_list = _get_mode_name_lists(ModePrepList)

    """If more then one mode is defined, then that requires an explicit 
       definition 'start = mode'.
    """
    assert implemented_mode_name_list
    assert blackboard.initial_mode is not None

    mode = initial_mode.get_text()

    # Start mode present and applicable?
    error.verify_word_in_list(mode, mode_name_list,
                        "Start mode '%s' is not defined." % mode,
                        blackboard.initial_mode.sr)
    error.verify_word_in_list(mode, implemented_mode_name_list,
                        "Start mode '%s' is inheritable only and cannot be instantiated." % mode,
                        initial_mode.sr)

def __access_mode(Mode, ModePrepList, OtherModeName, ModeNameList, EntryF):
    type_str = { True: "entry from", False: "exit to" }[EntryF]

    error.verify_word_in_list(OtherModeName, ModeNameList,
              "Mode '%s' permits the %s mode '%s'\nbut no such mode exists." % \
              (Mode.name, type_str, OtherModeName), Mode.sr)

    for mode in ModePrepList:
        if mode.name == OtherModeName: return mode
    # OtherModeName MUST be in ModePrepList, at this point in time.
    assert False

def __error_transition(Mode, OtherMode, EntryF):
    type_str  = { True: "entry",      False: "exit" }[EntryF]
    type0_str = { True: "entry from", False: "exit to" }[EntryF]
    type1_str = { True: "exit to",    False: "entry from" }[EntryF]

    error.log("Mode '%s' permits the %s mode '%s' but mode '%s' does not" % (Mode.name, type0_str, OtherMode.name, OtherMode.name),
              Mode.sr, DontExitF=True)
    error.log("permit the %s mode '%s' or any of its base modes." % (type1_str, Mode.name),
              OtherMode.sr, DontExitF=True)
    error.log("May be, use explicitly mode tag '<%s: ...>' for restriction." % type_str, 
              Mode.sr)

def __exit_transitions(mode, ModePrepList, mode_name_list):
    for exit_mode_name in mode.exit_mode_name_list:
        exit_mode = __access_mode(mode, ModePrepList, exit_mode_name, mode_name_list, EntryF=False)

        # Check if this mode or one of the base modes can enter
        for base_mode in mode.base_mode_sequence:
            if base_mode.name in exit_mode.entry_mode_name_list: break
        else:
            __error_transition(mode, exit_mode, EntryF=False)

def __entry_transitions(mode, ModePrepList, mode_name_list):
    for entry_mode_name in mode.entry_mode_name_list:
        entry_mode = __access_mode(mode, ModePrepList, entry_mode_name, mode_name_list, EntryF=True)

        # Check if this mode or one of the base modes can be reached
        for base_mode in mode.base_mode_sequence:
            if base_mode.name in entry_mode.exit_mode_name_list: break
        else:
            __error_transition(mode, entry_mode, EntryF=True)
           
def _check_on_bad_lexatom_handler_implemented(ModePrepList):
    bad_mode_name_list = [ 
        mode.name for mode in ModePrepList
        if E_IncidenceIDs.BAD_LEXATOM not in mode.incidence_db
    ]
    if not bad_mode_name_list: 
        return 

    lexatom_range = Setup.lexatom.type_range
    modes_str     = ", ".join(name for name in bad_mode_name_list)
    mode          = ModePrepList[0]
    error.warning("Missing 'on_bad_lexatom' handler in mode(s) %s.\n" \
                  % modes_str + \
                  "The range of values in buffer elements is [%i:%i].\n" \
                  % (lexatom_range.begin, lexatom_range.end-1) + \
                  "Not all of those contain representations in the buffer's encoding '%s'." % Setup.buffer_encoding.name,
                  mode.sr, 
                  SuppressCode=NotificationDB.warning_codec_error_with_non_unicode)

def _check_token_repetition_enabled(mode, token_db):
    if mode.loopers.indentation_handler:
        if not token_db.support_repetition():
            error.warning("Option 'indentation' defined token repetition is not supported.\n" \
                          "May be: * Define 'token { DEDENT \\repeatable; }'.\n"
                          "        * And, if token type is customized, define 'repetition_n = member-name'.", 
                          mode.sr)
        elif "DEDENT" not in token_db.token_repetition_token_id_list:   
            error.warning("Option 'indentation' defined, but 'DEDENT' is not marked as repeatable.\n" \
                          "Define 'token { DEDENT \\repeatable; }'.\n",
                          mode.sr)

def _get_mode_name_lists(ModePrepList):
    mode_name_list             = sorted([mode.name for mode in ModePrepList]) 
    # Applicable modes can only be determined after possible addition of "inheritable: only"
    implemented_mode_name_list = sorted([mode.name for mode in ModePrepList 
                                         if mode.option_db.value("inheritable") != "only"]) 

    return mode_name_list, implemented_mode_name_list

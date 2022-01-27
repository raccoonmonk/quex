# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.files.specifier.ppt_list               import PPTList_Builder
from   quex.input.regular_expression.pattern             import Pattern_Prep
from   quex.input.files.mode_option                      import OptionDB
from   quex.input.code.core                              import CodeUser
from   quex.input.code.base                              import SourceRef
from   quex.engine.analyzer.door_id_address_label        import DialDB
import quex.engine.analyzer.engine_supply_factory        as     engine
from   quex.engine.analyzer.state.core                   import ReloadState
from   quex.engine.incidence_db                          import IncidenceDB
from   quex.engine.pattern                               import Pattern           
from   quex.engine.counter                               import CountActionMap
from   quex.engine.mode                                  import Mode           
import quex.engine.misc.error                            as     error
from   quex.engine.misc.tools                            import typed, flatten

import quex.blackboard as     blackboard

from   collections import namedtuple
from   itertools   import islice

class Mode_Builder:
    def __init__(self, parsed_mode):
        self.dial_db = DialDB()
        self.reload_state_forward = ReloadState(EngineType=engine.FORWARD, dial_db=self.dial_db)

        self.parsed_mode = parsed_mode
        self.__product_Mode_Prep = None

    @property
    def name(self):
        return self.parsed_mode.name

    @property
    def sr(self):
        return self.parsed_mode.sr

    def get_Mode_Prep(self):
        assert self.__product_Mode_Prep
        return self.__product_Mode_Prep

    def get_Mode(self):
        assert self.__product_Mode
        return self.__product_Mode

    def collect_base_mode_information(self, BaseModeSequence, DerivedModeNameDb):
        """REQUIRES: All ModeParsed-s have been defined.
           TASK:     Collect loopers, options, and incidence_db from base
                     mode list.
                     Finalize all patterns and loopers!
        """
        assert BaseModeSequence
        assert BaseModeSequence[-1].name == self.name

        # IncidenceDb
        #
        incidence_db = IncidenceDB.from_BaseModeSequence(BaseModeSequence)

        # Extract information from OptionDb 
        #
        option_db = OptionDB.from_BaseModeSequence(BaseModeSequence)

        # Finalize patterns (requires ca_map)
        #
        ca_map = option_db.value("counter")
        pap_list = [
            PatternActionPair(pap.pattern().finalize(ca_map), pap.action())
            for pap in self.parsed_mode.pattern_action_pair_list
        ]

        # At this stage, no information is aggregated from base types.
        self.__product_Mode_Prep = Mode_Prep(self.parsed_mode.name, self.sr, 
                                             [m.name for m in BaseModeSequence], DerivedModeNameDb,
                                             pap_list, incidence_db, option_db,
                                             self.parsed_mode.deletion_info_list, 
                                             self.parsed_mode.reprioritization_info_list)

    def collect_and_prioritize_patterns(self, mode_prep_db):
        # (*) Mode_Prep: pre finalize
        #     All patterns of all modes have been finalized
        #     => collect all patterns and loopers from base modes 
        #     => generate pattern list / terminal configuration
        mp = self.__product_Mode_Prep
        mp.base_mode_sequence = [ 
            mode_prep_db[name] for name in mp.base_mode_name_sequence 
        ]
        mp.pattern_list,                  \
        self.terminal_db,                   \
        self.extra_analyzer_list,         \
        run_time_counter_required_f,      \
        self.required_register_set,       \
        self.doc_history_deletion,        \
        self.doc_history_reprioritization = PPTList_Builder.do(mp, self.dial_db, self.reload_state_forward)

        if not run_time_counter_required_f:
            self.ca_map_for_run_time_counter = None
        else:
            self.ca_map_for_run_time_counter = mp.ca_map

    def finalize_documentation(self, ModePrepDb):
        def filter_implemented(L):
            return [m for m in L if ModePrepDb[m].implemented_f()]

        mp = self.__product_Mode_Prep
        self.doc = ModeDocumentation(mp.pattern_list, 
                                     self.doc_history_deletion,
                                     self.doc_history_reprioritization,
                                     filter_implemented(mp.entry_mode_name_list),
                                     filter_implemented(mp.exit_mode_name_list),
                                     filter_implemented(mp.base_mode_name_sequence))

    def finalize(self):
        """REQUIRES: Patterns from base modes have been collected.
        """
        mp = self.__product_Mode_Prep
        assert mp.implemented_f()

        self.__product_Mode = Mode(mp.name, mp.sr, mp.pattern_list, 
                    self.terminal_db, self.extra_analyzer_list, mp.incidence_db,
                    CaMap4RunTimeCounter = self.ca_map_for_run_time_counter,
                    ReloadStateForward   = self.reload_state_forward,
                    RequiredRegisterSet  = self.required_register_set,
                    Documentation        = self.doc, 
                    dial_db              = self.dial_db,
                    IndentationHandlingF = mp.loopers.indentation_handler is not None)


class Loopers:
    """Loopers -- loops that are integrated into the pattern state machine.
    """
    #@typed(Skip               = (None, [Pattern_Prep]), 
    #       SkipRange          = (None, [dict]),
    #       SkipNestedRange    = (None, [dict]),
    #       IndentationHandler = (None, IndentationCount))
    def __init__(self, Skip, SkipRange, SkipNestedRange, IndentationHandler):
        self.skip                = Skip
        self.skip_range          = SkipRange
        self.skip_nested_range   = SkipNestedRange
        self.indentation_handler = IndentationHandler

    def combined_skip(self, CaMap):
        """Character Set Skipper: Multiple skippers from different modes are 
        combined into one pattern.

        RETURNS: [0] Total set of skipped characters
                 [1] Pattern string for total set of skipped characters
                 [2] Auxiliary source reference.

        Not all source references can be maintained (only one). It must be 
        assumed that the necessary checks to report errors have been done at
        this point in time. The given source reference is 'auxiliary' to 
        be able to point at least to some position.
        """
        iterable           = iter(self.skip)
        pattern, total_set = next(iterable)
        pattern_str        = pattern.pattern_string()
        source_reference   = pattern.sr
        for ipattern, icharacter_set in iterable:
            total_set.unite_with(icharacter_set)
            pattern_str += "|" + ipattern.pattern_string()

        return total_set, pattern_str, source_reference

class ModeDocumentation:
    def __init__(self, PatternList, HistDel, HistRepr, EntryMnl, ExitMnl, BMNS):
        self.history_deletion         = HistDel 
        self.history_reprioritization = HistRepr
        self.entry_mode_name_list     = EntryMnl
        self.exit_mode_name_list      = ExitMnl
        self.base_mode_name_sequence  = BMNS
        self.pattern_info_list = [
            (p.incidence_id, p.sr.mode_name, p.pattern_string())
            for p in PatternList]

    def get_string(self):
        ModeName = self.base_mode_name_sequence[-1]
        L = max(len(name) for name in self.base_mode_name_sequence)
        txt  = ["\nMODE: %s\n\n" % ModeName]

        base_mode_name_list = self.base_mode_name_sequence[:-1] 
        if base_mode_name_list:
            base_mode_name_list.reverse()
            txt.append("    BASE MODE SEQUENCE:\n")
            txt.extend("      %s\n" % name 
                       for name in base_mode_name_list)
            txt.append("\n")

        if self.history_deletion:
            txt.append("    DELETION ACTIONS:\n")
            txt.extend("      %s:  %s%s  (from mode %s)\n" % \
                (entry[0], " " * (L - len(ModeName)), entry[1], entry[2])
                for entry in self.history_deletion
            )
            txt.append("\n")

        if self.history_reprioritization:
            txt.append("    DEMOTION ACTIONS:\n")
            self.history_reprioritization.sort(key=lambda x: x[4])
            txt.extend("      %s: %s%s  (from mode %s)  (%i) --> (%i)\n" % \
                (entry[0], " " * (L - len(ModeName)), entry[1], entry[2], entry[3], entry[4])
                for entry in self.history_reprioritization
            )
            txt.append("\n")

        if self.pattern_info_list:
            txt.append("    PATTERN LIST:\n")
            txt.extend("      (%3i) %s: %s%s\n" % \
                (iid, mode_name, " " * (L - len(mode_name)), pattern_string)
                for iid, mode_name, pattern_string in self.pattern_info_list
            )
            txt.append("\n")

        return "".join(txt)

#-----------------------------------------------------------------------------------------
# ModeParsed/Mode Objects:
#
# During parsing 'ModeParsed' objects are generated. Once parsing is over, 
# the descriptions are translated into 'real' mode objects where code can be generated
# from. All matters of inheritance and pattern resolution are handled in the
# transition from description to real mode.
#-----------------------------------------------------------------------------------------
class ModeParsed:
    """Mode description delivered directly from the parser.
    ______________________________________________________________________________
    MAIN MEMBERS:

     (1) .pattern_action_pair_list:   [ (Pattern, CodeUser) ]

     Lists all patterns which are directly defined in this mode (not the ones
     from the base mode) together with the user code (class CodeUser) to be
     executed upon the detected match.

     (2) .incidence_db:               incidence_id --> [ CodeFragment ]

     Lists of possible incidences (e.g. 'on_match', 'on_enter', ...) together
     with the code fragment to be executed upon occurence.

     (3) .option_db:                  option name  --> [ OptionSetting ]

     Maps the name of a mode option to a list of OptionSetting according to 
     what has been defined in the mode. Those options describe

        -- [optional] The character counter behavior.
        -- [optional] The indentation handler behavior.
        -- [optional] The 'skip' character behavior.
           ...

     That is, they parameterize code generators of 'helpers'. The option_db
     also contains information about mode transition restriction, inheritance
     behavior, etc.

     (*) .direct_base_mode_name_list:   [ string ]
     
     Lists all modes from where this mode is derived, that is only the direct 
     super modes.
    ______________________________________________________________________________
    OTHER NON_TRIVIAL MEMBERS:

     If the mode is derived from another mode, it may make sense to adapt the 
     priority of patterns and/or delete pattern from the matching hierarchy.

     (*) .reprioritization_info_list: [ PatternRepriorization ] 
       
     (*) .deletion_info_list:         [ PatternDeletion ] 
    ______________________________________________________________________________
    """
    __slots__ = ("name",
                 "sr",
                 "direct_base_mode_name_list",
                 "option_db",
                 "pattern_action_pair_list",
                 "incidence_db",
                 "reprioritization_info_list",
                 "deletion_info_list")

    def __init__(self, Name, SourceReference):
        # Register ModeParsed at the mode database
        self.name  = Name
        self.sr    = SourceReference

        self.direct_base_mode_name_list = []

        self.pattern_action_pair_list   = []  
        self.option_db                  = OptionDB()    # map: option_name    --> OptionSetting
        self.incidence_db               = IncidenceDB() # map: incidence_name --> CodeFragment

        self.reprioritization_info_list = []  
        self.deletion_info_list         = [] 

    @typed(ThePattern=Pattern_Prep, Action=CodeUser)
    def add_pattern_action_pair(self, ThePattern, TheAction, fh):
        ThePattern.assert_consistency()

        if ThePattern.pre_context_trivial_begin_of_line_f:
            blackboard.required_support_begin_of_line_set()

        self.pattern_action_pair_list.append(PatternActionPair(ThePattern, TheAction))

    def add_match_priority(self, ThePattern, fh):
        """Whenever a pattern in the mode occurs, which is identical to that given
           by 'ThePattern', then the priority is adapted to the pattern index given
           by the current pattern index.
        """
        PatternIdx = ThePattern.incidence_id() 
        self.reprioritization_info_list.append(
            PatternRepriorization(ThePattern.finalize(None), PatternIdx, 
                                  SourceRef.from_FileHandle(fh, self.name))
        )

    def add_match_deletion(self, ThePattern, fh):
        """If one of the base modes contains a pattern which is identical to this
           pattern, it has to be deleted.
        """
        PatternIdx = ThePattern.incidence_id() 
        self.deletion_info_list.append(
            PatternDeletion(ThePattern.finalize(None), PatternIdx, 
                            SourceRef.from_FileHandle(fh, self.name))
        )

class Mode_Prep:
    focus = ("<skip>", "<skip_range opener>", "<skip_nested_range opener>", "<indentation newline>")

    @typed(AbstractF=bool)
    def __init__(self, Name, Sr, BaseModeNameSequence, DerivedModeNameDb,
                 PapList, incidence_db, option_db,
                 DeletionInfoList, RepriorizationInfoList):
        """REQUIRES: Loopers, options, and incidence_db has been collected 
                     from base modes.
           TASK:     Provide bases for iteration over modes to collect 
                     finalized pattern lists from base modes.
        """
        self.name                    = Name
        self.sr                      = Sr
        self.base_mode_name_sequence = BaseModeNameSequence
        self.incidence_db            = incidence_db

        # PapList = list with 'finalized' Pattern objects
        # BUT: Only local patterns!
        #      Patterns from base modes are collected later in 
        #      'ppt_list.collect_match_pattern()'.
        self.pattern_action_pair_list = PapList

        self.deletion_info_list         = DeletionInfoList
        self.reprioritization_info_list = RepriorizationInfoList

        self.abstract_f  = (option_db.value("inheritable") == "only")

        # Loopers = Containing all 'looping' objects for skipping and 
        #           indentation handling. (patterns are finalized)
        self.loopers = Loopers(option_db.value_list("skip"), 
                          option_db.value_list("skip_range"),
                          option_db.value_list("skip_nested_range"),
                          option_db.value("indentation"))

        # CaMap: Counting information for lines and columns
        #
        self.ca_map  = option_db.value("counter")
        assert isinstance(self.ca_map, CountActionMap)

        # Entry/Exit restrictions
        #
        # Entry from base includes entry permission from derived.
        self.exit_mode_name_list  = option_db.value_list("exit")
        entry_mode_name_list = list(option_db.value_list("entry"))
        entry_mode_name_list.extend(flatten(
            DerivedModeNameDb[mode_name] for mode_name in option_db.value_list("entry")
            if mode_name in DerivedModeNameDb))
        self.entry_mode_name_list = list(set(entry_mode_name_list))

    def implemented_f(self):
        """If the mode has incidences and/or patterns defined it is free to be 
        abstract or not. If neither one is defined, it cannot be implemented and 
        therefore MUST be abstract.
        """
        if self.abstract_f:         return False
        elif not self.pattern_list: return False
        else:                       return True

    def unique_pattern_pair_iterable(self):
        """Iterates over pairs of patterns:

            (high precedence pattern, low precedence pattern)

           where 'pattern_i' as precedence over 'pattern_k'
        """
        for i, high in enumerate(self.pattern_list):
            for low in islice(self.pattern_list, i+1, None):
                yield high, low

PatternRepriorization = namedtuple("PatternRepriorization", ("pattern", "new_pattern_index", "sr"))
PatternDeletion       = namedtuple("PatternDeletion",       ("pattern", "pattern_index",     "sr"))

class PatternActionPair(object):
    __slots__ = ("__pattern", "__action")
    @typed(ThePattern=(Pattern_Prep, Pattern), TheAction=CodeUser)
    def __init__(self, ThePattern, TheAction):
        self.__pattern = ThePattern
        self.__action  = TheAction

    @property
    def line_n(self):    return self.action().sr.line_n
    @property
    def file_name(self): return self.action().sr.file_name

    def pattern(self):   return self.__pattern

    def action(self):    return self.__action

    def __repr__(self):         
        txt  = ""
        if self.pattern().incidence_id not in blackboard.E_IncidenceIDs:
            txt += "self.pattern_string = %s\n" % repr(self.pattern().pattern_string())
        txt += "self.pattern        = %s\n" % repr(self.pattern()).replace("\n", "\n      ")
        txt += "self.action         = %s\n" % self.action().get_text()
        if hasattr(self.action(), "sr"):
            txt += "self.file_name  = %s\n" % repr(self.action().sr.file_name) 
            txt += "self.line_n     = %s\n" % repr(self.action().sr.line_n) 
        txt += "self.incidence_id = %s\n" % repr(self.pattern().incidence_id) 
        return txt


# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PPT List: A list of tuples that associate:

     (i)   the PRIORITY of a pattern in the match process.
     (ii)  the PATTERN, and
     (iii) a   TERMINAL to be executed upon match.

The complete matching process of the analyzer in forward direction is described
in this file by a list off PPT objects. This includes PPT entries for skippers
and incidence handlers. Based on the PPT list optional pattern deletion and
repriorization is implemented. Finaly, a mode's pattern list and terminal
database is extracted.
"""
from   quex.input.regular_expression.pattern        import Pattern_Prep
from   quex.engine.counter                          import CountActionMap
from   quex.engine.misc.tools                       import do_and_delete_if
from   quex.engine.pattern                          import Pattern
from   quex.engine.state_machine.character_counter  import SmLineColumnCountInfo
import quex.engine.state_machine.check.tail         as     tail
import quex.engine.state_machine.check.superset     as     superset_check
import quex.engine.state_machine.check.identity     as     identity_checker
from   quex.engine.operations.operation_list        import Op
from   quex.engine.analyzer.terminal.factory        import TerminalFactory
from   quex.engine.analyzer.terminal.core           import Terminal, \
                                                           TerminalGotoDoorId
from   quex.engine.analyzer.door_id_address_label   import DoorID
import quex.engine.analyzer.door_id_address_label   as     dial
import quex.engine.misc.error_check                 as     error_check
from   quex.engine.misc.tools                       import typed
import quex.engine.misc.error                       as     error
from   quex.engine.misc.quex_enum                   import QuexEnum
import quex.engine.loop.skip_character_set          as     skip_character_set
import quex.engine.loop.skip_nested_range           as     skip_nested_range
import quex.engine.loop.indentation_counter         as     indentation_counter

from   quex.constants  import E_IncidenceIDs, E_R


from   collections  import namedtuple
from   operator     import attrgetter

from   quex.blackboard import setup as Setup, \
                              standard_incidence_db_get_terminal_type, \
                              E_IncidenceIDs

class PatternPriority(object):
    """Description of a pattern's priority.
    ___________________________________________________________________________
    PatternPriority-s are possibly adapted according the re-priorization 
    or other 'mode-related' mechanics. Thus, they cannot be named tuples.
    ___________________________________________________________________________
    """
    __slots__ = ("mode_hierarchy_index", "pattern_index")
    def __init__(self, MHI, PatternIdx):
        self.mode_hierarchy_index = MHI
        self.pattern_index        = PatternIdx

    def __cmp__(self, Other):
        if   self.mode_hierarchy_index > Other.mode_hierarchy_index: return 1
        elif self.mode_hierarchy_index < Other.mode_hierarchy_index: return -1
        elif self.pattern_index > Other.pattern_index:               return 1
        elif self.pattern_index < Other.pattern_index:               return -1
        else:                                                        return 0

    def __lt__(self, Other):
        return self.__cmp__(Other) == -1

    def __gt__(self, Other):
        return self.__cmp__(Other) == 1

    def __eq__(self, Other):
        return self.__cmp__(Other) == 0

    def __repr__(self):
        return "{ mhi: %s; pattern_i: %s; }" % (self.mode_hierarchy_index, self.pattern_index)

class PPT(namedtuple("PPT_tuple", ("priority", "pattern", "terminal"))):
    """PPT -- (Priority, Pattern, Terminal) 
    ______________________________________________________________________________

    Collects information about a pattern, its priority, and the terminal 
    to be executed when it triggers. Objects of this class are intermediate
    they are not visible outside class 'Mode'.
    ______________________________________________________________________________
    """
    @typed(ThePatternPriority=PatternPriority, ThePattern=Pattern, TheTerminal=(Terminal, None))
    def __new__(self, ThePatternPriority, ThePattern, TheTerminal):
        return super(PPT, self).__new__(self, ThePatternPriority, ThePattern, TheTerminal)

    def __repr__(self):
        return "{ priority: %s; pattern: %s; terminal_iid: %s; }" \
                % (self.priority, self.pattern.pattern_string(), self.terminal.incidence_id)

class PPTList_Builder(list):
    def __init__(self, terminal_factory):
        self.extra_terminal_list = [] 
        self.extra_analyzer_list = [] 
        self.terminal_factory      = terminal_factory
        self.required_register_set = set()

    @staticmethod
    def do(mp, dial_db, reload_state_forward):
        """Collect all pattern-action pairs and 'loopers' and align it in a list
        of 'priority-pattern-terminal' objects, i.e. a 'ppt_list'. That list associates
        each pattern with a priority and a terminal containing an action to be executed
        upon match. 

        RETURNS: [0] List of all patterns to be matched, each pattern has a unique
                     'incidence_id'
                 [1] TerminalDb: incidence_id--> Terminal object
                 [2] Flag indicating if run-time character counting is required.
                 [3] ReloadState in forward direction.

        It is necessary to generate the reload state in forward direction, because, the
        loopers implement state machines which are subject to reload. The same reload 
        state later used by the general matching state machine.
        """
        # PPT from pattern-action pairs
        #
        terminal_factory = TerminalFactory(mp.name, mp.incidence_db, dial_db, 
                                           IndentationHandlingF=mp.loopers.indentation_handler is not None)

        builder = PPTList_Builder(terminal_factory)
        builder.collect_match_pattern(mp.base_mode_sequence)
        builder.collect_loopers(mp.loopers, mp.ca_map, reload_state_forward) 
        builder.delete_and_reprioritize(mp.base_mode_sequence)
        builder.finalize(mp)

        return builder.pattern_list, \
               builder.terminal_db, \
               builder.extra_analyzer_list, \
               builder.run_time_counter_required_f, \
               builder.required_register_set, \
               builder.history_deletion, \
               builder.history_reprioritization

    def finalize(self, mp):
        self.finalize_pattern_list()
        self.finalize_terminal_db(mp.incidence_db)
        self.finalize_run_time_counter_required_f()

    def collect_match_pattern(self, BaseModeSequence):
        """Collect patterns of all inherited modes. Patterns are like virtual functions
        in C++ or other object oriented programming languages. Also, the patterns of the
        uppest mode has the highest priority, i.e. comes first.

        'pap' = pattern action pair.
        """
        def pap_iterator(BaseModeSequence):
            assert len(BaseModeSequence) == len(set(m.name for m in BaseModeSequence)), \
                   "Base mode sequences MUST mention each mode only once."
            for mode_hierarchy_index, mode_prep in enumerate(BaseModeSequence):
                for pap in mode_prep.pattern_action_pair_list:
                    yield mode_hierarchy_index, pap.pattern(), pap.action()

        self.extend(
            PPT(PatternPriority(mhi, pattern.incidence_id), 
                pattern, 
                self.terminal_factory.do_match_pattern(code, pattern))
            for mhi, pattern, code in pap_iterator(BaseModeSequence)
        )

    @typed(CaMap=CountActionMap)
    def collect_loopers(self, Loopers, CaMap, ReloadState):
        """Collect patterns and terminals which are required to implement
        skippers and indentation counters.
        """
        new_ppt_list = []
        self.indentation_handler_door_id    = None
        self.indentation_handler_newline_sm = None
        for i, func in enumerate([self._prepare_indentation_counter,
                                  self._prepare_skip_character_set, 
                                  self._prepare_skip_range,         
                                  self._prepare_skip_nested_range]):
            # Mode hierarchie index = before all: -4 to -1
            # => skippers and indentation handlers have precendence over all others.
            mode_hierarchy_index = -4 + i
            pl, al, tl = func(mode_hierarchy_index, Loopers, CaMap, ReloadState)

            new_ppt_list.extend(pl)
            self.extra_terminal_list.extend(tl)
            self.extra_analyzer_list.extend(al)

        # IMPORTANT: Incidence Ids of Looper terminals CANNOT CHANGE!
        #            They are already 'gotoed'!
        #            They cannot be subject to reprioritization!
        #            Mode Hierarchy Index < 0!
        assert all(priority.mode_hierarchy_index < 0 for priority, x, x in new_ppt_list)
        self._assert_incidence_id_consistency(
            [p.incidence_id for dummy, p, t in new_ppt_list]
        )
        self[:0] = new_ppt_list

    def delete_and_reprioritize(self, BaseModeSequence):
        """Performs the deletion and repriorization according the DELETE and DEMOTION
        commands in the mode. This may change the order and the incidence ids of the 
        mode's patterns. Thus, the ppt_list needs to be resorted and new incidence_id-s
        need to be assigned.

        RETURNS: [0] history of deletions
                 [1] history of reprioritizations
        """
        #________________
        assert all(p.incidence_id == t.incidence_id() for dummy, p, t in self)
        self._assert_incidence_id_consistency([p.incidence_id for dummy, p, t in self])
        #________________

        self.history_deletion = []
        self.history_reprioritization = []
        if not self: return 

        # Delete and reprioritize
        self.history_deletion         = self._pattern_deletion(BaseModeSequence) 
        self.history_reprioritization = self._pattern_reprioritization(BaseModeSequence) 

        self._adapt_pattern_id_to_priority(self)

        #________________
        assert all(p.incidence_id == t.incidence_id() for dummy, p, t in self)
        self._assert_incidence_id_consistency([p.incidence_id for dummy, p, t in self])
        #________________

    @staticmethod
    def _adapt_pattern_id_to_priority(ppt_list):
        """Ensure that the incidence-id of each pattern fits the position in 
        priorization sequence. That is, early entries in the list MUST have 
        lower incidence id than later entries.

        NOTE: For MHI-s < 0, i.e. loopers, this functions basically asserts
              that the incidence ids of all patterns are aligned with their 
              position in the list.
        """
        if len(ppt_list) < 1: return

        ppt_list.sort(key=attrgetter("priority"))
        prev_incidence_id = ppt_list[0].pattern.incidence_id 
        for i, ppt in enumerate(ppt_list[1:], start=1): 
            priority, pattern, terminal = ppt

            # NOT: Mode Hierarchy Index < 0 == 'Entry into Looper'
            #      Those patterns are NOT SUPPOSED to match common lexemes
            #      with each other or other lexemes in the mode!
            # => They are not subject to repriorization!
            if priority.mode_hierarchy_index < 0: 
                continue
            elif QuexEnum.general_cmp(pattern.incidence_id, prev_incidence_id) == 1:
                prev_incidence_id = pattern.incidence_id
                continue

            # Generate a new, cloned pattern. So that other related modes are not effected.
            new_incidence_id = dial.new_incidence_id() # new id > any older id.
            new_pattern      = pattern.clone_with_new_incidence_id(new_incidence_id)
            if terminal is not None: new_terminal = terminal.clone(new_incidence_id)
            else:                    new_terminal = None
            new_ppt = PPT(priority, new_pattern, new_terminal)
            ppt_list[i] = new_ppt

            prev_incidence_id = new_incidence_id

    def _pattern_reprioritization(self, BaseModeSequence):
        """Repriority patterns. The 'reprioritization_info_list' consists of a list of

                     (pattern, new_pattern_index, source_reference)

           If a pattern defined in this mode matches 'pattern' it needs to receive the
           new pattern index and there changes its preceedence.
        """
        def repriorize(MHI, Info, self, ModeName, history):
            done_f = False
            for ppt in self:
                priority, pattern, terminal = ppt
                if   priority.mode_hierarchy_index > MHI:                      continue
                elif priority.pattern_index        >= Info.new_pattern_index:  continue
                elif not identity_checker.do(pattern, Info.pattern):           continue

                done_f = True
                history.append([ModeName, 
                                pattern.pattern_string(), pattern.sr.mode_name,
                                pattern.incidence_id, Info.new_pattern_index])
                priority.mode_hierarchy_index = MHI
                priority.pattern_index        = Info.new_pattern_index

            if not done_f and Info.sr.mode_name == ModeName:
                error.warning("PRIORITY mark does not have any effect.", 
                              Info.sr)

        history = []
        mode_name = BaseModeSequence[-1].name
        for mode_hierarchy_index, mode in enumerate(BaseModeSequence):
            for info in mode.reprioritization_info_list:
                repriorize(mode_hierarchy_index, info, self, mode_name, history)

        return history

    def _pattern_deletion(self, BaseModeSequence):
        """Delete all patterns that match entries in 'deletion_info_list'.
        """
        def delete(MHI, Info, self, ModeName, history):
            def do(element, history):
                priority, pattern, terminal = element
                if   priority.mode_hierarchy_index > MHI:          return False
                elif priority.pattern_index >= Info.pattern_index: return False
                elif not superset_check.do(Info.pattern, pattern): return False
                history.append([ModeName, pattern.pattern_string(), pattern.sr.mode_name])
                return True

            size = len(self)
            do_and_delete_if(self, do, history)

            if size == len(self) and Info.sr.mode_name == ModeName:
                error.warning("DELETION mark does not have any effect.", Info.sr)

        history = []
        mode_name = BaseModeSequence[-1].name
        for mode_hierarchy_index, mode_prep in enumerate(BaseModeSequence):
            for info in mode_prep.deletion_info_list:
                delete(mode_hierarchy_index, info, self, mode_name, history)

        return history

    def finalize_pattern_list(self): 
        self.pattern_list = [ p for prio, p, t in self ]
        self._assert_incidence_id_consistency([p.incidence_id for p in self.pattern_list])

    def finalize_terminal_db(self, IncidenceDb):
        """This function MUST be called after 'finalize_pattern_list()'!
        """
        def extract_terminal_db(event_db, factory, ReloadRequiredF):
            result = {}
            for incidence_id, code_fragment in event_db.items():
                terminal_type = standard_incidence_db_get_terminal_type(incidence_id)
                if terminal_type is None:
                    continue
                elif     incidence_id == E_IncidenceIDs.END_OF_STREAM \
                     and not ReloadRequiredF:
                    continue
                assert terminal_type not in result
                terminal = factory.do(terminal_type, code_fragment)
                terminal.set_incidence_id(incidence_id)
                result[incidence_id] = terminal

            return result

        terminal_list = [
            terminal for priority, pattern, terminal in self
                     if terminal is not None
        ]

        # Some incidences have their own terminal
        # THEIR INCIDENCE ID REMAINS FIXED!
        terminal_list.extend(
            iter(extract_terminal_db(IncidenceDb, 
                                     self.terminal_factory, 
                                     ReloadRequiredF=True).values())
        )

        terminal_list.extend(self.extra_terminal_list)

        self._assert_incidence_id_consistency(
            [t.incidence_id() for t in terminal_list]
        )

        self.terminal_db = dict((t.incidence_id(), t) for t in terminal_list)

    @staticmethod
    def _assert_incidence_id_consistency(IncidenceIdList):
        """Basic constraints on incidence ids.
        """
        # (i) Incidence Ids are either integers or 'E_IncidenceIDs'
        assert all((   isinstance(incidence_id, int) 
                    or incidence_id in E_IncidenceIDs)
                   for incidence_id in IncidenceIdList)
        # (ii) Every incidence id appears only once.
        assert len(set(IncidenceIdList)) == len(IncidenceIdList)

    def finalize_run_time_counter_required_f(self):
        if self.terminal_factory.run_time_counter_required_f:
            self.run_time_counter_required_f = True
        else:
            self.run_time_counter_required_f = any(p.lcci.run_time_counter_required_f 
                                                   for prio, p, t in self if p.lcci is not None)

    def _prepare_indentation_counter(self, MHI, Loopers, CaMap, ReloadState):
        """Prepare indentation counter. An indentation counter is implemented by 
        the following:

        'newline' pattern --> triggers as soon as an UNSUPPRESSED newline occurs. 
                          --> entry to the INDENTATION COUNTER.

        'suppressed newline' --> INDENTATION COUNTER is NOT triggered.
         
        The supressed newline pattern is longer (and has precedence) over the
        newline pattern. With the suppressed newline it is possible to write
        lines which overstep the newline (see backslahs in Python, for example).

        RETURNS: List of:
                 [0] newline PPT and
                 [1] optionally the PPT of the newline suppressor.

        The primary pattern action pair list is to be the head of all pattern
        action pairs.

        MHI = Mode hierarchie index defining the priority of the current mode.
        """
        ISetup = Loopers.indentation_handler
        if ISetup is None: return [], [], []

        check_indentation_setup(ISetup)

        # Isolate the pattern objects, so alternatively, 
        # they may be treated in 'indentation_counter'.
        pattern_newline = ISetup.pattern_newline.clone()
        if ISetup.pattern_suppressed_newline:
            pattern_suppressed_newline = ISetup.pattern_suppressed_newline.clone()
        else:
            pattern_suppressed_newline = None

        new_analyzer_list,     \
        new_terminal_list,     \
        required_register_set, \
        run_time_counter_f     = indentation_counter.do(self.terminal_factory.mode_name, 
                                                        CaMap, ISetup, ReloadState, 
                                                        self.terminal_factory.dial_db)

        self.indentation_handler_newline_sm = pattern_newline.get_cloned_sm()
        self.indentation_handler_door_id    = DoorID.state_machine_entry(new_analyzer_list[0].state_machine_id, 
                                                                         self.terminal_factory.dial_db)

        self.terminal_factory.run_time_counter_required_f |= run_time_counter_f
        self.required_register_set.update(required_register_set)

        def _indentation_start_pattern_terminal(ISetup, CaMap, terminal_factory, pattern_newline, SmId):
            # 'newline' triggers --> indentation counter
            pattern  = pattern_newline.finalize(CaMap)
            pattern  = pattern.clone_with_new_incidence_id(E_IncidenceIDs.INDENTATION_HANDLER)
            terminal = TerminalGotoDoorId(DoorID.state_machine_entry(SmId, 
                                                                     terminal_factory.dial_db),
                                          IncidenceId         = pattern.incidence_id, 
                                          LCCI                = pattern.lcci,
                                          Name                = "<indentation handler>", 
                                          RequiredRegisterSet = required_register_set, 
                                          terminal_factory    = terminal_factory) 
            return PPT(PatternPriority(MHI, 0), pattern, terminal)

        def _suppressed_newline_pattern_terminal(ISetup, CaMap, terminal_factory, pattern_suppressed_newline):
            # 'newline-suppressor' causes following 'newline' to be ignored.
            # => next line not subject to new indentation counting.
            pattern  = pattern_suppressed_newline.finalize(CaMap)
            terminal = TerminalGotoDoorId(DoorID.global_reentry(terminal_factory.dial_db),
                                          IncidenceId         = pattern.incidence_id, 
                                          LCCI                = pattern.lcci,
                                          Name                =  "<indentation handler suppressed newline>", 
                                          RequiredRegisterSet = None, 
                                          terminal_factory    = terminal_factory) 
            return PPT(PatternPriority(MHI, 1), pattern, terminal)


        new_ppt_list = [
            _indentation_start_pattern_terminal(ISetup, CaMap, self.terminal_factory, 
                                                pattern_newline, new_analyzer_list[0].state_machine_id)
        ]

        if pattern_suppressed_newline is not None:
            new_ppt_list.append(
                _suppressed_newline_pattern_terminal(ISetup, CaMap, self.terminal_factory, 
                                                     pattern_suppressed_newline) 
            )

        return new_ppt_list, new_analyzer_list, new_terminal_list

    def _prepare_skip_character_set(self, MHI, Loopers, CaMap, ReloadState):
        """MHI = Mode hierarchie index."""
        if Loopers.skip is None: return [], [], []

        skipped_character_set, \
        pattern_str,           \
        aux_source_reference   = Loopers.combined_skip(CaMap)

        new_analyzer_list,    \
        new_terminal_list,    \
        character_set_list,   \
        required_register_set = skip_character_set.do(self.terminal_factory.mode_name,
                                                      CaMap, skipped_character_set, 
                                                      ReloadState, 
                                                      self.terminal_factory.dial_db)

        self.required_register_set.update(required_register_set)

        SKIP_door_id = DoorID.state_machine_entry(new_analyzer_list[0].state_machine_id, 
                                                  self.terminal_factory.dial_db)

        # Any skipped character must enter the skipper entry.
        new_ppt_list = []
        for character_set in character_set_list:
            new_incidence_id = dial.new_incidence_id()

            pattern  = Pattern.from_character_set(character_set, new_incidence_id, 
                                                  LCCI=None, PatternString="<skip>",
                                                  Sr=aux_source_reference)
            pattern.lcci = SmLineColumnCountInfo(CaMap, pattern.sm,
                                                 BeginOfLineF=False,
                                                 CodecTrafoInfo=Setup.buffer_encoding)
            # There is no reference pointer => Add directly
            terminal = TerminalGotoDoorId(SKIP_door_id,
                                          IncidenceId         = pattern.incidence_id, 
                                          LCCI                = pattern.lcci,
                                          Name                = "<skip>", 
                                          RequiredRegisterSet = required_register_set, 
                                          terminal_factory    = self.terminal_factory)

            new_ppt_list.append(
                PPT(PatternPriority(MHI, new_incidence_id), pattern, terminal)
            )

        return new_ppt_list, new_analyzer_list, new_terminal_list

    def _prepare_skip_range(self, MHI, Loopers, CaMap, ReloadState):
        """MHI = Mode hierarchie index.
        
        RETURNS: new ppt_list to be added to the existing one.
        """
        if not Loopers.skip_range: return [], [], []

        dial_db             = self.terminal_factory.dial_db
        new_ppt_list        = []
        extra_terminal_list = []
        extra_analyzer_list = []
        for i, data in enumerate(Loopers.skip_range):
            entry_pattern         = data.opener_pattern.clone().finalize(CaMap)
            closer_pattern_raw    = data.closer_pattern.clone()
            closer_suppressor_raw = data.closer_suppressor_pattern.clone()
            door_id_exit          = self._exit_to_indentation_handler_if_same_end(closer_pattern_raw)

            new_analyzer_list,     \
            new_terminal_list,     \
            required_register_set, \
            run_time_counter_f     = skip_nested_range.do(ModeName                = self.terminal_factory.mode_name, 
                                                          CaMap                   = CaMap, 
                                                          OpenerPattern           = Pattern_Prep.Empty(),
                                                          CloserPattern           = closer_pattern_raw, 
                                                          OpenerSuppressorPattern = Pattern_Prep.Empty(),
                                                          CloserSuppressorPattern = closer_suppressor_raw,
                                                          DoorIdExit              = door_id_exit,
                                                          ReloadState             = ReloadState, 
                                                          dial_db                 = dial_db,
                                                          NestedF                 = False)

            self.terminal_factory.run_time_counter_required_f |= run_time_counter_f

            self.required_register_set.update(required_register_set)

            extra_analyzer_list.extend(new_analyzer_list)
            extra_terminal_list.extend(new_terminal_list)

            terminal = TerminalGotoDoorId(DoorID.state_machine_entry(new_analyzer_list[0].state_machine_id, 
                                                                     self.terminal_factory.dial_db),
                                          IncidenceId         = entry_pattern.incidence_id, 
                                          LCCI                = entry_pattern.lcci,
                                          Name                = "<skip range>", 
                                          RequiredRegisterSet = required_register_set, 
                                          terminal_factory    = self.terminal_factory) 
            new_ppt_list.append(
                PPT(PatternPriority(MHI, i), entry_pattern, terminal)
            )

        return new_ppt_list, extra_analyzer_list, extra_terminal_list

    def _prepare_skip_nested_range(self, MHI, Loopers, CaMap, ReloadState):
        if not Loopers.skip_nested_range: return [], [], []

        dial_db             = self.terminal_factory.dial_db
        new_ppt_list        = []
        extra_terminal_list = []
        extra_analyzer_list = []
        for i, data in enumerate(Loopers.skip_nested_range):
            opener_pattern_raw    = data.opener_pattern.clone() # must come before 'entry_pattern'!
            closer_pattern_raw    = data.closer_pattern.clone()
            entry_pattern         = data.opener_pattern.finalize(CaMap).clone_with_new_incidence_id()
            closer_suppressor_raw = data.closer_suppressor_pattern.clone()
            opener_suppressor_raw = data.opener_suppressor_pattern.clone()

            door_id_exit = self._exit_to_indentation_handler_if_same_end(closer_pattern_raw)

            new_analyzer_list,     \
            new_terminal_list,     \
            required_register_set, \
            run_time_counter_f     = skip_nested_range.do(ModeName                = self.terminal_factory.mode_name, 
                                                          CaMap                   = CaMap, 
                                                          OpenerPattern           = opener_pattern_raw,
                                                          CloserPattern           = closer_pattern_raw, 
                                                          OpenerSuppressorPattern = opener_suppressor_raw,
                                                          CloserSuppressorPattern = closer_suppressor_raw,
                                                          DoorIdExit    = door_id_exit,
                                                          ReloadState   = ReloadState, 
                                                          dial_db       = dial_db)
    
            # The 'opener' has matched when this terminal is entered => counter = 1
            extra_CmdList = [ Op.AssignConstant(E_R.Counter,1) ]
            self.terminal_factory.run_time_counter_required_f |= run_time_counter_f
            self.required_register_set.update(required_register_set)
            extra_analyzer_list.extend(new_analyzer_list)
            extra_terminal_list.extend(new_terminal_list)

            terminal = TerminalGotoDoorId(DoorID.state_machine_entry(new_analyzer_list[0].state_machine_id, 
                                                                     self.terminal_factory.dial_db),
                                          IncidenceId         = entry_pattern.incidence_id, 
                                          LCCI                = entry_pattern.lcci,
                                          Name                =  "<skip nested range>", 
                                          RequiredRegisterSet = required_register_set, 
                                          terminal_factory    = self.terminal_factory,
                                          ExtraCmdList        = extra_CmdList) 
            new_ppt_list.append(
                PPT(PatternPriority(MHI, i), entry_pattern, terminal)
            )

        return new_ppt_list, extra_analyzer_list, extra_terminal_list

    def _exit_to_indentation_handler_if_same_end(self, CloserPattern):
        if self._match_indentation_counter_newline_pattern(CloserPattern): 
            return self.indentation_handler_door_id
        else:
            return DoorID.continue_without_on_after_match(self.terminal_factory.dial_db)
            
    def _match_indentation_counter_newline_pattern(self, CloserPattern):

        if CloserPattern is None: return False

        inewline_sm = self.indentation_handler_newline_sm
        closer_sm   = CloserPattern.get_cloned_sm()
        if inewline_sm is None or closer_sm is None: return False


        only_common_f, \
        common_f       = tail.do(inewline_sm, closer_sm)

        error_check.tail(only_common_f, common_f, 
                        "indentation handler's newline", inewline_sm.sr, 
                        "range skipper", CloserPattern.sr)

        return only_common_f

def check_indentation_setup(isetup):
    """None of the elements 'comment', 'newline', 'newline_suppressor' should 
       not match some subsets of each other. Otherwise, the behavior would be 
       too confusing.
    """
    candidates = [
        isetup.pattern_newline.get_cloned_sm(),
    ]
    if isetup.pattern_suppressed_newline is not None:
        candidates.append(
            isetup.pattern_suppressed_newline.get_cloned_sm()
        )
    if isetup.pattern_suspend_list:
        candidates.extend([
            p.get_cloned_sm() for p in isetup.pattern_suspend_list
        ])
    candidates = tuple(x for x in candidates if x is not None)

    def mutually_subset(Sm1, Sm2):
        if   Sm1 is None or Sm2 is None:                           return False
        elif superset_check.do(Sm1, Sm2): return True
        elif superset_check.do(Sm2, Sm1): return True
        return False

    for i, candidate1 in enumerate(candidates):
        if candidate1 is None: continue
        for candidate2 in candidates[i+1:]:
            if candidate2 is None: continue
            elif not mutually_subset(candidate1, candidate2): continue
            error.log_consistency_issue(candidate1, candidate2,
                                        ThisComment="matches on some common lexemes as",
                                        ThatComment="") 


# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.string_handling             import blue_print
#
from   quex.engine.misc.interval_handling           import NumberSet, Interval, \
                                                           NumberSet_All
import quex.engine.state_machine.index              as     state_machine_index
from   quex.engine.state_machine.state.core         import DFA_State
from   quex.engine.state_machine.state.single_entry import SeAccept
from   quex.input.code.base                         import SourceRef_VOID

from   quex.engine.misc.tree_walker  import TreeWalker, TreeIterator
from   quex.engine.misc.tools  import typed, flatten, \
                                      iterator_N_slots_with_setting_db
from   quex.constants          import E_IncidenceIDs, \
                                      E_AcceptanceCondition, \
                                      E_StateIndices, \
                                      INTEGER_MAX

from   copy        import copy
from   operator    import itemgetter

from   collections import defaultdict

class DFA(object):
    """A 'DFA', in Quex-Lingo, is a finite state automaton where all entries 
    into a state are subject to the same entry action. 

                  events
           ...   ----->---.                              .--->   ...
                           \                    .-----.-'
           ...   ----->-----+--->[ Action ]----( State )----->   ...
                           /                    '-----'
           ...   ----->---'        

    A 'DFA' must be considered in contrast to a 'FSM', a finite state machine
    where every transition into a state triggers its dedicated action.

    The term DFA comes from its closeness to the scientific definition of a
    DFA which "is a finite-state machine that accepts and rejects strings of
    symbols and only produces a unique computation of the automaton for each
    input string." (en.wikipedia.org/wiki/Deterministic_finite_automaton)

    However, a Quex-DFA-s can do more than just accept or reject patterns. They
    may count colum and line numbers, set jump positions for post-context
    pattern, or compute CRCs on the fly.
    """
    __slots__ = (
        "states",
        "init_state_index",
        "__id",
        "sr"
    )
    def __init__(self, InitStateIndex=None, AcceptanceF=False, InitState=None, DoNothingF=False, DfaId=None):
        if DfaId is None: self.set_id(state_machine_index.get_state_machine_id())
        else:             self.set_id(DfaId)

        self.sr = SourceRef_VOID

        if DoNothingF: 
            self.init_state_index = -1
            self.states           = {}
            return

        if InitStateIndex is None: InitStateIndex = state_machine_index.get()
        self.init_state_index = InitStateIndex
            
        # DFA_State Index => DFA_State (information about what triggers transition to what target state).
        if InitState is None: InitState = DFA_State(AcceptanceF=AcceptanceF)
        self.states = { self.init_state_index: InitState }        

    @staticmethod
    def Empty():
        """'Empty' <=> Matches nothing
                                                 .---.
                                                 |   |
                                                 '---'
        """
        return DFA()

    def is_Empty(self):
        if   len(self.states) != 1:                 return False
        elif self.get_init_state().is_acceptance(): return False
        else:                                       return True

    @staticmethod
    def Universe():
        """'Universe' <=> Matches everything      .------<-----------.
                                                 .===.                |
                                                 | A |--- any char ---'
                                                 '==='                 

        Difference to 'AnyPlus': match even on empty lexeme.
        """
        result = DFA(AcceptanceF=True)
        result.add_transition(result.init_state_index, NumberSet_All(), 
                              result.init_state_index)
        return result

    def is_Universal(self):
        if len(self.states) != 1:                 
            return False
        else:
            return self.is_AcceptAllState(self.init_state_index)

    @staticmethod
    def Nothing():
        """'Nothing' <=> matches nothing, not having any transitions.
           (This DFA is inadmissible)
                                           .===.
                                           | A |
                                           '==='
                                               
        """
        return DFA(AcceptanceF=True)

    def is_Nothing(self):
        if   len(self.states) != 1:                           return False
        elif not self.get_init_state().target_map.is_empty(): return False
        elif not self.get_init_state().is_acceptance():       return False
        else:                                                 return True

    @staticmethod
    def Any(CompleteSet=None):
        """'Any' <=> matches any character.
                                            .---.                 .===. 
                                            |   |--- any char --->| A |
                                            '---'                 '==='

        """
        if CompleteSet is None: CompleteSet = NumberSet_All()
        result = DFA()
        result.add_transition(result.init_state_index, CompleteSet, AcceptanceF=True)
        return result

    @staticmethod
    def AnyPlus():
        """'Any' <=> matches any character repeated at least once.

                                                .------<-----------. 
                        .---.                 .===.                |
                        |   |--- any char --->| A |--- any char ---'
                        '---'                 '==='                 

        Difference to 'Universe': match at least once.
        """
        result = DFA()
        si = result.add_transition(result.init_state_index, NumberSet_All(), AcceptanceF=True)
        result.add_transition(si, NumberSet_All())
        return result

    @staticmethod
    def from_iterable(InitStateIndex, IterableStateIndexStatePairs):
        """IterableStateIndexStatePairs = list of (state_index, state) 
        """
        result = DFA(DoNothingF=True)
        result.init_state_index = InitStateIndex
        result.states = dict(IterableStateIndexStatePairs)
        return result

    @staticmethod
    def from_sequence(Sequence):
        """Sequence is a list of one of the following:
            -- NumberSet
            -- Number
            -- Character
        """
        result = DFA()
        result.add_transition_sequence(result.init_state_index, Sequence)
        return result

    @staticmethod
    def from_path_list(PathList):
        """Path = list of (StateIndex, CharacterSet)

        where the 'CharacterSet' let to the 'StateIndex'. Therefore,
        Path[0][1] is None, since nothing has let to the initial state.
        """
        result = DFA()
        if not PathList or not PathList[0]: return result

        real_transition_f = False
        for path in PathList:
            # The state entered by 'None', can only be one!
            raw_start_si, character_set = path[0]
            start_si = result.init_state_index

            # Every path needs its own states, otherwise strange relations might
            # be webbed into the DFA.
            db       = { raw_start_si: start_si }
            LastIdx  = len(path) - 1
            for i, step in enumerate(path[1:], start=1):
                raw_target_si, character_set = step

                if raw_target_si not in db:
                    target_si         = state_machine_index.get()
                    db[raw_target_si] = target_si
                else:
                    target_si         = db[raw_target_si]

                if character_set is None: # epsilon transition 
                    result.add_epsilon_transition(start_si, target_si,
                                                  RaiseAcceptanceF=(i == LastIdx))
                    # next transition starts from same 'start_si'
                else:
                    real_transition_f = True
                    result.add_transition(start_si, character_set, target_si,
                                          AcceptanceF=(i == LastIdx))
                    # next transition starts from current 'target_si'
                    start_si = target_si

        if not real_transition_f: 
            return DFA()

        return result

    @staticmethod
    def from_character_set(CharacterSet, StateMachineId=None):
        result = DFA()
        result.add_transition(result.init_state_index, CharacterSet, AcceptanceF=True)
        if StateMachineId is not None: result.__id = StateMachineId
        return result

    @staticmethod
    def from_IncidenceIdMap(IncidenceIdMap, DfaId=None):
        """Generates a state machine that transits to states accepting specific
        incidence ids. That is from a list of (NumberSet, IncidenceId) pairs
        a state machine as the following is generated:

                        .----- set0 ---->( DFA_State 0: Accept Incidence0 )
                .-------.
                | init  |----- set1 ---->( DFA_State 1: Accept Incidence1 )
                | state |    
                '-------'                 ...

        IncidenceIdMap: 
                           incidence_id --> number set

        """
        def add(sm, StateIndex, TriggerSet, IncidenceId):
            if TriggerSet.is_empty(): return
            target_state_index = sm.add_transition(StateIndex, TriggerSet)
            target_state       = sm.states[target_state_index]
            target_state.set_acceptance()
            target_state.mark_acceptance_id(IncidenceId)

        sm = DFA(DfaId=DfaId)
        if IncidenceIdMap:
            for character_set, incidence_id in IncidenceIdMap:
                add(sm, sm.init_state_index, character_set, incidence_id)

        return sm

    def clone(self, ReplDbStateIndex=None, ReplDbPreContext=None, ReplDbAcceptance=None, 
              StateMachineId=None):
        """Clone state machine, i.e. create a new one with the same behavior,
        i.e. transitions, but with new unused state indices. This is used when
        state machines are to be created that combine the behavior of more
        then one state machine. E.g. see the function 'sequentialize'. Note:
        the state ids SUCCESS and TERMINATION are not replaced by new ones.

        RETURNS: cloned object if cloning successful
                 None          if cloning not possible due to external state references

        """
        def assert_transitivity(db):
            """Ids and their replacement remain in order, i.e. if x > y then db[x] > dv[y]."""
            if db is None: return
            prev_new = -1
            for old, new in sorted(iter(db.items()), key=itemgetter(0)): # x[0] = old value
                assert new > prev_new
                prev_new = new

        def assert_uniqueness(db):
            if db is None: return
            reference_set = set()
            for value in db.values():
                assert value not in reference_set
                reference_set.add(value)

        assert_uniqueness(ReplDbStateIndex)
        assert_uniqueness(ReplDbPreContext)
        assert_uniqueness(ReplDbAcceptance)
        assert_transitivity(ReplDbAcceptance)

        if ReplDbStateIndex is None: 
            ReplDbStateIndex = dict(
                (si, state_machine_index.get())
                for si in sorted(self.states.keys())
            )

        iterable = (
            (ReplDbStateIndex[si], state.clone(ReplDbStateIndex, 
                                               ReplDbPreContext=ReplDbPreContext,
                                               ReplDbAcceptance=ReplDbAcceptance))
            for si, state in self.states.items()
        )
        
        new_init_si = ReplDbStateIndex[self.init_state_index]
        result = DFA.from_iterable(new_init_si, iterable)
        if StateMachineId is not None: result.set_id(StateMachineId)

        return result

    def normalized_clone(self, ReplDbPreContext=None):
        index_map, dummy  = self.get_state_index_mapping_normalized()
        acceptance_condition_db, \
        pattern_id_map           = self.get_pattern_and_pre_context_normalization()
        
        return self.clone(index_map, 
                          ReplDbPreContext=acceptance_condition_db, 
                          ReplDbAcceptance=pattern_id_map)

    def clone_subset(self, StartSi, StateSiSet, DfaId=None):
        """Should do the same as 'clone_from_state_subset()', replacement 
        can be made after unit tests.
        """
        correspondance_db = {
            si: state_machine_index.get() for si in StateSiSet
        }
        result = DFA(InitStateIndex=correspondance_db[StartSi], DfaId=DfaId)

        result.states = {
            # '.clone(correspondance_db)' only clones transitions to target states 
            # which are mentioned in 'correspondance_db'.
            correspondance_db[si]: self.states[si].clone(correspondance_db)
            for si in StateSiSet
        }
        
        return result

    def get_id(self):
        assert isinstance(self.__id, int) or self.__id in E_IncidenceIDs
        return self.__id  # core.id()

    def set_id(self, Value):
        assert isinstance(Value, int) or Value == E_IncidenceIDs.INDENTATION_HANDLER or Value == E_IncidenceIDs.INDENTATION_BAD
        self.__id = Value # core.set_id(Value)

    def get_init_state(self):
        return self.states[self.init_state_index]

    def get_orphaned_state_index_list(self):
        """Find list of orphan states.

        ORPHAN STATE: A state that is not connected to an init state. That is
                      it can never be reached from the init state.
        """
        work_set      = set([ self.init_state_index ])
        connected_set = set()
        while work_set:
            state_index = work_set.pop()
            # may be the 'state_index' is not even in state machine
            state       = self.states.get(state_index) 
            if state is None: continue
            connected_set.add(state_index)

            work_set.update((i for i in state.target_map.get_target_state_index_list()
                             if  i not in connected_set))

        # indices in 'connected_set' have a connection to the init state.
        # indice not in 'connected_set' do not. => Those are the orphans.

        return [ i for i in self.states.keys() if i not in connected_set ]

    def get_hopeless_state_index_list(self):
        """Find list of hopeless states, i.e. states from one can never 
        reach an acceptance state. 
        
        HOPELESS STATE: A state that cannot reach an acceptance state.
                       (There is no connection forward to an acceptance state).
        """
        from_db = self.get_from_db()

        work_set     = set(  self.acceptance_state_index_list() 
                           + self.get_bad_lexatom_detector_state_index_list())
        reaching_set = set()  # set of states that reach acceptance states
        while len(work_set) != 0:
            state_index = work_set.pop()
            reaching_set.add(state_index)

            work_set.update((i for i in from_db[state_index] if  i not in reaching_set))

        # indices in 'reaching_set' have a connection to an acceptance state.
        # indice not in 'reaching_set' do not. => Those are the hopeless.
        return [ i for i in self.states.keys() if i not in reaching_set ]

    def get_epsilon_closure_db(self):
        return self.epsilon_closure_db(AddNoEpsilonStatesF=True)

    def epsilon_closure_db(self, AddNoEpsilonStatesF=False):
        """RETURNS: 
                    state index --> set(epsilon target state indices)
        """
        db = {}
        occurrence_db = defaultdict(int)
        for si, state in self.states.items():
            etsi_list = state.target_map.get_epsilon_target_state_index_list()
            if not etsi_list: 
                if AddNoEpsilonStatesF: db[si] = set([si])
                continue
            db[si] = set(etsi_list)
            db[si].add(si)
            for etsi in etsi_list: 
                occurrence_db[etsi] += 1

        # Expand those with the highest amount of references first.
        for si, closure in sorted(iter(db.items()), key=lambda x: - occurrence_db[x[0]]):
            worklist = set(closure)
            done_set = set([si])
            while worklist:
                csi          = worklist.pop()
                csi_closure  = db.get(csi)
                done_set.add(csi)
                if csi_closure is None: continue
                new_etsi_set = csi_closure.difference(closure)
                closure.update(new_etsi_set)
                worklist.update(x for x in new_etsi_set if x not in done_set)
            # 'closure' (a reference) of 'si' has been updated.

        return db

    def get_epsilon_closure(self, StateIdx):
        """Return all states that can be reached from 'StateIdx' via epsilon
           transition."""
        assert StateIdx in self.states

        result = set([StateIdx])
        self.__dive_for_epsilon_closure(StateIdx, result)
        return result
 
    def acceptance_state_iterable(self):
        return [ 
            (si, state) 
            for si, state in self.states.items() if state.is_acceptance() 
        ]

    def get_acceptance_state_list(self):
        return [ 
            state 
            for state in self.states.values() if state.is_acceptance() 
        ]

    def acceptance_id_set(self):
        return set(flatten( 
            state.acceptance_id_set() for state in self.states.values() 
            if state.is_acceptance() 
        ))

    def get_bad_lexatom_detector_state_index_list(self):
        """At the time of this writing, BAD_LEXATOMs are implemented as states 
        accepting 'BAD_LEXATOM' and performing a transition upon drop-out.
        Bad-lexatom detector states are not 'hopeless' states, so this function
        is there to collect them.
        """
        return [ 
            index for index, state in self.states.items() 
                  if state.is_bad_lexatom_detector() 
        ]

    def acceptance_state_index_list(self, AcceptanceID=None):
        if AcceptanceID is None:
            return [ 
                index for index, state in self.states.items() 
                      if state.is_acceptance() 
            ]

        return [ 
            index for index, state in self.states.items() 
                  if     state.is_acceptance() 
                     and state.single_entry.has_acceptance_id(AcceptanceID) 
        ]

    def get_to_db(self):
        """RETURNS:
                    map:    state_index --> states which it enters
        """
        return dict(
            (from_index, set(state.target_map.get_map().keys()))
            for from_index, state in self.states.items()
        )

    def get_from_db(self):
        """RETURNS:
                    map:     state_index --> states from which it is entered.
        """
        from_db = defaultdict(set)
        for from_index, state in self.states.items():
            for to_index in state.target_map.get_target_state_index_list():
                from_db[to_index].add(from_index)
        return from_db

    def get_pure_epsilon_state_set(self):
        """RETURNS: Set of indices of state which are not entered through
                    trigger-transitions.

        If there are no orphaned states, then the result are the states which
        are only entered via epsilon transitions.
        """
        candidates = set(self.states.keys())
        if self.init_state_index in candidates: 
            candidates.remove(self.init_state_index)
        for state in self.states.values():
            candidates.difference_update(list(state.target_map.get_map().keys()))
        return candidates

    def get_successors(self, SI):
        """RETURNS: State indices of all successor states of 'SI' 
                    including 'SI' itself.
        """
        work_set = set([SI])
        result   = set([SI])
        while work_set:
            state          = self.states[work_set.pop()]
            target_si_list = state.target_map.get_target_state_index_list()
            work_set.update(
                target_si 
                for target_si in target_si_list if target_si not in result
            )
            result.update(target_si_list)
        return result

    def get_predecessors(self, SI):
        """RETURNS: State indices of all predecessor states of 'SI' 
                    including 'SI' itself.
        HINT: If this function is to be called multiple times, better generate
              a 'predecessor_db' and interview the database.
        """
        predecessor_db = self.get_predecessor_db()
        return predecessor_db[SI] + [SI]
    
    def get_predecessor_db(self):
        """RETURNS:
        
            map:   state index ---> set of states that lie on the path to it.

        PROOF: 
            
        (1) Whenever a transition from B to A is entered, the predecessor set
        of A receives all known predecessors of B and B itself as predecessor.

        (2) Every predecessor set containing A is extended by the B and its 
        predecessors. Thus, ALL states containing A in their known predecessors
        receive the newly known predecessors of A.

        (3) Since, at the end all predecessor relationships are treated, all 
        known relationships are entered and all precessors are 'connected'.
        """
        def update(predecessor_db, StateIndex, PredecessorSet):
            """Enter into the 'predecessor_db' that all states in 'PredecessorSet'
            are predecessors of 'StateIndex'. Also, all states of which the 
            StateIndex is a predecessor, inherit its predecessors.
            """
            predecessor_db[StateIndex].update(PredecessorSet)
            for prev_predecessor_set in predecessor_db.values():
                if StateIndex not in prev_predecessor_set: continue
                prev_predecessor_set.update(PredecessorSet)
                    
        predecessor_db = defaultdict(set)
        for si, state in self.states.items():
            target_predecessor_set = copy(predecessor_db[si])
            target_predecessor_set.add(si)
            for target_si in state.target_map.get_map().keys():
                update(predecessor_db, target_si, target_predecessor_set)

        return predecessor_db

    def get_successor_db(self, HintPredecessorDb=None):
        """RETURNS:

            map:   state index ---> set of states on the path from init state to this state.

        The algorithm takes the result from 'get_predecessor_db' and inverts it.
        """
        if not HintPredecessorDb:
            HintPredecessorDb = self.get_predecessor_db()

        successor_db = defaultdict(set)
        for si, predecessor_set in HintPredecessorDb.items():
            for predecessor_si in predecessor_set:
                successor_db[predecessor_si].add(si)
        return successor_db

    def get_sequence(self):
        """RETURNS: list of number if all transitions happen on single numbers
                         and no state has more than one transition.
                    None, else.
        """
        sequence = []
        state = self.get_init_state()
        done  = set([self.init_state_index])
        while state.has_transitions():
            tm = state.target_map.get_map()
            if len(tm) != 1: return None
            si, number_set = next(iter(tm.items()))
            if not number_set.has_size_one(): return None
            elif si in done: return None

            sequence.append(number_set.minimum())
            state = self.states[si]
            done.add(si)

        if state.is_acceptance(): return sequence
        else:                     return None

    def iterable_NumberSetSequences(self, max_loop_n=1):
        for path in [p for p in self.iterable_paths(max_loop_n)]:
            yield [step[1] for step in path[1:]]

    def iterable_lexemes(self, max_loop_n=1):
        for number_set_sequence in self.iterable_NumberSetSequences(max_loop_n):
            for number_sequence in NumberSetSequence_to_NumberSequences(number_set_sequence):
                yield number_sequence

    def iterable_paths(self, MaxLoopN):
        class PathsFinder(TreeIterator):
            def __init__(self, Dfa, MaxLoopN):
                self.dfa             = Dfa
                self.path            = []
                self.done_on_path_db = defaultdict(int)
                self.max_loop_n      = MaxLoopN
                TreeIterator.__init__(self)

            def on_enter(self, Node):
                from_si, character_set = Node
                self.path.append((from_si, character_set))
                self.done_on_path_db[from_si] += 1

                harvest       = []
                if self.dfa.states[from_si].is_acceptance():
                    harvest.append(copy(self.path))

                sub_node_list = []
                for target_si, character_set in self.dfa.states[from_si].target_map:
                    if self.done_on_path_db[target_si] <= self.max_loop_n:
                        sub_node_list.append((target_si, character_set))

                return sub_node_list, harvest

            def on_finished(self, Node):
                si, cs = self.path.pop()
                self.done_on_path_db[si] -= 1

        path_finder = PathsFinder(self, MaxLoopN)
        for path in path_finder.do((self.init_state_index, None)):
            yield path

    def get_number_set(self):
        """Returns a number set that represents the state machine.
        If the state machine cannot be represented by a plain NumberSet,
        then it returns 'None'.

        Assumes: DFA is 'beautified'.
        """
        if len(self.states) != 2: return None

        # There can be only one target state from the init state
        target_map = self.get_init_state().target_map.get_map()
        if len(target_map) != 1: return None

        target, number_set = next(iter(target_map.items()))
        if self.states[target].has_transitions(): return None
        return number_set

    def get_union_of_number_sets(self):
        """RETURNS: union of all NumberSet-s in transition trigger sets.
        """
        return NumberSet.from_union_of_iterable(
            state.target_map.get_trigger_set_union()
            for state in self.states.values()
        )

    def get_beginning_character_set(self):
        """Return the character set union of all triggers in the init state.
        """
        return self.get_init_state().target_map.get_trigger_set_union()

    def get_state_index_mapping(self):
        index_map      = {}
        index_sequence = self.__get_state_sequence_for_normalization()
        for state_i in index_sequence:
            index_map[state_i] = state_i

        return index_map, index_sequence

    def get_state_index_mapping_normalized(self, NormalizeF=True):
        index_sequence = self.__get_state_sequence_for_normalization()
        index_map      = dict( (state_i, counter) for counter, state_i in enumerate(index_sequence))
        return index_map, index_sequence

    def get_pattern_and_pre_context_normalization(self, PreContextID_Offset=None, 
                                                  AcceptanceID_Offset=None):

        acceptance_condition_set_set = set()
        acceptance_id_set            = set()
        for state in self.states.values():
            for cmd in state.single_entry.get_iterable(SeAccept):
                acceptance_condition_set_set.add(cmd.acceptance_condition_set())
                acceptance_id_set.add(cmd.acceptance_id())
                
        def enter(db, Value, TheEnum, NewId):
            if Value in TheEnum: db[Value] = Value; return NewId
            else:                db[Value] = NewId; return NewId + 1

        i = 1
        repl_db_acceptance_condition_id = {}
        for acceptance_condition_set in sorted(acceptance_condition_set_set):
            for acceptance_condition_id in acceptance_condition_set:
                i = enter(repl_db_acceptance_condition_id, acceptance_condition_id, E_AcceptanceCondition, i)

        i = 1
        repl_db_acceptance_id  = {}
        for acceptance_id in sorted(acceptance_id_set):
            i = enter(repl_db_acceptance_id, acceptance_id, E_IncidenceIDs, i)

        return repl_db_acceptance_condition_id, \
               repl_db_acceptance_id

    def get_string(self, NormalizeF=False, Option="utf8", OriginalStatesF=True):
        assert Option in ("hex", "dec", "utf8")

        # (*) normalize the state indices
        if NormalizeF:
            index_map, index_sequence = self.get_state_index_mapping_normalized()
        else:
            index_map, index_sequence = self.get_state_index_mapping()

        # (*) construct text 
        msg = "init-state = " + repr(index_map[self.init_state_index]) + "\n"
        for state_i in index_sequence:
            printed_state_i = index_map[state_i]
            state           = self.states[state_i]
            try:    state_str = "%05i" % printed_state_i
            except: state_str = "%s"   % printed_state_i
            msg += "%s%s" % (state_str, state.get_string(index_map, Option, OriginalStatesF))

        return msg

    def get_graphviz_string(self, NormalizeF=False, Option="utf8"):
        assert Option in ("hex", "dec", "utf8")

        # (*) normalize the state indices
        if NormalizeF:
            index_map, index_sequence = self.get_state_index_mapping_normalized()
        else:
            index_map, index_sequence = self.get_state_index_mapping()

        # (*) Border of plot block
        frame_txt  = "digraph state_machine_%i {\n" % self.get_id()
        frame_txt += "rankdir=LR;\n"
        frame_txt += "size=\"8,5\"\n"
        frame_txt += "node [shape = doublecircle]; $$ACCEPTANCE_STATES$$\n"
        frame_txt += "node [shape = circle]; $$NON_ACCEPTANCE_STATES$$\n"
        frame_txt += "$$TRANSITIONS$$"
        frame_txt += "}\n"

        transition_str           = ""
        acceptance_state_str     = ""
        non_acceptance_state_str = ""
        for printed_state_i, state in sorted(map(lambda i: (index_map[i], self.states[i]), index_sequence)):
            if state.is_acceptance(): 
                acceptance_state_str     += "%i; " % int(printed_state_i)
            else:
                non_acceptance_state_str += "%i; " % int(printed_state_i)
            transition_str += state.get_graphviz_string(printed_state_i, index_map, Option)

        if acceptance_state_str != "": acceptance_state_str = acceptance_state_str[:-2] + ";"
        return blue_print(frame_txt, [["$$ACCEPTANCE_STATES$$",     acceptance_state_str ],
                                      ["$$NON_ACCEPTANCE_STATES$$", non_acceptance_state_str ],
                                      ["$$TRANSITIONS$$",           transition_str]])
        
    def __get_state_sequence_for_normalization(self):
        def _key(state_db, tm, A):
            """Decide which target state is to be considered next. Sort by 'lowest trigger'.
            """
            trigger_set_to_A = tm.get(A)
            assert trigger_set_to_A is not None
            trigger_set_min = trigger_set_to_A.minimum()
            target_tm       = state_db[A].target_map.get_map()
            target_branch_n = len(target_tm)
            if not target_tm: target_tm_min = -INTEGER_MAX
            else:             target_tm_min = min([x.minimum() for x in iter(target_tm.values())])
            return (trigger_set_min, target_branch_n, target_tm_min, A)

        result     = []
        work_stack = [ self.init_state_index ]
        done_set   = set()
        while work_stack:
            i = work_stack.pop()
            if i in done_set: continue

            result.append(i)
            done_set.add(i)

            tm = self.states[i].target_map.get_map()
            target_state_index_list = [ k for k in tm.keys() if k not in done_set ]
            target_state_index_list.sort(key=lambda x: _key(self.states, tm, x), reverse=True)

            work_stack.extend(target_state_index_list)
                                         
        # Append 'orphans' sorted by state index. 
        if len(self.states) != len(done_set):
            orphans = set(self.states.keys()).difference(done_set)
            result.extend(sorted(orphans))

        return result

    def longest_path_to_first_acceptance(self):
        """Find the longest path to first acceptance state.

        'First acceptance state' is an acceptance state which can be
        reached without passing by another acceptance state.

        This function is useful for pre-contexts, where the arrival at
        the first acceptance state is sufficient. With the longest path
        possible to such a state a reasonable 'fallback number' can be
        determined, i.e. the number of lexatoms to maintain inside the
        buffer upon reload.

        RETURNS: Number of lexatoms to reach the first acceptance state.
                 None, if path is not unique.
        """
        worklist   = [(self.init_state_index, 0, set([self.init_state_index]))]
        max_length = -1
        while worklist:
            si, length, predecessor_set = worklist.pop()
            if self.states[si].is_acceptance():
                if length > max_length: max_length = length
                # NOT: si -> done_set, otherwise the acceptance could not be 
                #                      entered from elsewhere.
                # NOT: successors -> worklist, because anything behind the 
                #                              acceptance state is meaningless.
            else:
                new_predecessor_set = predecessor_set.copy()
                new_predecessor_set.add(si)
                for target_si in self.states[si].target_map.get_map().keys():
                    if target_si in predecessor_set: return None
                    worklist.append((target_si, length+1, new_predecessor_set))

        if max_length == -1: return None
        else:                return max_length

    def clean_up(self):
        # Delete states which are not connected from the init state.
        self.delete_orphaned_states()
        # Delete states from where there is no connection to an acceptance state.
        self.delete_hopeless_states() 

    def delete_state(self, StateIdx):
        try:    del self.states[StateIdx]
        except: pass

    def delete_loops_to_init_state(self):
        """Deleting transitions to the init state makes sure that there is no
        iteration, no loop, that starts from the init state. That in turn, 
        ensures, that for the reverse state machine, there is no loop starting
        from an acceptance state.
        """
        for state in self.states.values():
            state.target_map.delete_transitions_to_target(self.init_state_index)
        self.delete_orphaned_states()

    def delete_orphaned_states(self):
        """Remove all orphan states.

        ORPHAN STATE: A state that is not connected to an init state. That is
                      it can never be reached from the init state.
        """
        for state_index in self.get_orphaned_state_index_list():
            if state_index == self.init_state_index: continue
            self.states.pop(state_index)

    def delete_hopeless_states(self):
        """Delete all hopeless states and transitions to them.

        HOPELESS STATE: A state that cannot reach an acceptance state.
                       (There is no connection forward to an acceptance state).
        """
        hopeless_si_set = set(self.get_hopeless_state_index_list())
        concerned_state_list = [
            state
            for si, state in self.states.items()
            if si not in hopeless_si_set or si == self.init_state_index
        ]
        for hl_si in hopeless_si_set:
            for state in concerned_state_list:
                state.target_map.delete_transitions_to_target(hl_si)
            if hl_si == self.init_state_index: continue
            self.states.pop(hl_si)
        return 

    def delete_transitions_on_number(self, Number):
        """This function deletes any transition on 'Value' to another
           state. The resulting orphaned states are deleted. The operation
           may leave orphaned states! They need to be deleted manually.
        """
        for state in self.states.values():
            # 'items()' not 'iteritems()' because 'delete_transitions_to_target()'
            # may change the dictionaries content.
            for target_state_index, trigger_set in list(state.target_map.get_map().items()):
                assert not trigger_set.is_empty()
                if not trigger_set.contains(Number): continue

                trigger_set.cut_interval(Interval(Number))
                # If the operation resulted in cutting the path to the target state, 
                # => then delete it.
                if trigger_set.is_empty():
                    state.target_map.delete_transitions_to_target(target_state_index)

        return

    def delete_named_number_list(self, NamedNumberList):
        """Input: list of (number, name)

        Deletes and given 'number' from the transitions of the state machine. 
        
        RETURNS: 'name' of the number that made the state machine empty.
                 None,  if everything is Ok, things have been removed, 
                        sm not empty.
        """
        for number, name in NamedNumberList:
            self.delete_transitions_on_number(number)
            self.clean_up()
            if self.is_Empty(): return name
        return None

    def delete_transitions_beyond_interval(self, MaskInterval):
        """Removes any transitions beyond the specified 'MaskInterval' from the DFA.
        """
        for from_si, state in list(self.states.items()):
            target_map = state.target_map.get_map()
            for to_si, number_set in list(target_map.items()):
                number_set.mask_interval(MaskInterval)
                if number_set.is_empty(): del target_map[to_si]

    def __dive_for_epsilon_closure(self, state_index, result):
        index_list = self.states[state_index].target_map.get_epsilon_target_state_index_list()
        for target_index in filter(lambda x: x not in result, index_list):
            result.add(target_index)
            self.__dive_for_epsilon_closure(target_index, result)

    def is_DFA_compliant(self):
        for state in list(self.states.values()):
            if state.target_map.is_DFA_compliant() == False: 
                return False
        return True

    def is_AcceptAllState(self, StateIndex):
        """RETURNS: True,  if the state accepts and iterates on every character to
                           itself.
                    False, else.
        """
        state = self.states[StateIndex]
        if not state.is_acceptance():     return False

        tm = state.target_map.get_map()
        if len(tm) != 1:                  return False

        target_index, trigger_set = next(iter(tm.items()))
        if   target_index != StateIndex:  return False
        elif not trigger_set.is_all():    return False
        else:                             return True

    def has_transition_to(self, TargetIndex):
        return any(state.target_map.has_target(TargetIndex)
                   for state in self.states.values())

    def has_orphaned_states(self):
        """Detect whether there are states where there is no transition to them."""
        unique = set([])
        for state in list(self.states.values()):
            unique.update(state.target_map.get_target_state_index_list())

        return any(state_index not in unique and state_index != self.init_state_index
                   for state_index in self.states.keys())

    def has_acceptance_condition(self, AccConditionId):
        return any(AccConditionId in state.acceptance_condition_set()
                   for state in self.states.values())

    def has_specific_acceptance_id(self):
        return any(state.single_entry.has_specific_acceptance_id()
                   for state in self.states.values())

    def set_new_init_state(self, new_state):
        self.init_state_index              = state_machine_index.get()
        self.states[self.init_state_index] = new_state
        return self.init_state_index

    def create_new_init_state(self, AcceptanceF=False):
        self.init_state_index = self.create_new_state()
        return self.init_state_index

    def create_new_state(self, AcceptanceF=False, StateIdx=None, RestoreInputPositionF=False, 
                         MarkAcceptanceId=None):
        """RETURNS: DFA_State index of the new state.
        """
        if StateIdx is None: new_si = state_machine_index.get()
        else:                new_si = StateIdx

        new_state = DFA_State(AcceptanceF or MarkAcceptanceId is not None)
        if MarkAcceptanceId is not None:
            new_state.mark_acceptance_id(MarkAcceptanceId)
            if RestoreInputPositionF:
                new_state.set_read_position_restore_f()

        self.states[new_si] = new_state
        return new_si

    def create_new_state_from_closure(self, SiClosure, RemoveEpsilonTansitionsF=False):
        """'SiClosure' = set of state indices to be combined. States remain in 
        place.
        """
        state_list = [self.states[si] for si in SiClosure]

        # Merge 'single_entry'
        new_state = DFA_State.from_state_iterable(state_list)
        # Merge target maps.
        for state in state_list:
            new_state.target_map.absorb_target_map(state.target_map.get_map())

        new_si = state_machine_index.get()
        self.states[new_si] = new_state
        return new_si
        
    @typed(StartStateIdx=int, AcceptanceF=bool)
    def add_transition(self, StartStateIdx, TriggerSet, TargetStateIdx = None, AcceptanceF = False):
        """Adds a transition from Start to Target based on a given Trigger.

           TriggerSet can be of different types: ... see add_transition()
           
           (see comment on 'DFA_State::add_transition)

           RETURNS: The target state index.
        """
        # NOTE: The Transition Constructor is very tolerant, so no tests on TriggerSet()
        #       assert TriggerSet.__class__.__name__ == "NumberSet"
        assert type(TargetStateIdx) == int or TargetStateIdx is None or TargetStateIdx in E_StateIndices

        # If target state is undefined (None) then a new one has to be created
        if TargetStateIdx is None:                  TargetStateIdx = state_machine_index.get()
        if StartStateIdx not in self.states:  self.states[StartStateIdx]  = DFA_State()        
        if TargetStateIdx not in self.states: self.states[TargetStateIdx] = DFA_State()
        if AcceptanceF:                             self.states[TargetStateIdx].set_acceptance(True)

        self.states[StartStateIdx].add_transition(TriggerSet, TargetStateIdx)

        return TargetStateIdx
            
    def add_transition_sequence(self, StartIdx, Sequence, AcceptanceF=True):
        """Add a sequence of transitions which is ending with acceptance--optionally.
        """
        idx = StartIdx
        for x in Sequence:
            idx = self.add_transition(idx, x)
        if AcceptanceF:
            self.states[idx].set_acceptance(True)

    def add_epsilon_transition(self, StartStateIdx, TargetStateIdx=None, RaiseAcceptanceF=False):
        assert TargetStateIdx is None or type(TargetStateIdx) == int

        # create new state if index does not exist
        if StartStateIdx not in self.states:
            self.states[StartStateIdx] = DFA_State()
        if TargetStateIdx is None:
            TargetStateIdx = self.create_new_state(AcceptanceF=RaiseAcceptanceF)
        elif TargetStateIdx not in self.states:
            self.states[TargetStateIdx] = DFA_State()

        # add the epsilon target state
        self.states[StartStateIdx].target_map.add_epsilon_target_state(TargetStateIdx)     
        # optionally raise the state of the target to 'acceptance'
        if RaiseAcceptanceF: self.states[TargetStateIdx].set_acceptance(True)

        return TargetStateIdx

    def mark_state_origins(self, OtherStateMachineID=-1):
        """Marks at each state that it originates from this state machine. This is
           important, when multiple patterns are combined into a single DFA and
           origins need to be traced down. In this case, each pattern (which is
           are all state machines) needs to mark the states with the state machine 
           identifier and the state inside this state machine.

           If OtherStateMachineID and StateIdx are specified other origins
              than the current state machine can be defined (useful for pre- and post-
              conditions).         
        """
        assert type(OtherStateMachineID) == int or OtherStateMachineID in E_IncidenceIDs

        if OtherStateMachineID == -1: state_machine_id = self.__id
        else:                          state_machine_id = OtherStateMachineID

        for state_idx, state in list(self.states.items()):
            state.mark_acceptance_id(state_machine_id)

    def mount_to_acceptance_states(self, MountedStateIdx, 
                                   CancelStartAcceptanceStateF=True):
        """Mount on any acceptance state the MountedStateIdx via epsilon transition.
        """
        for state_idx, state in self.acceptance_state_iterable():
            # -- only handle only acceptance states
            # -- only consider state other than the state to be mounted
            if state_idx == MountedStateIdx: continue
            # add the MountedStateIdx to the list of epsilon transition targets
            state.target_map.add_epsilon_target_state(MountedStateIdx)
            # if required (e.g. for sequentialization) cancel the acceptance status
            if CancelStartAcceptanceStateF: 
                # If there was a condition to acceptance => Cancel it first
                state.set_acceptance_condition_id(None) 
                state.set_acceptance(False)

    def replace_triggers(self, ReplacementDict):
        for state in self.states.values():
            state.target_map.replace_triggers(ReplacementDict)

    def replace_target_indices(self, ReplacementDict):
        for state in self.states.values():
            state.target_map.replace_target_indices(ReplacementDict)

    def filter_dominated_origins(self):
        for state in list(self.states.values()): 
            state.single_entry.delete_dominated()

    @typed(Sequence=list)
    def apply_sequence(self, Sequence, StopAtBadLexatomF=True):
        """RETURNS: Resulting target state if 'Sequence' is applied on 
                    state machine.

           This works ONLY on DFA!
        """
        si = self.init_state_index
        for x in Sequence:
            si = self.states[si].target_map.get_resulting_target_state_index(x)
            if si is None: return None
            elif self.states[si].has_acceptance_id(E_IncidenceIDs.BAD_LEXATOM):
                break
        return self.states[si]

    @typed(Sequence=[NumberSet])
    def match_NumberSet_sequence(self, Sequence):
        """RETURNS: 'True', if sequence of NumberSets can be matched by self.
                    'False', else.
        """
        if not Sequence:
            return True

        worklist = [(self.get_init_state().target_map, copy(Sequence))]
        while worklist:
            tm, tail      = worklist.pop()
            character_set = tail.pop(0)
            submap        = tm.get_resulting_target_state_index_list_if_complete(character_set)
            if submap is None: return False
            elif not tail:     continue
            for ti in submap:
                worklist.append((self.states[ti].target_map, copy(tail)))
        return True

    def iterable_target_state_indices(self, StateIndex):
        return self.state_db[StateIndex].iterable_target_state_indices(StateIndex)

    def __repr__(self):
        return self.get_string(NormalizeF=True)

    def assert_consistency(self):
        """Check: -- whether each target state in contained inside the state machine.
        """
        state_indice_set = set(self.states.keys())
        for state in self.states.values():
            assert state_indice_set.issuperset(state.target_map.get_target_state_index_list())

    def assert_range(self, Range):
        for state in self.states.values():
            for number_set in state.target_map.get_map().values():
                number_set.assert_range(Range.minimum(), Range.least_greater_bound())
           
    def has_acceptance_state(self):
        return any(state.is_acceptance() for state in list(self.states.values()))

    def has_cycles(self):
        """Searches recursively for cycles.

        RETURNS: True, if a cycle has been found.
                 False, else.
        """
        class CycleSearcher(TreeWalker):
            def __init__(self, Dfa):
                self.dfa           = Dfa
                self.path          = []
                self.found_cycle_f = False
                TreeWalker.__init__(self)

            def on_enter(self, FromSi):
                self.path.append(FromSi)

                sub_node_list = []
                for target_si in self.dfa.states[FromSi].target_map.iterable_target_state_indices():
                    if target_si in self.path: 
                        self.abort_f       = True
                        self.found_cycle_f = True
                    else:
                        sub_node_list.append(target_si)

                return sub_node_list

            def on_finished(self, Node):
                self.path.pop()

        searcher = CycleSearcher(self)
        searcher.do(self.init_state_index)
        return searcher.found_cycle_f

def NumberSetSequence_to_NumberSequences(NumberSetSequence):
    """Takes a sequence of NumberSet objects. Each NumberSet corresponds
    to possible numbers at the position where it occurs. Alls possible
    combination of numbers are, then, expanded. Finally the result is
    a list of number sequences which are possible for the given NumberSet
    sequence.

    YIELD:   number sequence

    EXAMPLE: [0,1], [5,6,7], [10]

             yield 0, 5, 10
             yield 0, 6, 10
             yield 0, 7, 10
             yield 1, 5, 10
             yield 1, 6, 10
             yield 1, 7, 10

    """
    def _one_or_None(step):
        if step.has_size_one(): return step.get_the_only_element()
        else:                   return None

    def _plug(PlugPositions, PlugSettings, NumberSequence):
        result = list(NumberSequence) # Clone number sequence
        for i, value in zip(PlugPositions, PlugSettings):
            result[i] = value
        return result

    number_sequence = [ _one_or_None(step) for step in NumberSetSequence ]
    if None not in number_sequence:
        # If all elements of the sequence are of 'size = one number', then
        # then nothing has to be expanded.
        yield number_sequence
        return

    # Positions where there is more than one alternative, because
    # the NumberSet's size is greater than 1.
    plug_positions = [
        i for i, step in enumerate(number_sequence) if step is None
    ]
    plug_setting_db = [
        NumberSetSequence[i].get_number_list() for i in plug_positions
    ]
    for plug_settings in iterator_N_slots_with_setting_db(plug_setting_db):
        # Plug the number settings into the 'open' positions of the 
        # lexatom sequence
        yield _plug(plug_positions, plug_settings, number_sequence)

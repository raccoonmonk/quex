# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""
________________________________________________________________________________
Trace Analysis

For each state in the state machine (virtually) all paths are considered which
guide through it. The analysis is concerned with acceptance and input position
storage and restorage. A path corresponds to a possible sequence of state
transition as consequence of a sequence of appearing characters.

The main result is a map that tells what consequences a path has in a specific 
state, i.e.:

    trace_db:        state index --> consequences of paths

As a by-product a 'path_element_db' is developed which tells for a given 
state what states lie on the path to it, i.e.

    path_element_db: state index --> indices of states which lie
                                     on the path to that state.
________________________________________________________________________________
EXPLANATION:

Each path is related to a list of 'AcceptCondition' objects. An
AcceptCondition consists of the following main members:

    .acceptance_id           -- Pattern that can be accepted.
    
    .acceptance_condition_set -- Conditions for acceptance.
    
    .accepting_state_index   -- State where the last acceptance of 'acceptance_id' 
                                appeared.
    
    .positioning_state_index -- State where the input position had to be 
                                stored.

    .transition_n_since_positioning -- ... self explanatory

Different acceptance_id-s may be involved in the same state, 

  (i)  because the state may be reached through different paths or 

  (ii) because the winning pattern may depend on what pre-context is 
       fulfilled. 
  
The position storing state is involved when 

  (i)  a post-context needs to reset the input pointer to the end of 
       the core lexeme or 

  (ii) an acceptance detected on a previous state is winning. In that
       case the positioning state index is equal to the accepting
       state index.

The eventualities of a path is represented by a list of AcceptCondition 
objects. It behaves like a list where sorting order tells the precedence 
of winners. The first pattern where the pre_context is fulfilled wins.

     AcceptSequence: [ 
          #               length       acceptance_id   acceptance_condition_set   ...
          AcceptCondition(67,          2,               ...)
          AcceptCondition(32,          1,               ...)
          AcceptCondition(7,           None,            ...)
     ]

Note, that length has preceedence over acceptance_id. For this reason, greater
acceptance_id-s may have precedence of higher once--if it matches a longer
lexeme.

Since there are potentially mutiple paths to a state, there is a list of
lists of AcceptCondition objects. Thus the mapping:

    map:  state index --> consequences of paths

is represented by 

    map:  state index --> list(list(AcceptCondition)) 
________________________________________________________________________________

Based on this information on AcceptCondition-s requirements on entry and 
drop_out behaviors of a state can be derived. This is done by module 'core.py'.
________________________________________________________________________________
NOTE:

It is possible, that not all paths are walked along. If a state is reached 
though a different path but with the same consequence as another path through
that state, then the further investigation of that path is aborted. All 
possible informations have been gathered, no need to investigate further.
________________________________________________________________________________
(C) 2010-2014 Frank-Rene Schaefer
ABSOLUTELY NO WARRANTY
________________________________________________________________________________
"""
from   quex.engine.operations.se_operations              import SeAccept, \
                                                                SeStoreInputPosition
from   quex.engine.misc.tree_walker                      import TreeWalker
from   quex.engine.misc.tools                            import typed
from   quex.engine.analyzer.trace_analysis.merged_traces import MergedTraces
from   quex.constants                                    import E_IncidenceIDs, \
                                                                E_TransitionN


from   collections import namedtuple, defaultdict
from   copy        import copy
from   zlib        import crc32


T_RestorePosition   = namedtuple("T_RestorePosition",   ("storing_si_set", "transition_n_since_positioning"))
T_AcceptAndPosition = namedtuple("T_AcceptAndPosition", ("acceptance_sequence", "position_db"))

class TA_StateInfo(object):
    """Brief information about the acceptance and positioning related to a 
    particular state. It has the following structure.
        
    .store.acceptance_sequence:    list of acceptance-ids
          .position_db:            acceptance-id --> target indices in direction
                                                     of according position restore

    .restore.acceptance_sequence:  list of acceptance-ids
            .position_db:          acceptance-id --> transition n since storing
                                                     position storing state indices.
    """
    __slots__ = ("store", "restore")
    def __init__(self, 
                 store_acceptance_sequence, store_position_db, 
                 restore_acceptance_sequence, restore_position_db):
        self.store   = T_AcceptAndPosition(store_acceptance_sequence, store_position_db)
        self.restore = T_AcceptAndPosition(restore_acceptance_sequence, restore_position_db)

    @classmethod
    def from_MergedTrace(cls, merged_trace, si, acceptance_storing_f, restore_position_db, store_position_db):
        # storing of acceptance and input positions
        #
        if acceptance_storing_f:
            # acceptance sequence based on a state's acceptance
            store_acceptance_sequence = tuple(sorted( 
                x.acceptance_id 
                for x in merged_trace.acceptance_sequence_prototype() 
                if x.accepting_state_index == si))
        else:
            store_acceptance_sequence = ()

        # restoring of acceptance and input positions
        #
        from_graph = merged_trace.uniform_acceptance_sequence()
        if from_graph is None: 
            restore_acceptance_sequence = None
        else:
            restore_acceptance_sequence = tuple(x.acceptance_id for x in from_graph)

        return cls(store_acceptance_sequence, store_position_db, 
                   restore_acceptance_sequence, restore_position_db)

class TA_StateInfoDb(dict):
    """PURPOSE:

        map: state index --> brief information about a state's storing and restoring
                             of acceptance and input positions.
                             
    """
    def __init__(self, Iterable_Si_TA_StateInfo, AcceptanceConditionDb):
        dict.__init__(self, ((si, state_info) for si, state_info in Iterable_Si_TA_StateInfo))
        self.acceptance_condition_db = AcceptanceConditionDb

    @classmethod
    def from_Traces(cls, trace_result, PredecessorDb, ToDb):
        MergedTraceDb = dict((key, MergedTraces(trace_list)) 
                              for key, trace_list in trace_result.items())

        # map:  storing_si   --> map: acceptance_id --> target states in direction of restore
        _store_position_db = cls.__get_position_storing_db(MergedTraceDb, PredecessorDb, ToDb)

        # map:  restoring_si --> map: acceptance_id --> (transition_n since storing, 
        #                                                position storing state index set)
        _restore_position_db = cls.__get_position_restoring_db(MergedTraceDb)

        # list: indices of states that need to store accepance_id-s
        _acceptance_storing_si_set = cls.__get_acceptance_storing_si_set(MergedTraceDb)

        _iterable_si_state_info = (
            (si, TA_StateInfo.from_MergedTrace(paths_to_state, si, 
                                               si in _acceptance_storing_si_set,
                                               _restore_position_db[si],
                                               _store_position_db[si])) 
            for si, paths_to_state in MergedTraceDb.items())

        # map: acceptance_id --> acceptance_condition_set
        _acceptance_condition_db = cls.__get_acceptance_condition_db(MergedTraceDb)

        return TA_StateInfoDb(_iterable_si_state_info, _acceptance_condition_db)

    @staticmethod
    def __get_position_storing_db(MergedTraceDb, PredecessorDb, ToDb):
        def _target_states_in_direction_of_restore(position_storing_si, to_db, predecessor_si_list):
            """-- Only consider target states which guide to the 'position_restoring_si'.
               -- Do not store upon entry to state itself.
            """
            return [
                si for si in to_db[position_storing_si] 
                if si in predecessor_si_list and si != position_storing_si
            ]

        result = defaultdict(dict)
        for si, path_to_state in sorted(MergedTraceDb.items()):
            for x in path_to_state.positioning_info():
                if x.transition_n_since_positioning != E_TransitionN.VOID: continue
                # Request the storage of the position from related states.
                predecessor_of_restoring_si_list = PredecessorDb[si].union([si])
                for position_storing_si in x.positioning_state_index_set:
                    sub_db = result[position_storing_si]
                    if x.acceptance_id not in sub_db: sub_db[x.acceptance_id] = set()
                    sub_db[x.acceptance_id].update(
                        _target_states_in_direction_of_restore(position_storing_si, ToDb, 
                                                               predecessor_of_restoring_si_list))
        return result

    @staticmethod
    def __get_position_restoring_db(MergedTraceDb):
        result = {}
        for si, pts in MergedTraceDb.items():
            result[si] = dict((x.acceptance_id, T_RestorePosition(x.positioning_state_index_set, 
                                                                  x.transition_n_since_positioning))
                              for x in pts.positioning_info())
        return result

    @staticmethod
    def __get_acceptance_condition_db(MergedTraceDb):
        result = {}
        for path_to_state in MergedTraceDb.values():
            for x in path_to_state.acceptance_sequence_prototype():
                if x.acceptance_id in result:
                    assert result[x.acceptance_id] == x.acceptance_condition_set
                else:
                    result[x.acceptance_id] = x.acceptance_condition_set
        return result

    @staticmethod
    def __get_acceptance_storing_si_set(MergedTraceDb):
        # (*) Collect all states that need to store acceptance
        result = set()
        for si, pts in sorted(MergedTraceDb.items()):
            if pts.uniform_acceptance_sequence() is None:
                result.update(pts.accepting_state_index_list())
        return result
            
def do(SM, ToDB):
    """Analyze the state machine graph of 'SM'. Whenever the acceptance or the
    input position at drop-out can be pre-determined, it is spared to store
    and restore it.
    """
    trace_result = __do_core(SM, ToDB)
    return TA_StateInfoDb.from_Traces(trace_result, SM.get_predecessor_db(), ToDB)

## def DELETED_pseudo(SM, ToDB):
##     """Creates a 'TA_StateInfoDb' without any trace analysis. That is, at every
##     drop-out, acceptance and input positions are restored. Respectively, no 
##     storage of acceptance or input positions is spared.
##     """
##     def _get_acceptance_sequence(state):
##         return sorted(
##             cmd.acceptance_id()
##             for cmd in state.single_entry.get_iterable(SeAccept))
## 
##     def _get_acceptance_condition_db(SM):
##         return dict(
##             (cmd.acceptance_id(), cmd.acceptance_condition_set())
##             for state in SM.states.itervalues()
##             for cmd in state.single_entry.get_iterable(SeAccept))
## 
##     def _get_store_position_db(state, si, ToDb):
##         return dict(
##             (cmd.acceptance_id(), ToDb[si])
##             for cmd in state.single_entry
##             if    (cmd.__class__ == SeStoreInputPosition) \
##                or (cmd.__class__ == SeAccept and not cmd.restore_position_register_f()))
## 
##     def _get_general_store_information(SM, ToDb):
##         return dict((si, _get_store_position_db(state, si, ToDb))
##                     for si, state in SM.states.iteritems())
## 
##     def _get_general_position_restore_db(SM, all_store_position_db):
##         acceptance_id_to_storing_si_set_db = defaultdict(set) 
##         for si in SM.states:
##             for acceptance_id in all_store_position_db:
##                 acceptance_id_to_storing_si_set_db[acceptance_id].add(si)
## 
##         return dict(
##             (acceptance_id, 
##              T_RestorePosition(acceptance_id_to_storing_si_set_db[acceptance_id], 
##                                E_TransitionN.VOID))
##             for acceptance_id in sorted(SM.acceptance_id_set()))
## 
##     all_store_position_db       = _get_general_store_information(SM, ToDB)
## 
##     general_position_restore_db = _get_general_position_restore_db(SM,
##                                                                    all_store_position_db)
## 
##     _iterable_si_state_info = (
##         (si, TA_StateInfo(store_acceptance_sequence   = _get_acceptance_sequence(state),
##                           store_position_db           = all_store_position_db[si],
##                           restore_acceptance_sequence = None,
##                           restore_position_db         = general_position_restore_db))
##         for si, state in SM.states.iteritems())
## 
##     return TA_StateInfoDb(_iterable_si_state_info, 
##                           _get_acceptance_condition_db(SM))

def __do_core(SM, ToDB):
    """RETURNS: Acceptance trace database:

                map: state_index --> MergedTraces

    ___________________________________________________________________________
    This function walks down almost each possible path trough a given state
    machine.  During the process of walking down the paths it develops for each
    state its list of _Trace objects.
    ___________________________________________________________________________
    IMPORTANT:

    There is NO GUARANTEE that the paths from acceptance to 'state_index' or
    the paths from input position storage to 'state_index' are complete! The 
    calling algorithm must walk these paths on its own.

    This is due to a danger of exponential complexity with certain setups. Any
    path analysis is dropped as soon as a state is reached with an equivalent
    history.
    ___________________________________________________________________________
    """
    def print_path(x):
        print(x.state_index, " ", end=' ')
        if x.parent is not None: print_path(x.parent)
        else:                    print()

    class TraceFinder(TreeWalker):
        """Determines _Trace objects for each state. The heart of this function is
           the call to '_Trace.next_step()' which incrementally develops the 
           acceptance and position storage history of a path.

           Recursion Terminal: When state has no target state that has not yet been
                               handled in the 'path' in the same manner. That means,
                               that if a state appears again in the path, its trace
                               must be different or the recursion terminates.
        """
        def __init__(self, state_machine, ToDB):
            self.sm         = state_machine
            self.to_db      = ToDB
            self.result     = dict((i, []) for i in self.sm.states.keys())
            self.path       = []

            # Under some circumstances, the init state may accept!
            # (E.g. the appendix state machines of the 'loopers')
            TreeWalker.__init__(self)

        def on_enter(self, Args):
            PreviousTrace = Args[0]
            StateIndex    = Args[1]

            # (*) Update the information about the 'trace of acceptances'
            dfa_state = self.sm.states[StateIndex]

            if not self.path: trace = _Trace(self.sm.init_state_index, dfa_state)
            else:             trace = PreviousTrace.next_step(StateIndex, dfa_state) 

            target_index_list = self.to_db[StateIndex]

            # (*) Recursion Termination:
            #
            # If a state has been analyzed before with the same trace as result,  
            # then it is not necessary dive into deeper investigations again. All
            # of its successor paths have been walked along before. This catches
            # two scenarios:
            #   
            # (1) Loops: A state is reached through a loop and nothing 
            #            changed during the walk through the loop since
            #            the last passing.
            # 
            #            There may be connected loops, so it is not sufficient
            #            to detect a loop and stop.
            #
            # (2) Knots: A state is be reached through different branches.
            #            However, the traces through those branches are
            #            indifferent in their positioning and accepting 
            #            behavior. Only one branch needs to consider the
            #            subsequent states.
            #
            #     (There were cases where this blew the computation time
            #      see bug-2257908.sh in $QUEX_PATH/TEST).
            # 
            existing_trace_list = self.result.get(StateIndex) 
            if existing_trace_list:
                end_of_road_f = (len(target_index_list) == 0)
                for pioneer in existing_trace_list:
                    if not trace.is_equivalent(pioneer, end_of_road_f): 
                        continue
                    elif trace.has_parent(pioneer):
                        # Loop detected -- Continuation unnecessary. 
                        # Nothing new happened since last passage.
                        # If trace was not equivalent, the loop would have to be stepped through again.
                        return None
                    else:
                        # Knot detected -- Continuation abbreviated.
                        # A state is reached twice via two separate paths with
                        # the same positioning_states and acceptance states. The
                        # analysis of subsequent states on the path is therefore
                        # complete. Almost: There is no alternative paths from
                        # store to restore that must added later on.
                        return None

            # (*) Mark the current state with its acceptance trace
            self.result[StateIndex].append(trace)

            # (*) Add current state to path
            self.path.append(StateIndex)

            # (*) Recurse to all (undone) target states. 
            return [(trace, target_i) for target_i in target_index_list ]

        def on_finished(self, Args):
            # self.done_set.add(StateIndex)
            self.path.pop()

    trace_finder = TraceFinder(SM, ToDB)
    trace_finder.do((None, SM.init_state_index))

    return trace_finder.result

class _Trace(object):
    """
    An object of this class documents the impact of actions that happen
    along ONE specific path from the init state to a specific state. 
    ___________________________________________________________________________
    EXPLANATION:

    During a path from the init state to 'this state', the following things
    may happen or may have happened:

         -- The input position has been stored in a position register
            (for post context management or on accepting a pattern).

         -- A pattern has been accepted. Acceptance may depend on a
            pre-context being fulfilled.

    Storing the input position can be a costly operation. If the length of
    the path from storing to restoring can be determined from the number of
    transitions, then it actually does not have to be stored. Instead, it
    can be obtained by 'input position -= transition number since
    positioning.' In any case, the restoring of an input position is
    triggered by an acceptance event.

    Acceptance of a pattern occurs, if one drops out of a state, i.e. there
    are no further transitions possible. Later analysis will focus on these
    acceptance events. They are stored in a sorted member '.acceptance_trace'.

    The sort order of the acceptance trace reflects the philosophy of
    'longest match'. That, is that the last acceptance along a path has a
    higher precedence than an even higher prioritized pattern before. 
    Actually, all patterns without any pre-context remove any _AcceptInfo
    object that preceded along the path.

    For further analysis, this class provides:

         .acceptance_trace -- Sorted list of information about acceptances.

    During the process of building path traces, the function

         .next_step(...)

    is called. It assumes that the current object represents the path trace
    before 'this state'. Based on the given arguments to this function it 
    modifies itself so that it represents the trace for 'this_state'.

    ___________________________________________________________________________
    EXAMPLE:
    
    
        ( 0 )----->(( 1 ))----->( 2 )----->(( 3 ))----->( 4 ) ....
                    8 wins                 pre 4 -> 5 wins                    
                                           pre 3 -> 7 wins

    results in _Trace objects for the states as follows:

        State 0: has no acceptance trace, only '(no pre-context, failure)'.
        State 1: (pattern 8 wins, input position = current)
        State 2: (pattern 8 wins, input position = current - 1)
        State 3: (if pre context 4 fulfilled: 5 wins, input position = current)
                 (if pre context 3 fulfilled: 7 wins, input position = current)
                 (else,                       8 wins, input position = current - 2)
        State 4: (if pre context 4 fulfilled: 5 wins, input position = current - 1)
                 (if pre context 3 fulfilled: 7 wins, input position = current - 1)
                 (else,                       8 wins, input position = current - 3)
        ...
    ___________________________________________________________________________
    """
    __slots__ = ("__acceptance_trace",  # List of _AcceptInfo objects
                 "__storage_db",        # Map: acceptance_id --> _StoreInfo objects
                 "__parent", 
                 "__state_index", 
                 "__equivalence_hash", 
                 "__equivalence_hint", 
                 "__acceptance_trace_len",
                 "__storage_db_len")

    def __init__(self, InitStateIndex=None, InitState=None, HashF=True): 
        self.__acceptance_trace = [] 
        self.__storage_db       = {}
        if InitStateIndex is not None: # 'None' --> call from '.reproduce()'
            self.__next_step(InitStateIndex, InitState, UnconditionalAcceptFailureF=True)

        self.__state_index      = InitStateIndex
        self.__parent           = None
        self.__equivalence_hash = None
        self.__equivalence_hint = None
        if HashF:
            self.__compute_equivalence_hash()

    def reproduce(self, StateIndex):
        """Reproduce: Clone + update for additional StateIndex in the path."""
        result = _Trace(HashF=False) # We compute 'hash' later.
        result.__acceptance_trace = [ x.reproduce(StateIndex) for x in self.__acceptance_trace ]
        result.__storage_db       = dict(( (i, x.reproduce(StateIndex)) 
                                         for i, x in self.__storage_db.items()))
        result.__state_index      = StateIndex
        result.__parent           = self

        result.__compute_equivalence_hash()
        return result

    def next_step(self, StateIndex, dfa_state):
        """The present object of _Trace represents the history of events 
        along a path from the init state to the state BEFORE 'this state'.

        Applying the events of 'this state' on the current history results
        in a _Trace object that represents the history of events until
        'this state'.

        RETURNS: Altered clone of the present object.
        """
        # Some experimenting has shown that the number of unnecessary cloning,
        # i.e.  when there would be no change, is negligible. The fact that
        # '.path_since_positioning()' has almost always to be adapted,
        # makes selective cloning meaningless. So, it is done the safe way:
        # (update .path_since_positioning during 'reproduction'.)
        result = self.reproduce(StateIndex) # Always clone. 
        result.__next_step(StateIndex, dfa_state, UnconditionalAcceptFailureF=False)
        return result

    def __next_step(self, StateIndex, dfa_state, UnconditionalAcceptFailureF):
        """Update '.__acceptance_trace' and '.__storage_db' according to 
        occurring acceptances and store-input-position events.  Origins must 
        be sorted with the highest priority LAST, so that they will appear on 
        top of the acceptance trace list.
        """
        if UnconditionalAcceptFailureF:
            self.__acceptance_trace_add_at_front(SeAccept(E_IncidenceIDs.MATCH_FAILURE), 
                                                 StateIndex)

        for cmd in sorted(dfa_state.single_entry.get_iterable(SeAccept), 
                          key=lambda x: x.acceptance_id(), reverse=True):
            # Acceptance 
            self.__acceptance_trace_add_at_front(cmd, StateIndex)

        for cmd in sorted(dfa_state.single_entry.get_iterable(SeStoreInputPosition), 
                          key=lambda x: x.acceptance_id(), reverse=True):
            # Store Input Position Information
            self.__storage_db[cmd.acceptance_id()] = _StoreInfo([StateIndex], 0)

        assert len(self.__acceptance_trace) >= 1
        self.__compute_equivalence_hash()
        return self

    def __acceptance_trace_add_at_front(self, Op, StateIndex):
        """Assume that the 'Op' belongs to a state with index 'StateIndex' that
        comes after all states on the path before considered path.  Assume that 
        the 'Op' talks about 'acceptance'.
        """
        # If there is an unconditional acceptance, it dominates all previous 
        # occurred acceptances (philosophy of longest match).
        if not Op.acceptance_condition_set():
            del self.__acceptance_trace[:]

        # Input Position Store/Restore
        acceptance_id = Op.acceptance_id()
        if Op.restore_position_register_f():
            # Restorage of Input Position (Post Contexts): refer to the 
            # input position at the time when it was stored.
            entry                          = self.__storage_db[acceptance_id]
            path_since_positioning         = entry.path_since_positioning
            transition_n_since_positioning = entry.transition_n_since_positioning
        else:
            # Normally accepted patterns refer to the input position at 
            # the time of acceptance.
            path_since_positioning         = [ StateIndex ]
            transition_n_since_positioning = 0

        # Reoccurring information about an acceptance overwrites previous occurrences.
        for entry_i in (i for i, x in enumerate(self.__acceptance_trace) \
                        if x.acceptance_id == acceptance_id):
            del self.__acceptance_trace[entry_i]
            # From the above rule, it follows that there is only one entry per acceptance_id.
            break

        entry = _AcceptInfo(Op.acceptance_condition_set(), acceptance_id,
                            AcceptingStateIndex         = StateIndex, 
                            PathSincePositioning        = path_since_positioning, 
                            TransitionNSincePositioning = transition_n_since_positioning) 

        # Insert at the beginning, because what comes last has the highest
        # priority.  (Philosophy of longest match). The calling function must
        # ensure that for one step on the path, the higher prioritized patterns
        # appear AFTER the lower prioritized ones.
        self.__acceptance_trace.insert(0, entry)

    @property 
    def state_index(self):  
        return self.__state_index

    @property
    def parent(self): 
        return self.__parent

    def has_parent(self, Candidate):
        parent = self.__parent
        while parent is not None:
            if id(parent) == id(Candidate): return True
            parent = parent.parent
        return False

    @property
    def acceptance_trace(self):
        return self.__acceptance_trace

    def get(self, AccConditionID):
        """RETURNS: _AcceptInfo object for a given AccConditionID."""
        for entry in self.__acceptance_trace:
            if AccConditionID in entry.acceptance_condition_set: return entry
        return None

    def __compute_equivalence_hash(self):
        """Computes a numeric value 'self.__equivalence_hash' to identify the
           current setting of the object.  This hash value may be used in a
           necessary condition to compare for 'equivalence' with another
           object. That is, if the hash values of two objects are different,
           the objects MUST be different. If they are the same, a detailed
           check must investigate if they are equivalent or not. See function
           'is_equivalent()' which assumes that the '__equivalence_hash' has been
           computed.
        """
        # New Faster Try: (Must be Double Checked!)
        #        eq = hash(0x5a5a5a5a)
        #        for x in self.__acceptance_trace:
        #            eq ^= hash(x.acceptance_id)
        #            eq ^= hash(x.accepting_state_index)
        #            eq ^= hash(x.positioning_state_index)
        #            eq ^= hash(x.transition_n_since_positioning)
        #
        #        for acceptance_id, info in sorted(self.__storage_db.iteritems()):
        #            eq ^= hash(x.loop_f)
        #            eq ^= hash(x.transition_n_since_positioning)
        data = []
        for x in self.__acceptance_trace:
            if isinstance(x.acceptance_id, int):                  data.append(x.acceptance_id)
            elif x.acceptance_id == E_IncidenceIDs.MATCH_FAILURE:  data.append(0x5A5A5A5A)
            else:                                                  data.append(0xA5A5A5A5)
            if isinstance(x.accepting_state_index, int):          data.append(x.accepting_state_index)
            else:                                                  data.append(0x5B5B5B5B)
            if isinstance(x.positioning_state_index, int):        data.append(x.positioning_state_index)
            else:                                                  data.append(0x5C5C5C5C)
            if isinstance(x.transition_n_since_positioning, int): data.append(x.transition_n_since_positioning)
            else:                                                  data.append(0x5D5D5D5D)

        for acceptance_id, info in sorted(self.__storage_db.items()):
            if info.loop_f:                                             data.append(0x48484848)
            elif isinstance(info.transition_n_since_positioning, int): data.append(info.transition_n_since_positioning)
            else:                                                       data.append(0x4D4D4D4D)

        self.__equivalence_hash = crc32(str(data).encode())
        # HINT: -- One single acceptance on current state.
        #       -- No restore of position from previous states.
        #       => Store the acceptance_id of the winning pattern.
        # 
        # This hint may be used for a SUFFICENT condition to determine 
        # equivalence, IF the state has no subsequent transitions. Because,
        # then there is no restore involved and the __storage_db can be
        # neglected.
        if len(self.__acceptance_trace) == 1:
            x = self.__acceptance_trace[0]
            if     x.transition_n_since_positioning == 0               \
               and x.positioning_state_index == x.accepting_state_index:
                # From:    transition_n_since_positioning == 0
                # Follows: x.accepting_state_index == current state index
                self.__equivalence_hint = x.acceptance_id
            else:
                self.__equivalence_hint = None
        else:
            self.__equivalence_hint = None
        self.__acceptance_trace_len = len(self.__acceptance_trace)
        self.__storage_db_len       = len(self.__storage_db)

    def is_equivalent(self, Other, EndOfRoadF=False):
        """This function determines whether the path trace described in Other is
           equivalent to this trace. 
        """
        if self.__equivalence_hash != Other.__equivalence_hash:           return False

        if self.__equivalence_hint is not None:
            if self.__equivalence_hint == Other.__equivalence_hint:       return True

        if   self.__acceptance_trace_len != Other.__acceptance_trace_len: return False
        elif self.__storage_db_len       != Other.__storage_db_len:       return False

        for x, y in zip(self.__acceptance_trace, Other.__acceptance_trace):
            if   x.acceptance_id                  != y.acceptance_id:                  return False
            elif x.accepting_state_index          != y.accepting_state_index:          return False
            elif x.positioning_state_index        != y.positioning_state_index:        return False
            elif x.transition_n_since_positioning != y.transition_n_since_positioning: return False

        # When there are no further transitions to other states, then no restore
        # may happen. Then, considering '__storage_db' is not necessary.
        if not EndOfRoadF:
            for x_pattern_id, x in self.__storage_db.items():
                y = Other.__storage_db.get(x_pattern_id)
                if   y is None:                                              return False
                elif x.loop_f                  != y.loop_f:                  return False
                elif x.positioning_state_index != y.positioning_state_index: return False

        #print "## self.acceptance:", self.__acceptance_trace
        #print "## self.storage:", self.__storage_db
        #print "## Other.acceptance:", Other.__acceptance_trace
        #print "## self.storage:", self.__storage_db
        #print "## Other.storage:", Other.__storage_db
        #print "#TRUE", Other
        return True

    def __eq__(self, Other):
        if self.__acceptance_trace != Other.__acceptance_trace: return False
        if len(self.__storage_db)  != len(Other.__storage_db):  return False

        for acceptance_id, entry in self.__storage_db.items():
            other_entry = Other.__storage_db.get(acceptance_id)
            if other_entry is None:                                return False
            if not entry.is_equal(Other.__storage_db[acceptance_id]): return False
        
        return True

    def __ne__(self, Other):
        return not (self == Other)

    def __repr__(self):
        return "".join([repr(x) for x in self.__acceptance_trace]) + "".join([repr(x) for x in self.__storage_db.items()])

class _StoreInfo(object):
    """
    Informs about a 'positioning action' that happened during the walk
    along a specific path from init state to 'this state'. 
    
    Used in function '_Trace.next_step()'.
    ___________________________________________________________________________
    EXPLANATION:

    A 'positioning action' is the storage of the current input position 
    into a dedicated position register. Objects of class '_StoreInfo'
    are stored in dictionaries where the key represents the pattern-id
    is at the same time the identifier of the position storage register.
    (Note, later the position register is remapped according to required
     entries.)

    'This state' means the state where the trace lead to. 

    The member '.path_since_positioning' gets one more state index appended
    at each transition along a path. 
    
    If a loop is detected '.transition_n_since_positioning' returns
    'E_TransitionN.VOID'.

    The member '.positioning_state_index' is the state where the positioning
    happend. If there is a loop along the path from '.positioning_state_index'
    to 'this state, then the '.transition_n_since_positioning' is set to 
    'E_TransitionN.VOID' (see comment above).

    ___________________________________________________________________________
    .path_since_positioning  -- List of indices of states which have been
                                passed from the storage of input position
                                to this state.
    ___________________________________________________________________________
    """
    __slots__ = ('path_since_positioning', '__transition_n_since_positioning', '__loop_f')
    def __init__(self, PathSincePositioning, TransitionNSincePositioning=None):
        self.path_since_positioning = PathSincePositioning
        if TransitionNSincePositioning is None:
            if len(PathSincePositioning) != len(set(PathSincePositioning)):
                self.__loop_f                         = True 
                self.__transition_n_since_positioning = E_TransitionN.VOID
            else:
                self.__loop_f                         = False
                self.__transition_n_since_positioning = len(PathSincePositioning) - 1
        else:
            if TransitionNSincePositioning == E_TransitionN.VOID:
                self.__loop_f                         = True
            else:
                self.__loop_f                         = False
            self.__transition_n_since_positioning = TransitionNSincePositioning

    def reproduce(self, StateIndex):
        """Reproduce: Clone + update for additional StateIndex in the path."""
        path_since_positioning         = copy(self.path_since_positioning)
        transition_n_since_positioning = self.get_transition_n_since_positioning_update(StateIndex)
        path_since_positioning.append(StateIndex)

        return _StoreInfo(path_since_positioning, transition_n_since_positioning)

    def get_transition_n_since_positioning_update(self, StateIndex):
        """RETURNS: Value of 'transition_n_since_positioning' when 'StateIndex'
                    is put on the path.
        """
        if      StateIndex in self.path_since_positioning \
            and self.__transition_n_since_positioning != E_TransitionN.LEXEME_START_PLUS_ONE:
            return E_TransitionN.VOID

        elif isinstance(self.__transition_n_since_positioning, int):
            return self.__transition_n_since_positioning + 1

        else:
            return self.__transition_n_since_positioning

    @property
    def loop_f(self):                         
        # NOT: return self.__transition_n_since_positioning == E_TransitionN.VOID
        #      because the comparison is much slower, then returning simply a boolean.
        # THIS FUNCTION MAY BE CALLED EXTENSIVELY!
        return self.__loop_f

    @property
    def transition_n_since_positioning(self): 
        return self.__transition_n_since_positioning

    @property
    def positioning_state_index(self):
        return self.path_since_positioning[0]

    def is_equal(self, Other):
        return     self.transition_n_since_positioning == Other.transition_n_since_positioning \
               and self.positioning_state_index        == Other.positioning_state_index

    def __repr__(self):
        txt = ["---\n"]
        txt.append("    .path_since_positioning         = %s\n" % repr(self.path_since_positioning))
        return "".join(txt)

class _AcceptInfo(_StoreInfo):
    """
    Information about the acceptance and input position storage behavior in 
    a state which is a result of events that happened before on a specific path 
    from the init state to 'this_state'.
    ___________________________________________________________________________
    EXPLANATION:
    
    Acceptance of a pattern is something that occurs in case that the 
    state machine can no further proceed on a given input (= philosophy
    of 'longest match'), i.e. on 'drop-out'. '_AcceptInfo' objects tell 
    about the acceptance of a particular pattern (given by '.acceptance_id').
    
    .acceptance_id              -- Identifies the pattern that is concerned.
                             
    .acceptance_condition_set   -- if none (== empty), then '.acceptance_id' is
                                always accepted. If not, then the pre-context
                                must be checked before the pattern can be 
                                accepted.
                             
    .accepting_state_index   -- Index of the state that caused the acceptance 
                                of the pattern somewhere before on the path.
                                It may, as well be 'this state'.
    
    [from _StoreInfo]

    .path_since_positioning  -- List of indices of states which have been
                                passed from the storage of input position
                                to this state.
    ___________________________________________________________________________
    """
    __slots__ = ("acceptance_condition_set", 
                 "acceptance_id", 
                 "accepting_state_index") 

    @typed(AccConditionSet=tuple)
    def __init__(self, AccConditionSet, AcceptanceID, 
                 AcceptingStateIndex, PathSincePositioning, 
                 TransitionNSincePositioning): 
        self.acceptance_condition_set = AccConditionSet
        self.acceptance_id            = AcceptanceID
        self.accepting_state_index    = AcceptingStateIndex

        if self.acceptance_id == E_IncidenceIDs.MATCH_FAILURE:
            transition_n_since_positioning = E_TransitionN.LEXEME_START_PLUS_ONE
        else:
            transition_n_since_positioning = TransitionNSincePositioning

        _StoreInfo.__init__(self, PathSincePositioning, transition_n_since_positioning)

    def reproduce(self, StateIndex):
        """Reproduce: Clone + update for additional StateIndex in the path."""
        path_since_positioning         = copy(self.path_since_positioning)
        transition_n_since_positioning = self.get_transition_n_since_positioning_update(StateIndex)
        path_since_positioning.append(StateIndex)
        result = _AcceptInfo(copy(self.acceptance_condition_set), 
                             self.acceptance_id, 
                             self.accepting_state_index, 
                             path_since_positioning, 
                             transition_n_since_positioning) 
        return result

    @property
    def positioning_state_index(self):
        return self.path_since_positioning[0]

    def is_equal(self, Other):
        if   self.acceptance_condition_set       != Other.acceptance_condition_set:       return False
        elif self.acceptance_id                  != Other.acceptance_id:                  return False
        elif self.accepting_state_index          != Other.accepting_state_index:          return False
        elif self.transition_n_since_positioning != Other.transition_n_since_positioning: return False
        elif self.positioning_state_index        != Other.positioning_state_index:        return False
        return True

    def __eq__(self, Other):
        return self.is_equal(Other)

    def __repr__(self):
        txt = ["---\n"]
        txt.append("    .acceptance_condition_set                 = %s\n" % repr(self.acceptance_condition_set))
        txt.append("    .acceptance_id                     = %s\n" % repr(self.acceptance_id))
        txt.append("    .transition_n_since_positioning = %s\n" % repr(self.transition_n_since_positioning))
        txt.append("    .accepting_state_index          = %s\n" % repr(self.accepting_state_index))
        txt.append("    .positioning_state_index        = %s\n" % repr(self.positioning_state_index))
        txt.append(_StoreInfo.__repr__(self))
        return "".join(txt)



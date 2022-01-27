# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# See also Power set construction: "https://en.wikipedia.org/wiki/Powerset_construction"
#
from   quex.engine.state_machine.state.target_map     import TargetMap
from   quex.engine.state_machine.state.target_map_ops import get_elementary_trigger_sets

def do(SM, CloneF=True):
    """Creates a deterministic finite automaton (DFA) from a state machine 
    which may be a NFA (non-deterministic finite automaton). 
    
    This is a generalized version of the 'subset construction' algorithm. Where
    subsection construction focuses on letters of an alphabet for the
    investigation of transitions, this algorithm focuses on elementary trigger
    sets. A very good description of the subset construction algorithm can be
    found in 'Engineering a Compiler' by Keith Cooper.

    TODO: Identify places in the code, that can actually renounce on 'CloneF=True'.
    """
    if CloneF: result = SM.clone()
    else:      result = SM
    _combine_all_epsilon_closures(result)

    worklist   = list(result.states.keys())
    closure_db = ClosureDb()

    while worklist:
        # 'start_state_index' is the index of an **existing** state in the state machine.
        # It was either created above, in DFA's constructor, or as a target
        # state index.
        si    = worklist.pop()
        state = result.states[si]

        if not state.target_map.ambiguities_possible(): continue

        # Compute the elementary trigger sets together with the epsilon closure 
        # of target state combinations that they trigger to. In other words: 
        # find the ranges of characters where the state triggers to a unique state 
        # combination. E.g:
        #            Range        Target DFA_State Combination 
        #            [0:23]   --> [ State1, State2, State10 ]
        #            [24:60]  --> [ State1 ]
        #            [61:123] --> [ State2, State10 ]
        #
        new_target_map = TargetMap()
        elementary_trigger_set_infos = get_elementary_trigger_sets(state.target_map)
        for target_si_closure, trigger_set in elementary_trigger_set_infos.items():
            assert type(target_si_closure) == tuple
            if trigger_set.is_empty(): continue

            target_state_index, \
            original_target_si_closure = closure_db.get_target_state_index(target_si_closure)

            if target_state_index is None:
                target_state_index = result.create_new_state_from_closure(original_target_si_closure)
                closure_db.enter(target_state_index, original_target_si_closure)
                worklist.append(target_state_index)

            new_target_map.add_transition(trigger_set, target_state_index)

        state.set_target_map(new_target_map)

    return closure_db.remove_orphaned_states(result)

class ClosureDb:
    def __init__(self):
        self.__closure_db = {}
        self.__expand_db  = {}

    def enter(self, TargetSi, OrigTargetSiClosure):
        self.__closure_db[OrigTargetSiClosure] = TargetSi
        self.__expand_db[TargetSi]             = OrigTargetSiClosure

    def get_target_state_index(self, RawSiClosure):
        assert RawSiClosure
        original_si_closure = self.__originate(RawSiClosure)
        if len(original_si_closure) == 1: si = RawSiClosure[0]
        else:                             si = self.__closure_db.get(original_si_closure)
        return si, original_si_closure

    def remove_orphaned_states(self, result):
        """TODO: Develop a 'delete_orphaned_states' version that only works on the
                 superset of the state indices in union(self.__expand_db.values()).
                 => Computational performance increase!

        A state that is absorbed into a combined state may loose all its transitions
        to it. If so, it is orphan and can be removed. 
        The target states of an orphaned state still have their transitions from
        the combined state, at least. Such a target state can only become orphan
        if it is absorbed into a combined state.

        => Only those states can possibly be orphans which are present in a closure.
           That is, THERE ARE NO ORPHANS EXCEPT IN 'union(self.__expand_db.values())'.

            (1) candidates = union(self.__expand_db.values())
        .-->(2) remainder = copy(candidates)
        |       for state in result.states:
        |           remainder.difference_update(state.transition_map.get_map().keys())
        |       => remainder are definitely 'real orphans'
        |   (3) remove orphan states
        '---(4) repeat until no new deletions
        """
        result.delete_orphaned_states()
        return result

    def __originate(self, SiClosure):
        """RETURNS: Tuple that only contains state indices which belong to the
                    original state machine.

        RECURSON IS NOT NECESSARY, since only those closures are entered which are
        original.
        """
        new_closure = []
        for si in SiClosure:
            expansion = self.__expand_db.get(si)
            if not expansion: 
                new_closure.append(si)
            else:
                # No recursion required
                ## assert set(expansion).isdisjoint(self.__expand_db.keys())
                new_closure.extend(expansion)
        return tuple(sorted(set(new_closure)))

def _combine_all_epsilon_closures(sm):
    """For any state that inhabits epsilon transitions, generate a new state
    from the states of its epsilon closure. The original state is removed.
    All target state indices are adapted.
    """
    pure_epsilon_state_set = sm.get_pure_epsilon_state_set()
    epsilon_closure_db     = sm.epsilon_closure_db()
    replacement_db = {}
    for si, etsi_set in epsilon_closure_db.items():
        if si in pure_epsilon_state_set: continue
        replacement_db[si] = sm.create_new_state_from_closure(etsi_set, 
                                                              RemoveEpsilonTansitionsF=True)

    # Delete only after all replacement states have been created.
    for si, etsi_set in epsilon_closure_db.items():
        del sm.states[si]

    sm.replace_target_indices(replacement_db)
    if sm.init_state_index in replacement_db:
        sm.init_state_index = replacement_db[sm.init_state_index]




# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: Stem and Branches

This module prunes DFAs with respect to the set of 'front acceptance states'.
A front acceptance state is an acceptance state which can be reached without
stepping over any other acceptance state.

Stem: Is the graph of the state machine starting from the initial state until
      a front acceptance state is reached. The acceptance state is overtaken,
      but none of its transitions.

Branch: All graphs from one acceptance state until another acceptance state
      is reached.
      
A DFA has, obviously, only one head but potentially more than one tail. 
"""
from   quex.engine.state_machine.core                     import DFA
import quex.engine.state_machine.construction.parallelize as     parallelize

def stem(Dfa):
    """RETURNS: DFA consisting only of branches until the first acceptance 
                state.
    """
    return __clone_until_acceptance(Dfa, Dfa.init_state_index)

def crown(Dfa):
    """RETURNS: DFA consisting of all branchest starting from any acceptance 
                state.
    """
    branch_list = __all_paths_between_acceptance_states(Dfa)
    if not branch_list: return DFA.Empty()
    else:               return parallelize.do(branch_list)

def __all_paths_between_acceptance_states(Dfa):
    """Generates for each front acceptance state a copy of the complete
    graph which can be reached inside 'Dfa' starting from it until the next
    acceptance state.

    RETURNS: List of DFAs containing a tail for each found acceptance states.
    """
    def _get_branch(Dfa, acceptance_si):
        result = Dfa.clone_subset(acceptance_si, Dfa.get_successors(acceptance_si))

        # Clone acceptance state as init state, which does not accept.
        # Take over all transitions of the acceptance state.
        new_state = result.get_init_state().clone()
        new_state.set_acceptance(False)
        result.set_new_init_state(new_state)

        # Original acceptance only remains in place, if it is the target of a 
        # transition.
        if not result.has_transition_to(acceptance_si):
            result.delete_state(acceptance_si)
        return result

    return [ 
        _get_branch(Dfa, acceptance_si) 
        for acceptance_si in Dfa.acceptance_state_index_list() 
    ]

def __clone_until_acceptance(Dfa, StartSi):
    """Make a new DFA from the graph between the given 'StartSi' to the 
    until an acceptance state is reached. Walks from a given 'StartSi'
    along all paths until an acceptance state is reached.

    RETURNS: DFA containing the graph.
    """
    result = DFA(InitStateIndex = StartSi,
                 AcceptanceF    = Dfa.states[StartSi].is_acceptance())

    work_set = set([StartSi])
    done_set = set([StartSi])
    orphans_possible_f = False
    while work_set:
        si = work_set.pop()
        state = Dfa.states[si]
        done_set.add(si)

        if state.is_acceptance(): 
            target_si_iterable = []
            result.states[si]  = state.clone()
            result.states[si].target_map.clear()
            orphans_possible_f = True 
        else:
            result.states[si]  = state
            target_si_iterable = state.target_map.get_target_state_index_list()

        work_set.update(
            target_si
            for target_si in target_si_iterable if target_si not in done_set
        )

    return result.clone()


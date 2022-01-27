# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""Algebraic relations:

       reverse(reverse(P)) == P
       reverse(\\Universe) == \\Universe
       reverse(\Empty)     == \Empty

       reverse(union(P, Q))        == union(reverse(P), reverse(Q))
       reverse(intersection(P, Q)) == intersection(reverse(P), reverse(Q))
"""
from   quex.engine.state_machine.state.single_entry   import SeAccept
from   quex.engine.state_machine.core                 import DFA
import quex.engine.state_machine.algorithm.beautifier as beautifier

def do(SM, EnsureDFA_f=True):
    result = __do(SM)
    if EnsureDFA_f: return beautifier.do(result)
    else:           return result

def __do(SM):
    """Creates a state machine that matches the reverse of what 'SM' matches.
    """
    original_acceptance_state_index_list = SM.acceptance_state_index_list()

    if not original_acceptance_state_index_list:
        # If there is no acceptance state in a state machine, the state machine
        # cannot match any pattern, it is equivalent to '\Empty'. The reverse
        # of \Empty is \Empty.
        return DFA.Empty()

    # Ensure that each target state index has a state inside the state machine
    result = DFA(InitStateIndex=SM.init_state_index)
    for state_index in list(SM.states.keys()):
        result.create_new_state(StateIdx=state_index)

    for state_index, state in list(SM.states.items()):
        for target_state_index, trigger_set in list(state.target_map.get_map().items()):
            result.states[target_state_index].add_transition(trigger_set.clone(), state_index)

        for target_state_index in state.target_map.get_epsilon_target_state_index_list():
            result.states[target_state_index].target_map.add_epsilon_target_state(state_index)

    # -- copy all origins of the original state machine
    # -- We need to cancel any acceptance, because the reversed engine now starts
    #    from a combination of the acceptance states and ends at the initial state.
    for state_index, state in list(SM.states.items()):
        result.states[state_index].single_entry.set(
            cmd.clone() for cmd in state.single_entry
                if cmd.__class__ != SeAccept
        ) # deepcopy implicit

    # -- only the ORIGINAL initial state becomes an acceptance state (end of reversed)
    result.states[SM.init_state_index].set_acceptance(True)

    # -- setup an epsilon transition from an new init state to all previous 
    #    acceptance states.
    new_init_state_index = result.create_new_init_state() 
    for state_index in original_acceptance_state_index_list:
        result.add_epsilon_transition(new_init_state_index, state_index)        

    # -- for uniqueness of state ids, clone the result
    return result.clone()    
    

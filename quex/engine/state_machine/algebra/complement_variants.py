# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.index                as state_machine_index
import quex.engine.state_machine.algorithm.beautifier as beautifier
from   copy import deepcopy

def acceptance_flush(Dfa):
    """Turns non-acceptance states into acceptance states and leaves 
    acceptance states as they are.

    RETURNS: DFA which matches all possible paths in the DFA. This 
             includes the path of zero length and paths which do not
             end at an acceptance state.
    """
    result = Dfa.clone()
    for state in result.states.values():
        state.set_acceptance(True)
    result.clean_up()
    return beautifier.do(result)

def acceptance_inversion(Dfa):
    """Turns acceptance states into non-acceptance states and vice versa.

    RETURNS: DFA which matches all possible paths in the DFA, except for
             those which end at an acceptance state.
    """
    result = Dfa.clone()
    for si, state in result.states.items():
        state.set_acceptance(not state.is_acceptance())
    result.clean_up()
    return result

def infimum_deviant(Dfa):
    """RETURNS: Matches as soon as lexeme deviates from Dfa.

    Contrary to the algebraic 'not', this not does not eat until infinity
    upon deviation. 
    """
    assert Dfa.is_DFA_compliant()

    result = Dfa.clone()
    original_acceptance_si_list = result.acceptance_state_index_list()
    new_acceptance_si           = state_machine_index.get()
    for state in result.states.values():
        # drop-out --> transition to 'Accept-All' state.
        drop_out_trigger_set = state.target_map.get_drop_out_trigger_set_union()
        if not drop_out_trigger_set.is_empty():
            state.add_transition(drop_out_trigger_set, new_acceptance_si)

    new_acceptance_si = result.create_new_state(AcceptanceF=True, 
                                                StateIdx=new_acceptance_si) 

    # Remove all original acceptance states
    key_list = list(result.states.keys())
    for si in key_list:
        if   si == result.init_state_index:     
            # Never delete the initial state
            result.states[si].set_acceptance(False)
        elif si in original_acceptance_si_list: 
            del result.states[si]

    # 'result.delete_hopeless_states()' is not enough.
    # There might be an acceptance state pending in the void.
    result.clean_up()
    return result.clone()


# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
r"""PURPOSE: Complement of pattern: '\Not{P}'

   => Matches every lexeme that P does not match.

ALGEBRAIC RELATIONS:

    union(complement(P), P)        == All
    intersection(complement(P), P) == Empty
    complement(complement(P))      == P

(C) 2013-2016 Frank-Rene Schaefer
"""
from quex.engine.misc.interval_handling import NumberSet_All
from copy                               import deepcopy

def do(SM):
    """RETURNS: A state machines that matches anything which is 
                not matched by SM.

        (1a) Non-Acceptance           --> Acceptance
        (1b) Acceptance               --> Non-Acceptance
        (2a) Transition to Accept-all --> Drop-out
        (2b) Drop-out                 --> Transition to Accept-all

       NOTE: This function produces a finite state automaton which
             is not applicable by itself. It would eat ANYTHING
             from a certain state on.
    """
    assert SM.is_DFA_compliant()

    result = deepcopy(SM) # Not clone, state indices MUST be SAME!

    accept_on_drop_out_si = result.create_new_state(AcceptanceF=True) 
    result.add_transition(accept_on_drop_out_si, NumberSet_All(), 
                          accept_on_drop_out_si)

    for state_index, state in SM.states.items():
        result_state = result.states[state_index]

        # drop-out --> transition to 'Accept-All' state.
        drop_out_trigger_set = state.target_map.get_drop_out_trigger_set_union()
        if not drop_out_trigger_set.is_empty():
            result_state.add_transition(drop_out_trigger_set, 
                                        accept_on_drop_out_si)
        # All other transitions are forgotten in result

    # acceptance state     --> non-acceptance state.
    # non-acceptance state --> acceptance state.
    for state_index, state in SM.states.items():
        #if state_index == SM.init_state_index: continue
        # deepcopy --> use same state indices in SM and result
        result_state = result.states[state_index]
        result_state.set_acceptance(not state.is_acceptance())

    # 'result.delete_hopeless_states()' is not enough.
    # There might be an acceptance state pending in the void.
    result.clean_up()
    return result.clone()


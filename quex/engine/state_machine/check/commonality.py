# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.engine.state_machine.core import DFA
from quex.constants                 import E_Commonality
from quex.engine.state_machine.state.target_map_ops import get_intersection_line_up


def do(A, B):
    if isinstance(A, DFA):
        assert isinstance(B, DFA)
        return __core(A, B)

    assert not isinstance(B, DFA)

    # If pre-conditions differ, they cannot have any commonality
    pre_result = E_Commonality.NONE
    if A.pre_context_trivial_begin_of_line_f != B.pre_context_trivial_begin_of_line_f:
        # One depends on begin-of-line, the other doesn't => no commonality
        pre_result = E_Commonality.NONE

    elif (A.pre_context_sm_to_be_reversed is not None) != (B.pre_context_sm_to_be_reversed is not None):
        # One depends on pre-conditions, the other doesn't => no commonality
        pre_result = E_Commonality.NONE

    elif A.pre_context_sm_to_be_reversed is not None:
        assert B.pre_context_sm_to_be_reversed is not None
        # Both depend on pre-conditions: Are there commonalities in the pre-conditions?
        pre_result = __core(A.pre_context_sm_to_be_reversed, B.pre_context_sm_to_be_reversed)
    else:
        pre_result = E_Commonality.BOTH

    if pre_result == E_Commonality.NONE: return E_Commonality.NONE

    # NOTE: Post-conditions do not change anything, since they match only when the whole
    #       lexeme has matched (from begin to end of post condition). Post-conditions only
    #       tell something about the place where the analyzer returns after the match.
    result = __core(A.borrow_sm(), B.borrow_sm())

    if result == E_Commonality.NONE: return E_Commonality.NONE

    if   pre_result == E_Commonality.BOTH:   return result
    elif pre_result == result: return result 
    else:                      return E_Commonality.NONE

def __core(A, B):
    """Checks whether one state machine may match a lexeme that is the START of
    a lexeme that is matched by the other state machine. For example:

          A:  [a-z]{5}
          B:  otto

    B matches 'otto', A does not. However, A would match 'ottoy' would which
    contains the pattern that B can match.

    A is not a superset, since it does not match everything that B matches. It
    happens only that A and B have a commonality.  

    RETURNS:  NONE    if no commonalities exist.
              BOTH    if both ACCEPT a common lexeme.
              A_IN_B  if A has a pattern that lies inside the state machine of B.
              B_IN_A  if B has a pattern that lies inside the state machine of A.
    """
    work_list = [(A.init_state_index, B.init_state_index)]
    a_done_set = set()
    b_done_set = set()
    while work_list:
        A_si, B_si = work_list.pop()

        A_state = A.states[A_si]
        B_state = B.states[B_si]

        if A_state.is_acceptance(): 
            if B_state.is_acceptance(): return E_Commonality.BOTH    # both share a commonality
            else:                       return E_Commonality.A_IN_B  # path in A is a path in B
        elif B_state.is_acceptance():   return E_Commonality.B_IN_A  # path in B is a path in A

        # Follow the path of common trigger sets
        line_up = get_intersection_line_up((A_state.target_map, B_state.target_map))
        for target_state_setup, trigger_set in line_up.items():
            A_target_si, B_target_si = target_state_setup
            if A_target_si in a_done_set and B_target_si in b_done_set: continue

            work_list.append((A_target_si, B_target_si))

        a_done_set.add(A_si)
        b_done_set.add(B_si)

    return E_Commonality.NONE


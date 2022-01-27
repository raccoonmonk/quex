# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# PURPOSE: Investigate the ability of one DFA 'eating' into what may be 
#          matched by another. 
#
#-------------------------------------------------------------------------------
# Definitions:
#
# Start(X) = set of starting sequences of X:
#            Non-empty sequence that walks 
#            from INIT STATE in 'X' along the graph of 'X' until some state 'xi'.
#
# Match(X) = set of lexemes that match X from INIT STATE to ACCEPTANCE
#
# End(X)   = set of terminating sequences of X:
#            Non-empty sequence that walks 
#            from some state 'xi' along the graph of 'X' until an ACCEPTANCE STATE.
#
# In(X)    = set of lexemes that match along a path in 'X'.
#-------------------------------------------------------------------------------
#
# inside_A_matches_B(A,B):    Intersection(In(A), Match(B)) not empty
#
#     Is  there a sequence matched by 'B' that walks inside the graph of 'A'?
#
# ending_A_beginning_B(A, B): Intersection(Begin(B), End(A)) not empty 
#
#     Is there a beginning sequence of 'B' that is terminating sequence of 'A'?
#
# TODO: The algorithms are *symmetric*. It may be worth to investigate the
#       exact relationship and rename the functions. 
#______________________________________________________________________________

from quex.engine.state_machine.state.target_map_ops import get_intersection_line_up

def inside_A_match_B(A, B):
    """RETURNS: True, if 'A' swallows something that can be matched by 'B'.
                False, else.

    If there is a lexeme matched by 'B' which could be run-over by 'A' than 
    this function returns True. 

    EXAMPLE:

    A: "elfrieda" B: "frieda": True
    
       The lexeme 'frieda' can walk in 'A' starting after 'el'. 

    A: "friedhelm", B: "frieda": False
    
        The lexeme 'frieda' is not present in 'A'. 

    A: "friedhelm", B: "helmut": False
    
        The lexeme 'helmut' is not present in 'A'. 
    """
    return any(__walk_inside_A_match_B(A, si, B) for si in A.states)

def ending_A_beginning_B(A, B):
    """RETURNS: True, if 'A' may eat into something that could be the beginning of 'B'.
                False, else.

    A: "elfrieda" B: "frieda": True
    
       The lexeme 'frieda' is the end of 'A' and 'eats' into 'B'.

    A: "friedhelm", B: "ried": False
    
        The lexeme 'ried' is present in 'A' but it is not a terminating sequence.

    A: "friedhelm", B: "helmut": True
    
        The lexeme 'helm' is the beginning of 'B' and at the same time 
        a terminating sequence of 'A'.
    """
    return any(__walk_ending_A_beginning_B(A, si, B) 
               for si, state in A.states.items() if not state.is_acceptance())

def __walk_inside_A_match_B(A, A_StartIdx, B):
    """RETURNS: True, if starting from A and B can walk together along their
                      graphs on the same character sets until 'B' reaches an 
                      acceptance state.
                False, else.
    """
    work_list = [(A_StartIdx, B.init_state_index)]
    a_done_set = set()
    b_done_set = set()
    while work_list:
        A_si, B_si = work_list.pop()

        A_state = A.states[A_si]
        B_state = B.states[B_si]

        # If 'B' reaches any acceptance state, then at least one
        # lexeme completely walks inside of 'A'
        if B_state.is_acceptance(): return True

        # Follow the path of common trigger sets
        line_up = get_intersection_line_up((A_state.target_map, B_state.target_map))
        for target_state_setup, trigger_set in line_up.items():
            A_target_si, B_target_si = target_state_setup
            if A_target_si in a_done_set and B_target_si in b_done_set: continue

            work_list.append((A_target_si, B_target_si))

        a_done_set.add(A_si)
        b_done_set.add(B_si)

    return False

def __walk_ending_A_beginning_B(A, A_StartIdx, B):
    """RETURNS: True, if starting from A and B can walk together along their
                      graphs on the same character sets until 'B' reaches an 
                      acceptance state.
                False, else.
    """
    work_list = [(A_StartIdx, B.init_state_index)]
    a_done_set = set()
    b_done_set = set()
    while work_list:
        A_si, B_si = work_list.pop()

        A_state = A.states[A_si]
        B_state = B.states[B_si]

        # If 'B' reaches any acceptance state, then at least one
        # lexeme completely walks inside of 'A'
        if A_state.is_acceptance(): return True

        # Follow the path of common trigger sets
        line_up = get_intersection_line_up((A_state.target_map, B_state.target_map))
        for target_state_setup, trigger_set in line_up.items():
            A_target_si, B_target_si = target_state_setup
            if A_target_si in a_done_set and B_target_si in b_done_set: continue

            work_list.append((A_target_si, B_target_si))

        a_done_set.add(A_si)
        b_done_set.add(B_si)

    return False

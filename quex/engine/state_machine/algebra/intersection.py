# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""Intersection: 

      .-------------------------------------------------------------.
      | The intersection of multiple DFAs (state machines) is given |
      | by a DFA that matches *only* those lexemes that are matched |
      | by all DFAs.                                                |
      '-------------------------------------------------------------'

(C) 2013 Frank-Rene Schaefer
___________________________________________________________________________
"""
from   quex.engine.state_machine.core                 import DFA
from   quex.engine.state_machine.state.target_map_ops import get_intersection_line_up
import quex.engine.state_machine.index                as     index

def do(SM_List):
    for sm in SM_List:
        sm.assert_consistency() 

    if any(sm.is_Empty() for sm in SM_List): # If one state machine is '\Empty',
        return DFA.Empty()                   # then the intersection is '\Empty'.

    init_state_setup = tuple(sm.init_state_index for sm in SM_List)
    result           = DFA(AcceptanceF=intersect_acceptance(init_state_setup, SM_List))

    # Result state setup: A result state is setup out of a state from each DFA.
    #                     state_setup[i] is the state from DFA 'SM_List[i]'.
    worklist       = [ (result.init_state_index, init_state_setup) ]
    state_setup_db = {}
    N              = len(SM_List)
    while worklist:
        state_index, state_setup = worklist.pop()

        # Generate Map that shows what lexatoms trigger to what state combination.
        #
        #       NumberSet    Target DFA_State Combination 
        #       [0:23]   --> [ State1, State24, State56 ]
        #       [0:23]   --> [ State5, State21, State55 ]
        #       [24:60]  --> [ State1, State23, State51 ]
        #
        # 'get_intersection_line_up()' only delivers those transitions where there
        # is a transition for each state machine's state.
        line_up = get_intersection_line_up([SM_List[i].states[si].target_map
                                            for i, si in enumerate(state_setup)])
        for target_state_setup, trigger_set in line_up.items():
            assert len(target_state_setup) == N
            target_index, new_f = state_index_for_combination(state_setup_db,
                                                              target_state_setup)

            acceptance_f = intersect_acceptance(target_state_setup, SM_List)
            result.add_transition(state_index, trigger_set, target_index,
                                  AcceptanceF = acceptance_f)

            if new_f:
                worklist.append((target_index, target_state_setup))

    result.delete_hopeless_states()
    return result

def state_index_for_combination(state_setup_db, StateSetup):
    """RETURNS: [0] target index to represent 'StateSetup'
                [1] True, if the combination was new; False, else.
    """
    target_index = state_setup_db.get(StateSetup)
    if target_index is not None:
        return target_index, False
    target_index               = index.get()
    state_setup_db[StateSetup] = target_index
    return target_index, True

def intersect_acceptance(StateSetup, SM_List):
    return all(SM_List[i].states[si].is_acceptance() for i, si in enumerate(StateSetup))


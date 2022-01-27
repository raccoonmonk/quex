# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# (C) 2005-2016 Frank-Rene Schaefer
# ABSOLUTELY NO WARRANTY
###############################################################################
from   quex.engine.state_machine.core          import DFA
from   quex.engine.state_machine.state.core    import DFA_State
import quex.engine.state_machine.algorithm.nfa_to_dfa as nfa_to_dfa
from   quex.engine.misc.tools import typed

@typed(StateMachineList=[DFA])
def do(StateMachineList, CommonTerminalStateF=True):
    """Connect state machines paralell.

       CommonTerminalStateF tells whether the state machines shall trigger 
                            to a common terminal. This may help nfa-to-dfa
                            or hopcroft minimization for ISOLATED patterns.

                            A state machine that consists of the COMBINATION
                            of patterns MUST set this flag to 'False'.
    """
    assert len(StateMachineList) != 0
              
    def consider(sm):
        return not sm.is_Empty() and sm.get_init_state().has_transitions()

    # filter out empty state machines from the consideration          
    sm_list       = [ sm for sm in StateMachineList if consider(sm) ]
    empty_sm_list = [ sm for sm in StateMachineList if not consider(sm) ]

    if len(sm_list) < 2:
        if len(sm_list) < 1: result = DFA()
        else:                result = sm_list[0]

        return __consider_empty_state_machines(result, empty_sm_list)

    # (*) collect all transitions from both state machines into a single one
    result     = DFA()
    init_state = result.get_init_state()

    # Connect from the new initial state to the initial states of the
    # sms via epsilon transition. 
    # Connect from each success state of the sms to the new terminal
    # state via epsilon transition.
    if __nfa_to_dfa_required(sm_list):
        for sm in sm_list:
            result.states.update(
                (si, state.clone()) for si, state in sm.states.items()
            )
            init_state.target_map.add_epsilon_target_state(sm.init_state_index)
        result = nfa_to_dfa.do(result)
    else:
        # Set the 'single_entry' operations.
        init_state.set_single_entry(sm_list[0].get_init_state().single_entry.clone())
        # Add transitions to the states.
        for sm in sm_list:
            init_state.target_map.update(sm.get_init_state().target_map)
            # not __nfa_to_dfa_required(...) 
            # => No transition to an an init state.
            # => Original init states can be taken out.
            result.states.update(
                (si, state.clone()) 
                # (si, state.clone()) 
                for si, state in sm.states.items() if si != sm.init_state_index
            )
        result.assert_consistency()


    #if CommonTerminalStateF:
    #    __combine_transitionless_acceptance_states(result)

    return __consider_empty_state_machines(result, empty_sm_list)

def __nfa_to_dfa_required(SmList):
    """NFA to DFA transformation is only required if:

         -- there are epsilon transitions
         -- more than one target is reached by the same trigger

    Assumed that the input are DFAs, the result is only possibly an
    NFA, if the init state has intersecting transitions, or if there
    are transitions to the init state so that the state machines
    have to be considered seperatedly.
    """
    if DFA_State.interference([sm.get_init_state() for sm in SmList]):
        return True
    return any(sm.has_transition_to(sm.init_state_index) for sm in SmList)

def __consider_empty_state_machines(sm, EmptyStateMachineList):
    """An empty state machine basically means that its init state is going to 
    be merged into the init state of the resulting state machine. 

    If there is an empty state machine with an acceptance, then this is 
    reflected in the origins. Thus, the result's init state becomes an
    acceptance state for that pattern. 
    
    => There is no particular need for an epsilon transition to the common
       new terminal index.
    """
    single_entry = sm.get_init_state().single_entry
    for esm in EmptyStateMachineList:
        single_entry.merge(esm.get_init_state().single_entry)

    return sm

def __combine_transitionless_acceptance_states(result):
    """Combine all acceptance state that do not have any transition.
    """
    # Extract acceptance states that have no further transition
    equivalent_list = [
        si for si, state in result.acceptance_state_iterable()
        if state.target_map.is_empty() 
    ]
    if not equivalent_list: return

    prototype_si = equivalent_list.pop()

    # Delete all equivalent acceptance states, except for the prototype.
    for si in equivalent_list:
        result.states.pop(si)

    # Bend all transitions to removed states to transitions to the prototype.
    replacement_db = dict(
        (si, prototype_si)
        for si in equivalent_list
    )
    result.replace_target_indices(replacement_db)


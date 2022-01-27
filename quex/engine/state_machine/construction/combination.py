# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.construction.parallelize        as parallelize
import quex.engine.state_machine.algorithm.hopcroft_minimization as hopcroft_minimization
import quex.engine.misc.error                                    as     error

def do(StateMachine_List, FilterDominatedOriginsF=True,
       MarkNotSet=set(), AlllowInitStateAcceptF=False):
    """Creates a DFA state machine that incorporates the paralell
           process of all pattern passed as state machines in 
           the StateMachine_List. Each origins of each state machine
           are kept in the final state, if it is not dominated.

           Performs: -- parallelization
                     -- translation from NFA to DFA
                     -- Frank Schaefers Adapted Hopcroft optimization.

           Again: The state machine ids of the original state machines
                  are traced through the whole process.
                  
           FilterDominatedOriginsF, if set to False, can disable the filtering
                  of dominated origins. This is important for pre-contexts, because,
                  all successful patterns need to be reported!            
                          
    """   
    if len(StateMachine_List) == 0:
        return None

    def __insight_check(Place, sm, AlllowInitStateAcceptF):
        __check_on_orphan_states(Place, sm)
        if not AlllowInitStateAcceptF:
            __check_on_init_state_not_acceptance(Place, sm)
        error.insight("%s done." % Place)

    def __check_on_orphan_states(Place, sm):
        orphan_state_list = sm.get_orphaned_state_index_list()
        if len(orphan_state_list) == 0: return
        error.log("After '%s'" % Place + "\n" + \
                  "Orphaned state(s) detected in regular expression (optimization lack).\n" + \
                  "Please, log a defect at the projects website quex.sourceforge.net.\n"    + \
                  "Orphan state(s) = " + repr(orphan_state_list)) 

    def __check_on_init_state_not_acceptance(Place, sm):
        if sm.get_init_state().is_acceptance():
            error.log("After '%s'" % Place + "\n" + \
                      "Initial state 'accepts'. This should never happen.\n" + \
                      "Please, log a defect at the projects web site quex.sourceforge.net.\n")

    def __insight_begin(SM_List):
        ttn = 0
        for sm in SM_List:
            ttn += sum(state.target_map.get_transition_n() 
                       for state in sm.states.values())
        error.insight("Combine Patterns: %i patterns; %i total transition number;" \
                      % (len(SM_List), ttn))

    __insight_begin(StateMachine_List)

    # (1) mark at each state machine the machine and states as 'original'.
    #      
    # This is necessary to trace in the combined state machine the pattern that
    # actually matched. Note, that a state machine in the StateMachine_List
    # represents one possible pattern that can match the current input.   
    #
    for sm in StateMachine_List:
        if sm.get_id() in MarkNotSet: continue
        sm.mark_state_origins()
        assert sm.is_DFA_compliant(), sm.get_string(Option="hex")

    # (2) setup all patterns in paralell 
    sm = parallelize.do([sm.clone() for sm in StateMachine_List], 
                        CommonTerminalStateF=False) 
    __insight_check("Combine patterns", sm, AlllowInitStateAcceptF)


    # (4) determine for each state in the DFA what is the dominating original 
    #     state
    if FilterDominatedOriginsF: sm.filter_dominated_origins()
    __insight_check("Clean-up state entry operations", sm, AlllowInitStateAcceptF)

    # (3) convert the state machine to an DFA (paralellization created an NFA)
    sm = hopcroft_minimization.do(sm, CreateNewStateMachineF=False)
    __insight_check("Hopcroft Minimization", sm, AlllowInitStateAcceptF)
    
    return sm

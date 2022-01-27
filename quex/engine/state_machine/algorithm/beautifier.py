# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.algorithm.nfa_to_dfa            as nfa_to_dfa
import quex.engine.state_machine.algorithm.hopcroft_minimization as hopcroft

def do(SM, NfaToDfaF=True, CloneF=True):
    """Construct a state machine which is equivalent to SM and is:

       -- DFA compliant, i.e. without epsilon transitions and no two
              transitions to the same target.
       -- Hopcroft-minimized.
    """
    if NfaToDfaF: result = nfa_to_dfa.do(SM, CloneF=CloneF)
    else:         result = SM
    hopcroft.do(result, CreateNewStateMachineF=False)

    return result

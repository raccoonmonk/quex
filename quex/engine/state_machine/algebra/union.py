# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.construction.parallelize        as parallelize
import quex.engine.state_machine.algorithm.hopcroft_minimization as hopcroft_minimization

def do(SM_List):
    """The 'parallelize' module does a union of multiple state machines,
    even if they have different origins and need to be combined carefully.
    There is no reason, why another 'union' operation should be implemented
    in this case.
    """
    result = parallelize.do(SM_List)
    result = hopcroft_minimization.do(result, CreateNewStateMachineF=False)
    return result


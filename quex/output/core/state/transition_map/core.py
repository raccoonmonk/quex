# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.output.core.state.transition_map.solution as     solution
from   quex.blackboard                                import setup as Setup

def do(txt, TM, AssertBorderF=False):
    """Generate code for transition map 'TM'.

                    TM = list of pairs (interval, string)

    where 'string' is the code to be executed when a value falls inside the
    given 'interval'. The variable that carries the value which is compared
    agains the intervals is (implicitly) given as 

                                    'input'

    For state machines, the 'string' must be the code to transit to another
    state.
    
    RETURNS: Code that implements the map.
    """
    #__________________________________________________________________________
    #
    #   NOT:      TM.prune(min, least_greater_bound) !!
    #
    # Pruning at this point in time would mean that possible transitions are 
    # cut. As a consequence whole branches of the the state machine may be 
    # unreachable! Such things must have been clarified before!
    #__________________________________________________________________________
    if AssertBorderF: _assert_consistency(TM)

    structure = solution.do(TM)

    txt.extend(structure.implement())

def _assert_consistency(TM):
    """Check consistency of the given transition map.

    IMPORTANT: 

    The transition map MUST NOT exceed the range given by the buffer element
    type! Otherwise, it would mean that transitions wer cut off! This may lead
    to undefined reference labels etc. Such things must have been clarified
    before the call of the transition map coder!
    
    ABORTS: In case that the given transition map is not properly setup.
    """
    assert TM is not None
    assert len(TM) != 0

    # The transition map MUST be designed to cover exactly the range of 
    # of possible values given by the buffer element type!
    TM.assert_boundary(Setup.lexatom.type_range.begin,
                       Setup.lexatom.type_range.end) 

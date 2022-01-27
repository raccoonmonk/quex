# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.state_machine.core import DFA

def do(sm):
    """Sanitization: 
        
           .--------------------------------------------------------.
           | A DFA that has no acceptance states *cannot be healed* |
           |                 by this function.                      |
           '--------------------------------------------------------'

    This operation tries to transform a DFA into something that is admissible.
    Two lexemes are inadmissible and therefore their matching DFAs are
    inadmissible.

    They are:

        (i) The zero-length lexeme.
            It triggers on nothing, the lexer remains at the same position
            while permanently accepting the same position.

        (ii) The endless lexeme.
            It triggers an infinite number of lexatoms.

    The first is healed by removing acceptance from the init state. The second
    is healed by considering states that accept and transit to itself on any
    character.  In that case, the transition on any character to itself is
    removed.

    Noteably, the 'Empty' DFA and the 'Universe' DFA cannot be healed. The
    former case is obvious. The 'Universe' DFA has only one initial state on
    which it accepts. Through the admissibility removal it has no further
    acceptance states.
    """
    init_state = sm.get_init_state()

    # (i) Acceptance in init state => remove acceptance
    if init_state.is_acceptance():
        init_state.set_acceptance(False)

    # (ii) Infinite iteration on any input => remove transition to itself.
    for state_index, state in sm.states.items():
        if DFA.is_AcceptAllState(sm, state_index): 
            state.target_map.clear()   

    sm.delete_hopeless_states()

    return sm


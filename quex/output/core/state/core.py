# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.output.core.state.transition_map.code  import relate_to_TransitionCode
import quex.output.core.state.transition_map.core  as     transition_block
import quex.output.core.state.entry                as     entry
from   quex.engine.analyzer.core                   import FSM
from   quex.engine.analyzer.state.core             import FSM_State
from   quex.engine.misc.tools                      import typed, \
                                                          none_isinstance, \
                                                          none_is_None

@typed(TheState=FSM_State, TheAnalyzer=FSM)
def do(code, TheState, TheAnalyzer):

    # (*) Entry _______________________________________________________________
    txt, post_txt = entry.do(TheState)

    # (*) Transition Map ______________________________________________________
    tm = relate_to_TransitionCode(TheState.transition_map, 
                                  TheState.entry.dial_db)

    transition_block.do(txt, tm)

    # (*) Post-state entry to init state (if necessary)
    txt.extend(post_txt) 

    # (*) Consistency check ___________________________________________________
    assert none_isinstance(txt, list)
    assert none_is_None(txt)
    code.extend(txt)


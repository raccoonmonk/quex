# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.algebra.difference         as     difference 
import quex.engine.state_machine.algebra.intersection       as     intersection
import quex.engine.state_machine.construction.sequentialize as     sequentialize
import quex.engine.state_machine.algorithm.beautifier       as     beautifier
from   quex.engine.state_machine.core                       import DFA

def not_begin(P, Q):
    return beautifier.do(difference.do(P, anything_beginning_with(Q)))

def not_end(P, Q):
    return beautifier.do(difference.do(P, anything_ending_with(Q)))

def not_in(P, Q):
    return beautifier.do(difference.do(P, anything_containing(Q)))

def is_begin(P, Q):
    return beautifier.do(intersection.do([P, anything_beginning_with(Q)]))

def is_end(P, Q):
    return beautifier.do(intersection.do([P, anything_ending_with(Q)]))

def is_in(P, Q):
    return beautifier.do(intersection.do([P, anything_containing(Q)]))

def anything_beginning_with(Q):
    tmp = sequentialize.do([Q, DFA.Universe()])
    return beautifier.do(tmp)

def anything_ending_with(Q):
    tmp = sequentialize.do([DFA.Universe(), Q])
    return beautifier.do(tmp)

def anything_containing(Q):
    tmp = sequentialize.do([DFA.Universe(), Q, DFA.Universe()])
    return beautifier.do(tmp)


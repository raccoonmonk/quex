# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.state_machine.algebra.union        import do as union 
from   quex.engine.state_machine.algebra.intersection import do as intersection 
from   quex.engine.state_machine.algebra.complement   import do as complement 
from   quex.engine.state_machine.algebra.difference   import do as difference 
from   quex.engine.state_machine.check.identity       import do as identity 
from   quex.engine.state_machine.check.superset       import do as superset 
from   quex.engine.state_machine.core                 import DFA

import quex.input.regular_expression.engine           as     regex
import   quex.engine.state_machine.TEST_help.many_shapes as shapes

           

shapes.set_unique_transition_f()

def dfa(Str): 
    return regex.do(Str, {}, AllowNothingIsNecessaryF=True).extract_sm()

__dfa_list = [
        DFA.Universe(),  # Matches all lexemes
        DFA.Empty(),      # Matches the lexeme of zero length
        #
        dfa('a'),
        dfa('ab'),
        dfa('a(b?)'),
        dfa('ab|abcd'),
        # "Branches" 
        dfa('12|AB'),
        dfa('x(12|AB)'),
        dfa('(12|AB)x'),
        dfa('x(12|AB)x'),
        dfa('x(1?2|A?B)x'),
        dfa('x(1?2?|A?B?)x'),
        # "Loops" 
        dfa('A+'),
        dfa('A(B*)'),
        dfa('A((BC)*)'),
        dfa('((A+)B+)C+'),
        # "BranchesLoops"
        dfa('(AB|XY)+'),
        dfa('(AB|XY)(DE|FG)*'),
        dfa('(AB|XY)+(DE|FG)+'),
        dfa('((AB|XY)(DE|FG))+'),
        # "Misc" 
        dfa('(pri|ri|n)+'),
        dfa('(p?r?i?|rin|n)+'),
]

def add_more_DFAs():
    global __dfa_list
    __dfa_list.extend(
        shapes.get_sm_shape_by_name_with_acceptance(name.strip())
        for name in shapes.get_sm_shape_names_list()
    )

def sample_DFAs(Factor):
    global __dfa_list
    __dfa_list = [ dfa for i, dfa in enumerate(__dfa_list)
                   if i % Factor == 0 ]

assert all(isinstance(dfa, DFA) for dfa in __dfa_list)

def iterate1():
    global __dfa_list
    for dfa in __dfa_list:
        yield dfa.clone()

def iterate2():
    for dfa0 in __dfa_list:
        for dfa1 in __dfa_list:
            yield dfa0.clone(), dfa1.clone()

def iterate3():
    for i, dfa0 in enumerate(__dfa_list):
        for k, dfa1 in enumerate(__dfa_list[i:]):
            for p, dfa2 in enumerate(__dfa_list[k:]):
                yield dfa0.clone(), dfa1.clone(), dfa2.clone()

def test1(function):
    for arg in iterate1():
        function(arg)

def test2(function):
    for arg0, arg1 in iterate2():
        function(arg0, arg1)

def test3(function):
    for arg0, arg1, arg2 in iterate3():
        function(arg0, arg1, arg2)

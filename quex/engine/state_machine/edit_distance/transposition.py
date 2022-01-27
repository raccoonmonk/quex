# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.tools                          import flatten
from   quex.engine.state_machine.core                  import DFA
import quex.engine.state_machine.algorithm.beautifier  as     beautifier

from copy import copy


def do(Dfa, N, ConcernedCharacterSet):
    """A 'transposition' switches two adjacent characters. A DFA matching "nice"
    after transposition with N=1, matches the lexemes
          
                       "ince", "ncie", "niec"

    after the transposition with N=2, it matches

                       "nice", "icne", "inec",  (from "ince")
                       "cnie", "nice", "ncei",  (from "ncie")
                       "inec", "neic", "nice",  (from "niec")

    As can be seen, the result of N=1 does not match the original lexeme.
    N=2 does, since it contains lexemes that undid the actions of N=1.

    Only characters in 'ConcernedCharacterSet' are subject to transposition.

    NOT: The result DOES NOT MATCH 'UP TO' 'N' TRANSPOSITIONS. It matches
         exactly 'N' transpositions.
    
    RETURNS: DFA that matches all lexemes that can be produced by 'N'
             transpositions of adjacent characters.
    """
    iterable = Dfa.iterable_paths(1)
    for i in range(N):
        iterable = _unique_iter(_next_path_list(iterable, ConcernedCharacterSet))
            
    return beautifier.do(DFA.from_path_list(list(p for p in iterable)))

def do_upto(Dfa, N, ConcernedCharacterSet):
    """Same as 'do()' but result matches any lexeme that can be produced by 
    UP TO 'N' transpositions.

    Only characters in 'ConcernedCharacterSet' are subject to transposition.

    RETURNS: DFA that matches up to 'N' transpositions of the lexemes of 'Dfa'.
    """

    # Lists as iterable => may be consumed multiple times.
    # (Assumed 'list' operates faster then 'itertools.tee')
    iterable      = [x for x in Dfa.iterable_paths(1)]
    all_path_list = copy(iterable)
    for i in range(N):
        path_list = _next_path_list(iterable, ConcernedCharacterSet)
        iterable  = [x for x in _unique_iter(path_list)]
        all_path_list.extend(iterable)

    return beautifier.do(DFA.from_path_list(all_path_list))

def _next_path_list(iterable, ConcernedCharacterSet):
    return flatten(
        _generate_adapted_paths_on_pivots(path, ConcernedCharacterSet)
        for path in iterable if len(path) > 2
    )

def _unique_iter(PathList):
    """Avoid applying the same path twice.
    
    YIELDS: Paths from 'PathList' without yielding the same path twice.
    """

    def _is_equal(PathX, PathY):
        if len(PathX) != len(PathY): return False
        return all(x[0] == y[0] and ((x[1] is None and y[1] is None) or x[1].is_equal(y[1]))
                   for x, y in zip(PathX, PathY))

    def _is_present(Path, PathList):
        """RETURNS: True, if 'Path' is in 'PathList'.
                    False, else.
        """
        return any(_is_equal(Path, x) for x in PathList)

    for i, path in enumerate(PathList):
        if not _is_present(path, PathList[i+1:]): yield path

def _generate_adapted_paths_on_pivots(Path, ConcernedCharacterSet):
    """Receives a 'Path' through a DFA where each element is a tuple
     
       (state index reached, character set that triggered transition)

    It applies '_treat_transition' on two consecutive steps on the path. That
    function switches to steps on the path. 

    YIELDS: All paths that can be produced by a single transposition applied
            on the original 'Path'.
    """
    L = len(Path)

    changed_f = False
    for transpose_i in range(2, L):
        # cursor[i] -> position before the pivot
        operation_done_f = False
        new_path         = [ Path[0] ]
        current_step     = Path[1]
        for position, si in enumerate(Path[2:], start=2):
            prev_step    = current_step
            current_step = Path[position]
            if position == transpose_i:
                prev_step, \
                current_step, done_f = _treat_transition(new_path, prev_step, 
                                                         current_step, 
                                                         ConcernedCharacterSet)
                operation_done_f |= done_f
            new_path.append(prev_step)
        new_path.append(current_step)

        if operation_done_f:
            changed_f = True
            yield new_path

    if not changed_f:
        yield copy(Path)

def _treat_transition(new_path, PrevStep, CurrentStep, ConcernedCharacterSet): 
    """Switch to subsequent transitions.
    
       (StartSi)--- Cs0 --->(TargetSi)--- Cs1 --->(TargetSi)
               
    is replaced by a transition

       (StartSi)--- Cs1 --->(TargetSi)--- Cs0 --->(TargetSi)

    RETURNS: True, if something happend; False, else.
    """
    start_si, cs0  = PrevStep
    target_si, cs1 = CurrentStep
    if     cs0.has_intersection(ConcernedCharacterSet) \
       and cs1.has_intersection(ConcernedCharacterSet):
        remove0    = cs0.intersection(ConcernedCharacterSet)
        remainder0 = cs0.difference(ConcernedCharacterSet)
        remove1    = cs1.intersection(ConcernedCharacterSet)
        remainder1 = cs1.difference(ConcernedCharacterSet)
        new_cs0 = remainder0.union(remove1)
        new_cs1 = remainder1.union(remove0)
        return (start_si,  new_cs0), (target_si, new_cs1), True
    else:
        return PrevStep, CurrentStep, False


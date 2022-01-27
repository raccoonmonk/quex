# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: Edit Distance Functions

NOTE: Those functions are supposed to operate on non-cyclic DFAs.

This module implements functions to transform a given DFA into
a similar DFA. This may happen by means of the following functions:

 'insert':     Add an arbitrary lexatom at 1 position for each 
               matching lexeme.
 'delete':     Remove one transition for each matching lexeme.
 'substitute': Substitute any character of a set by another 
               character set.

For each function 'func()', there is a sister function 'func_upto()' that 
matches lexemes produced from up to 'N' operations.
"""
from   quex.engine.misc.tools                              import iterator_N_on_M_slots, \
                                                                  iterator_N_on_M_slots_multiple_occupancy, \
                                                                  flatten
from   quex.engine.state_machine.core                      import DFA
import quex.engine.state_machine.index                     as     index
import quex.engine.state_machine.algorithm.beautifier      as     beautifier
import quex.engine.state_machine.edit_distance.levenshtein as     levenshtein

from   copy import copy

def insert(Dfa, N, CharacterSet):
    """RETURNS: DFA that matches all lexemes that can be produced by EXACTLY 'N'
                insertions of 'CharacterSet'.
    """
    return _apply(Dfa, EdInsert(CharacterSet, N))

def insert_upto(Dfa, N, CharacterSet):
    """RETURNS: DFA that matches all lexemes that can be produce by UP TO 'N'
                insertions of 'CharacterSet'.
    """
    return levenshtein.do(Dfa, N, 
                          InsertableCs=CharacterSet, 
                          DeletableCs=None, 
                          SubstitutableCs=None, 
                          SubstituteCs=None)

def delete(Dfa, N, CharacterSet):
    """RETURNS: DFA that matches all lexemes that can be produced by EXACTLY 'N' 
                deletions of 'CharacterSet'.
    """
    return _apply(Dfa, EdDelete(CharacterSet, N))

def delete_upto(Dfa, N, CharacterSet):
    """RETURNS: DFA that matches all lexemes that can be produce by UP TO 'N'
                deletions of 'CharacterSet'.
    """
    return levenshtein.do(Dfa, N, 
                          InsertableCs=None, 
                          DeletableCs=CharacterSet, 
                          SubstitutableCs=None, 
                          SubstituteCs=None)

def substitute(Dfa, SubstN, ConcernedCharacterSet, SubstituteCharacterSet):
    """RETURNS: DFA that matches all lexemes that can be produce by EXACTLY 'N'
                substitions of characters from 'ConcernedCharacterSet' by 
                characters from 'SubstituteCharacterSet'.
    """
    return _apply(Dfa, EdSubstitute(ConcernedCharacterSet, SubstituteCharacterSet, SubstN))

def substitute_upto(Dfa, N, ConcernedCharacterSet, SubstituteCharacterSet):
    """RETURNS: DFA that matches all lexemes that can be produce by UP TO 'N'
                substitions of characters from 'ConcernedCharacterSet' by 
                characters from 'SubstituteCharacterSet'.
    """
    return levenshtein.do(Dfa, N, 
                          InsertableCs=None, 
                          DeletableCs=None, 
                          SubstitutableCs=ConcernedCharacterSet, 
                          SubstituteCs=SubstituteCharacterSet)

def _apply(Dfa, ed_operation):
    """Iterate over paths of 'Dfa'. Apply the derived class's adaptations
    and build a new DFA from the given list of paths.

    RETURNS: New DFA
    """
    path_list = flatten(
        _generate_adapted_paths(ed_operation, path) 
        for path in Dfa.iterable_paths(1) if len(path) > ed_operation.min_step_n
    )
    result = DFA.from_path_list(path_list)
    result = beautifier.do(result)
    result.get_init_state().set_acceptance(False)
    return result

def _generate_adapted_paths(ed_operation, Path): 
    """Receives a 'Path' through a DFA where each element is a tuple
     
       (state index reached, character set that triggered transition)

    According to the three edit distance operations 'insert', 'delete',
    and 'substitute' the path is adapted. The result is a list of paths.

    The path is, at 'AdaptN' positions. This functions finds all combinations
    of positions on the path, where adaptations can be made. For example,
    if a path has 3 steps and 2 adaptations are to be made then the 
    the following arrays display the possible change configurations

                            [1, 1, 0]
                            [1, 0, 1]
                            [0, 1, 1]

    were a 'array[i] == 1' indicates a change is to be made at step 'i' and
    else, it is left as is. A path of N elements has N-1 steps.
    """
    changed_f  = False
    for cursor in ed_operation.generator(len(Path)):
        # cursor[i] -> where the i-th insertion happens.
        new_path         = []
        operation_done_f = False
        for position, step in enumerate(Path + [(None, None)]):
            target_si, character_set = step
            if position in cursor:
                occupancy_n = sum(int(p == position) for p in cursor)
                operation_done_f |= ed_operation.treat_transition(new_path, target_si, 
                                                                  character_set, occupancy_n)
            elif target_si is not None:
                new_path.append((target_si, character_set))

        if operation_done_f:
            changed_f = True
            yield new_path

    if not changed_f:
        yield copy(Path)

class EdOperation:
    def __init__(self, MinStepN):
        self.min_step_n = MinStepN # Minimum number of steps on path to operate

class EdInsert(EdOperation):
    """Modify 'Dfa' so that it matches lexemes with additional characters. For 
    example, given a DFA that matches

                while

    an insertion of '1' from the character set '[a-z]' results in a DFA that
    corresponds to the union of the following regular expressions:

                w[a-z]hile
                wh[a-z]ile
                whi[a-z]le
                whil[a-z]e

    .------------------------------------------------------------------.
    | NOTE: If the DFA contains CYCLES, and 'insert N' might actually  |
    |       tolerate an infinite number of additional characters.      |
    '------------------------------------------------------------------'

    That is, any transtion such as

               ( 0 )-- 'h' -->( 1 )

    is replaced by

               ( 0 )-- [a-z] -->( 2 )-- 'h' -->( 1 )

    If 'InsertionN' is greater than 1, more than one transition is replaced at
    a time.

    NOTE: There is NO INSERTION after the lexeme, because this is 
          in contradiction to the concept of a 'match' that goes
          until no match occurs.
    """
    def __init__(self, CharacterSet, InsertN):
        self._character_set = CharacterSet
        self._insert_n      = InsertN
        EdOperation.__init__(self, MinStepN=0)

    def treat_transition(self, new_path, TargetSi, CharacterSet, OccupancyN):
        """The transition 
        
           (StartSi)--- CharacterSet --->(TargetSi)
                   
        receives an intermediate transition, so that it becomes

           (StartSi)--- InsertCharacterSet --->(NewSi)--- CharacterSet --->(TargetSi)

        RETURNS: True, if something happend; False, else (i.e. never)
        """
        ConcernedCharacterSet = self._character_set
        if   TargetSi is None:      # terminal step
            for i in range(OccupancyN):
                new_si = index.get()
                new_path.append((new_si,   ConcernedCharacterSet))
        elif CharacterSet is None:  # initial step
            new_si = index.get()
            new_path.append((new_si,   None))
            for i in range(OccupancyN-1):
                new_si = index.get()
                new_path.append((new_si,   ConcernedCharacterSet))
            new_path.append((TargetSi, ConcernedCharacterSet))
        else:
            for i in range(OccupancyN):
                new_si = index.get()
                new_path.append((new_si,   ConcernedCharacterSet))
            new_path.append((TargetSi, CharacterSet))

        return True

    def generator(self, PathL):
        return iterator_N_on_M_slots_multiple_occupancy(self._insert_n, PathL+1)

class EdDelete(EdOperation):
    """Modify 'Dfa' so that it matches lexemes with deleted characters. For 
    example, given a DFA that matches

                silencium

    an deletion of '1' from the character set '[sim]' results in a DFA that
    corresponds to the union of the following regular expressions:

                ilencium   ('s'        removed)
                slencium   (first 'i'  removed)
                silencum   (second 'i' removed)
                silencu    ( 'm'       removed)

    characters not mentioned in 'CharacterSet' are never removed.
    """
    def __init__(self, CharacterSet, DeleteN):
        self._character_set = CharacterSet
        self._delete_n      = DeleteN
        EdOperation.__init__(self, MinStepN=DeleteN)

    def treat_transition(self, new_path, TargetSi, CharacterSet, OccupancyN):
        """Remove all elements from 'CharacterSet' which are mentioned in 
        'ConcernedCharacterSet'. A transition,
        
           (StartSi)--- CharacterSet --->(TargetSi)
                   
        is replaced by a transition

           (StartSi)--- 'CharacterSet - ConcernedCharacterSet' --->(TargetSi)

        If the resulting set is empty, the transition is removed completely.

        RETURNS: True, if something happend; False, else.
        """
        ConcernedCharacterSet = self._character_set
        if     CharacterSet is not None \
           and CharacterSet.has_intersection(ConcernedCharacterSet):
            remainder = CharacterSet.difference(ConcernedCharacterSet)
            # Add an epsilon transition 
            new_path.append((TargetSi, None)) 
            if not remainder.is_empty(): new_path.append((TargetSi, remainder)) 
            return True
        else:
            # Old transition remains in place
            new_path.append((TargetSi, CharacterSet))
            return False

    def generator(self, PathL):
        occupier_n = min(PathL-1, self._delete_n)
        for cursor in iterator_N_on_M_slots(occupier_n, PathL-1):
            yield tuple(cursor[i] + 1 for i, x in enumerate(cursor))

class EdSubstitute(EdOperation):
    """Remove all elements from 'CharacterSet' which are mentioned in 
    'ConcernedCharacterSet'. If that happened, enter the complete 
    SubstituteCharacterSet into the transition.
    
       (StartSi)--- CharSet --->(TargetSi)
               
    is replaced by a transition

       (StartSi)--- 'CharSet - ConcernedCharSet + SubstituteCharSet' --->(TargetSi)

    If the resulting set is empty, the transition is removed completely.

    RETURNS: True, if something happend; False, else.
    """
    def __init__(self, ConcernedCharacterSet, SubstituteCharacterSet, SubstN):
        self._character_set            = ConcernedCharacterSet
        self._substitute_character_set = SubstituteCharacterSet
        self._substitution_n           = SubstN
        EdOperation.__init__(self, MinStepN=SubstN)

    def treat_transition(self, new_path, TargetSi, CharacterSet, OccupancyN):
        ConcernedCharacterSet  = self._character_set
        SubstituteCharacterSet = self._substitute_character_set
        if   not CharacterSet:                                         return False
        elif not CharacterSet.has_intersection(ConcernedCharacterSet): return False
        new_character_set = CharacterSet.difference(ConcernedCharacterSet)
        new_character_set.unite_with(SubstituteCharacterSet)
        new_path.append((TargetSi, new_character_set))
        return True

    def generator(self, PathL):
        occupier_n = min(self._substitution_n, PathL-1)
        for cursor in iterator_N_on_M_slots(occupier_n, PathL-1):
            yield tuple(cursor[i] + 1 for i, x in enumerate(cursor))


# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.algebra.union               as     union
import quex.engine.state_machine.edit_distance.levenshtein   as     levenshtein
import quex.engine.state_machine.edit_distance.transposition as     transposition

def do(Dfa, N, InsertableCs, DeletableCs, SubstitutableCs, SubstituteCs, TransposableCs):
    """Generates  Damerau-Levenshtein Automata (brief 'DLA').
    
    An 'DLA' of a given 'Dfa' matches all lexemes which can be matched by the
    'Dfa', plus the lexemes that can be produced by 'N' edit distance 
    operations, namely 'insert', 'delete', 'substitute', and 'transposition'.

    'InsertableCs':    characters inserted during an 'Insert' ed-op.
                       '= None' disables insertion.
    'DeleteableCs':    characters deleted during an 'Delete' ed-op.
                       '= None' disables deletion.
    'SubstitutableCs': characters substitutable during an 'Substitute' ed-op.
                       '= None' disables substitution.
    'SubstituteCs':    characters substituted during an 'Substitute' ed-op.
    'TransposableCs':  characters possibly subject to transposition.

    NOTE: For DFAs with cycles, the result is still functional. It still
          matches similar lexemes, but the edit distance assumption may not 
          hold.
    
    RETURNS: Damerau-Levenshtein Automaton.
    """
    # EXPLANATION:
    # 
    # A 'Damerau Automaton' is an automaton that matches lexemes with an edit
    # distance of not more than 'N'. The operations admitted are mentioned above.
    # Now, if no transposition is required, all remaining operations may be 
    # Levenshtein operations (insert, delete, and substitute). If one tranposition
    # is required only 'N-1' Levenshtein operations are allowed. This continues
    # until 'N' transposition and no levenshtein operation.
    #
    # All possible DFAs are then alternatives, i.e. the union expresses their
    # collective match.
    alternatives = [
        # levenshtein_n=0, transpose_n=N
        levenshtein.do(Dfa, N, 
                       InsertableCs, DeletableCs, SubstitutableCs, SubstituteCs),
        # levenshtein_n=N, transpose_n=0
        transposition.do(Dfa, N, TransposableCs)
    ]
    alternatives.extend(
        # levenshtein_n=i, transpose_n=N-i
        levenshtein.do(transposition.do(Dfa, N-i, TransposableCs), i, 
                       InsertableCs, DeletableCs, SubstitutableCs, SubstituteCs)
        for i in range(1,N) 
    )
    return union.do(alternatives)

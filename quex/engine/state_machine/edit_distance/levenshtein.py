# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.state_machine.core                 import DFA
import quex.engine.state_machine.index                as     index
import quex.engine.state_machine.algorithm.beautifier as     beautifier

def do(Dfa, N, InsertableCs, DeletableCs, SubstitutableCs, SubstituteCs):
    """Generates a Levenshtein Automaton (brief 'LA').
    
    An 'LA' of a given 'Dfa' matches all lexemes which can be matched by the
    'Dfa', plus the lexemes that can be produced by 'N' edit distance 
    operations. Edit distance operations are 'insert', 'delete', and 
    'substitute'.

    'InsertableCs':    characters inserted during an 'Insert' ed-op.
                       '= None' disables insertion.
    'DeleteableCs':    characters deleted during an 'Delete' ed-op.
                       '= None' disables deletion.
    'SubstitutableCs': characters substitutable during an 'Substitute' ed-op.
                       '= None' disables substitution.
    'SubstituteCs':    characters substituted during an 'Substitute' ed-op.

    NOTE: For DFAs with cycles, the result is still functional. It still
          matches similar lexemes, but the edit distance assumption may not 
          hold.
    
    RETURNS: Levenshtein Automaton.
    """
    # HOW IT WORKS:
    #
    # An edit distance operation (ed-op) that fixes a deviation from an
    # original lexeme corresponds to special transitions. For an edit distance
    # of 'N' create 'N' levels of clones of the original DFA. Every clone
    # stands for the number of remaining ed-ops. Whenever and ed-op is applied,
    # it transits to the next level. When the highest level is reached no 
    # further ed-ops can be applied.

    grid = LevelGrid(Dfa, N)

    for next_level_db, si, state_tm in grid:
        # Copy the original transitions before any new ones are added.
        transition_iterable = list(iter(state_tm))

        # Insert transitions => Transition to the clones same state
        if InsertableCs is not None:
            next_level_si = next_level_db[si]
            state_tm.add_transition(InsertableCs, next_level_si)

        for target_si, character_set in transition_iterable:
            next_level_target_si = next_level_db[target_si]
            # Delete transitions => Epsilon to the clones subsequent states
            if     DeletableCs is not None \
               and DeletableCs.has_intersection(character_set): 
                state_tm.add_epsilon_target_state(next_level_target_si)
        
            # Substitutable transitions => Remainder to next level target
            if     SubstitutableCs is not None \
               and SubstitutableCs.has_intersection(character_set):
                remainder = SubstituteCs.difference(character_set)
                state_tm.add_transition(remainder, next_level_target_si)

    return beautifier.do(grid.dfa, CloneF=False)

class LevelGrid:
    def __init__(self, Dfa, N):
        """Whenever a transition happens which can only occur with an edit
        operation 'insert', 'delete', or 'substitute', there is a transition
        to a next level clone which allows one less edit operation.

        RETURNS: [0] List of DFAs 'clone_list'.
                 [1] State index database 'clone_state_db', where

            clone_state_db[clone_i][state_i] ---> correspondent state index 
                                                  in 'clone_i+1'

        For a given DFA clone 'clone_list[i]', the dictionary entry 
        'db[clone_i][state_i]' gives the state index of the original DFA
        from where the state 'state_i' has been cloned.
        """
        def get_replacement_db(SiIterable):
            return dict((orig_si, index.get()) for orig_si in SiIterable)

        self.dfa                       = DFA(DoNothingF=True)
        self.level_n                   = N
        self.next_level_state_index_db = []
        prev_clone                     = Dfa
        for level in range(self.level_n+1):
            next_level_db = get_replacement_db(iter(prev_clone.states.keys()))
            if level:
                self.next_level_state_index_db.append(next_level_db)
            else:
                # The grid's init state is the init state of the clone on the lowest 
                # level of the grid.
                self.dfa.init_state_index = next_level_db[prev_clone.init_state_index]
            next_level_clone    = prev_clone.clone(next_level_db)
            self.dfa.states.update(next_level_clone.states)
            # ... connections between states are done later.

            prev_clone = next_level_clone
            assert(set(next_level_db.values()) == set(next_level_clone.states.keys()))

    def __iter__(self):
        for next_level_db in self.next_level_state_index_db:
            for si in next_level_db.keys():
                yield next_level_db, si, self.dfa.states[si].target_map 


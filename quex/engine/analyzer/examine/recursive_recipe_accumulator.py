# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.tree_walker           import TreeWalker

class RecursiveRecipeAccumulator(TreeWalker):
    """Walks recursively along linear states until it reaches a terminal, until the
    state ahead is a mouth state, or a determined state.

        -- Performs the accumulation according to the given 'RecipeType'. 

        -- Every mouth state for which all entry recipes are defined, is added
           to the 'determined_mouths' set.

    The 'determined_mouths' will later determine their .recipe through 'interference'.
    """
    def __init__(self, TheExaminer):
        self.examiner           = TheExaminer
        self.mouths_touched_set = set()
        TreeWalker.__init__(self)

    def on_enter(self, Args):
        """Consider transitions of current state with determined recipe.
        """
        CurrStateIndex, CurrRecipe = Args
        curr_state = self.examiner._sm.states[CurrStateIndex]

        # Termination Criteria:
        # * DFA_State  = Terminal: no transitions, no further recursion. 
        #                      (Nothing needs to be done to guarantee that)
        # * Target is Mouth DFA_State => No entry!
        # * Target is Spring      => No entry!
        todo = []
        for target_index in curr_state.target_map.iterable_target_state_indices():
            if target_index is None: continue
            target_info = self.examiner.get_state_info(target_index)
            target      = self.examiner._sm.states[target_index]
            accumulated = self.examiner.recipe_type.accumulation(CurrRecipe, 
                                                                 target.single_entry)
            if target_info.mouth_f():        
                # Mouth state ahead => accumulate, but do NOT enter!
                target_info.entry_recipe_db[CurrStateIndex] = accumulated
                self.mouths_touched_set.add(target_index)
                continue # terminal condition
            elif target_info.spring_f:
                continue # terminal condition
            else:
                # Linear state ahead => accumulate and go further
                target_info.recipe = accumulated
                todo.append((target_index, target_info.recipe))

        if not todo: return None
        else:        return todo

    def on_finished(self, node):
        pass



# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""
PURPOSE: Implementation of the 'Recipe-Based-Optimization' as described in the
         file ./doc/main.tex.

         [DOC] --> means the documentation located in ./doc
________________________________________________________________________________

NOTE: A significant amount of effort has been put into the development of the
      documentation in order to derive process details and to proof the 
      correctness of the approach. Reading the documents may take two hours. 
      However, the provided knowledge is key to understand this code.

(C) Frank-Rene Schaefer

ABSOLUTELY NO WARRANTY
________________________________________________________________________________
"""
from   quex.engine.analyzer.examine.examiner     import Examiner
from   quex.engine.state_machine.core            import DFA
from   quex.engine.analyzer.examine.recipe_base  import Recipe
from   quex.engine.misc.tools                    import typed

@typed(SM=DFA)
def do(SM, RecipeType):
    """Takes a 'single-entry state machine' and derives an optimized 'multi-
    entry state machine' that behaves identical from an outside view [DOC].
    
    RecipeType -- derived from recipe_base.Recipe

    This type controls procedure elements related to an 'investigated behavior'
    [DOC]. Examples of investigated behavior are: acceptance behavior, line and
    column number counting, check-sum computation.
    """
    assert issubclass(RecipeType, Recipe)
        
    examiner = Examiner(SM, RecipeType)

    # Categorize states:
    #    .linear_db: 'linear states' being entered only from one state.
    #    .mouth_db:  'mouth states' being entered from multiple states.
    examiner.categorize()

    # Determine starting states from where the recursive accumulation of 
    # recipes may begin.
    springs   = examiner.setup_initial_springs()
    remainder = set(examiner.mouth_db.keys())

    # Core Algorithm:
    #
    # .----> (1) If there are no springs and there are undetermined mouth states
    # |          => prepare 'cautious recipes' in horizon states.
    # |          => horizon states become springs.
    # |      (2) Recursive accumulation of recipes.
    # '-yes- (3) Are there remaining undetermined mouth states?
    #
    while 1 + 1 == 2:
        if not springs:
            # No springs => consider horizon states and equip them with 
            #               'cautious recipes'.
            springs = examiner.prepare_springs_of_horizon(remainder)

        # Perform recursive accumulation, interfere if possible and further
        # perform recursive accumulation, ... until no springs are left to
        # from where to start.
        remainder = examiner.resolve(springs)
        if not remainder: break

        # When '.resolve()' stops, then there are no new springs to start a
        # further recursive accumulation.
        springs   = False
        
    # Double check, that the result makes sense.
    examiner.assert_consistency()

    return examiner.linear_db, examiner.mouth_db
    

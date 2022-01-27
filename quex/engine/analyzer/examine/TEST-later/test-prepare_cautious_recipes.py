# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#
# PURPOSE: Test the production of a cautious recipe for acceptance considerations.
#
# Details on 'cautious recipes' see [DOC]. Brief: A cautious recipe is a recipe
# for a mouth state, that actually has undetermined entries. Thus, ordinary
# interference cannot be applied. Cautious recipes take the place of
# undetermined recipes. Since, then all entry recipes are defined, ordinary
# interference produces a correct recipe that assumes that values are stored at
# state entry.
#
# Components of the mouth state's 'op(i)' which are constant do not trigger a 
# 'store/restore' behavior. The component can be overtaken to the output recipe.
#
# CORE TEST: 
#
#    -- Setup mouth state with undetermined entries in '.entry_recipe_db'.
#
#    -- Setup 'op(i)' for the mouth state.
#
#    -- ._prepare_cautious_recipe()
#         => .entry_recipe_db[p] = cautious recipe
#            for all predecessor state indices 'p'.
#
#    -- ordinary interference
#         => A correct output recipe.
#
# SCENARIOS: 'op(i)' = entry operation of the mouth state under test.
#
# (1) No 'op(i)' => Predecessor recipes become entry recipes.
#                => Undetermined recipes enforce 'store/restore' for all.
#
# (2) op(i) = Accept => Acceptance dominates 
#                       (op(i) = constant with respect to E_R.AcceptanceRegister)
#                    => Acceptance register does NOT restore
#                    => Position register restore
#
# (3) op(i) = StoreInput(x) => Position 'x' is not restored.
#                           => All other things are restored.
#
# (4) op(i) = Accept with Pre-Context => Acceptance does not dominate
#                                     => All registers restore
#
# CHOICES: n
#
# 'n' --> number of entries into state
#
# (C) Frank-Rene Schaefer
#______________________________________________________________________________
import os
import sys
sys.path.insert(0, os.environ["QUEX_PATH"])

from quex.engine.state_machine.core                             import DFA
from quex.engine.state_machine.state.core                       import DFA_State
from quex.engine.state_machine.state.single_entry               import SingleEntry
from quex.engine.state_machine.TEST_help.many_shapes import *
from quex.engine.analyzer.examine.TEST.helper                   import *
from quex.engine.analyzer.examine.acceptance                    import RecipeAcceptance
from quex.engine.analyzer.examine.core                          import Examiner
from quex.engine.misc.tools                                     import E_Values
from quex.constants import E_IncidenceIDs, E_AcceptanceCondition

if "--hwut-info" in sys.argv:
    print("Prepare Cautious Recipes;")
    print("CHOICES: 2, 3, 4, 5;")
    print("SAME;")
    sys.exit()

# choice = sys.argv[1]

def setup_mouth_with_undetermined_entries(examiner, EntryN, SomeRecipe0, SomeRecipe1):
    mouth  = MouthStateInfo(FromStateIndexSet=set(range(EntryN)))
    if EntryN > 0: mouth.entry_recipe_db[0] = None
    if EntryN > 1: mouth.entry_recipe_db[1] = SomeRecipe0
    if EntryN > 2: mouth.entry_recipe_db[2] = None
    if EntryN > 3: mouth.entry_recipe_db[3] = SomeRecipe1
    if EntryN > 4: mouth.entry_recipe_db[4] = None

    return mouth

def setup_state_operation(sm, CmdList, StateIndex):
    state = DFA_State()
    for cmd in CmdList:
        state.single_entry.add(cmd)
    sm.states[StateIndex] = state

def setup(EntryN, StateOperation):
    sm        = DFA()
    examiner  = Examiner(sm, RecipeAcceptance)

    si = 1111
    setup_state_operation(sm, StateOperation, si) 
    operation = sm.states[si].single_entry

    examiner.linear_db[sm.init_state_index] = LinearStateInfo()

    predecessor0_recipe  = RecipeAcceptance([SeAccept(0)], 
                                            {E_IncidenceIDs.CONTEXT_FREE_MATCH: 0,
                                             10: -1,      # same for both / no restore
                                             11: -2,      # unequal for both
                                             12: E_Values.RESTORE,    # same for both / restore same
                                             13: E_Values.RESTORE,    # same for both / restore differs
                                             21:  0,       # no present in other                 
                                            }, 
                                            {(E_R.PositionRegister, 12): 0,
                                             (E_R.PositionRegister, 13): 0
                                            }) 
    recipe0              = examiner.recipe_type.accumulation(predecessor0_recipe, operation)
    predecessor1_recipe  = RecipeAcceptance([SeAccept(1)], 
                                            {E_IncidenceIDs.CONTEXT_FREE_MATCH: 0,
                                             10: -1,      # same for both / no restore
                                             11: -3,      # unequal for both
                                             12: E_Values.RESTORE,    # same for both / restore same
                                             13: E_Values.RESTORE,    # same for both / restore differs
                                             22:  0,       # no present in other                 
                                            }, 
                                            {(E_R.PositionRegister, 12): 0, 
                                             (E_R.PositionRegister, 13): 1, 
                                            })
    recipe1              = examiner.recipe_type.accumulation(predecessor1_recipe, operation)

    mouth    = setup_mouth_with_undetermined_entries(examiner, EntryN, recipe0, recipe1)
    examiner.mouth_db[si] = mouth

    mouth.required_variable_set = set([
        E_R.AcceptanceRegister,
        (E_R.PositionRegister, E_IncidenceIDs.CONTEXT_FREE_MATCH),
        (E_R.PositionRegister, 10),
        (E_R.PositionRegister, 11),
        (E_R.PositionRegister, 12),
        (E_R.PositionRegister, 13),
        (E_R.PositionRegister, 21),
        (E_R.PositionRegister, 22),
        (E_R.PositionRegister, 4711),
    ])
    assert set(examiner.mouth_db).isdisjoint(examiner.linear_db), \
           "%s intersects with %s" % (set(examiner.mouth_db), set(examiner.linear_db))
    return examiner, si

def test(Name, EntryN, StateOperation):
    print("_" * 80)
    print(Name)
    print()
    examiner, si = setup(EntryN, StateOperation)
    examiner._prepare_cautious_recipe(si)
    examiner._interference([si])
    print_interference_result(examiner.mouth_db)

# This module may be included by another test. So, check whether it is run
# independently.
if __name__ == "__main__":
    entry_n = int(sys.argv[1])
    test("(1) No op(i)",                           entry_n, [])
    test("(2) op(i) = Accept without pre-context", entry_n, [SeAccept(4711)])
    test("(3) op(i) = StoreInputPosition",         entry_n, [SeStoreInputPosition(4711)])
    test("(4) Accept with pre-context",            entry_n, [SeAccept(4711, 33)])

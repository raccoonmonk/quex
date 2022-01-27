# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
#! /usr/bin/env python
import os
import sys
sys.path.insert(0, os.environ["QUEX_PATH"])

from quex.engine.state_machine.core                             import DFA
from quex.engine.state_machine.TEST_help.many_shapes import *
from quex.engine.analyzer.examine.TEST.helper                   import *
from quex.engine.analyzer.examine.acceptance                    import RecipeAcceptance
from quex.engine.analyzer.examine.core                          import Examiner
from quex.constants import E_IncidenceIDs, E_AcceptanceCondition

if "--hwut-info" in sys.argv:
    print("Resolve Without Dead-Lock Resolution;")
    print("CHOICES: %s;" % get_sm_shape_names())
    sys.exit()

name             = sys.argv[1]
sm, state_n, pic = get_sm_shape_by_name(name)

print(pic)

# add_SeAccept(sm, sm.init_state_index, E_IncidenceIDs.MATCH_FAILURE)
add_SeStoreInputPosition(sm, 1, 77)
add_SeAccept(sm, 1, 1, 111)
add_SeAccept(sm, 3, 33, 333)
add_SeAccept(sm, 4, 44)
add_SeAccept(sm, 6, 66, 666)
# Post-Context: Store in '1', restore in '7'
add_SeAccept(sm, 7, 77, None, True)
print()

examiner        = Examiner(sm, RecipeAcceptance)
examiner.categorize()
springs         = examiner.setup_initial_springs()
remainder       = examiner.resolve(springs)

print("Unresolved Mouth States:")
print("   %s" % sorted(list(remainder)))
print()
print("Linear States:")
for si, info in examiner.linear_db.items():
    print_recipe(si, info.recipe)

print("Mouth States (Resolved):")
for si, info in examiner.mouth_db.items():
    if si in remainder: continue
    print_recipe(si, info.recipe)

print("Mouth States (Unresolved):")
for si, info in examiner.mouth_db.items():
    if si not in remainder: continue
    print_entry_recipe_db(si, info.entry_recipe_db)

print()
print("Horizon:", sorted(list(examiner.get_horizon(list(examiner.mouth_db.keys())))))

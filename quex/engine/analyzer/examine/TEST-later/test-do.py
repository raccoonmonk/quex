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
import quex.engine.analyzer.examine.core                        as     examination
from quex.constants import E_IncidenceIDs, E_AcceptanceCondition

if "--hwut-info" in sys.argv:
    print("Complete Process;")
    print("CHOICES: %s;" % get_sm_shape_names())
    sys.exit()

name             = sys.argv[1]
sm, state_n, pic = get_sm_shape_by_name(name)

print(pic)

add_SeStoreInputPosition(sm, sm.init_state_index, 100)
add_SeStoreInputPosition(sm, 1, 11111)
add_SeAccept(sm, 1, 11, 111)
add_SeAccept(sm, 2, 22, 222)
add_SeAccept(sm, 3, 33)
add_SeAccept(sm, 4, 44)
add_SeAccept(sm, 5, 55)
# Post-Context: Store in '0', restore in '6'
add_SeAccept(sm, 6, 66, 666, True)
# Post-Context: Store in '1', restore in '7'
add_SeAccept(sm, 7, 77, None, True)
print()

linear_db, mouth_db = examination.do(sm, RecipeAcceptance)
all_set = set(linear_db.keys())
all_set.update(iter(mouth_db.keys()))

print("All states present in 'sm' are either linear states or mouth states? ", end=' ')
print(all_set == set(sm.states.keys()))
print("There are no undetermined mouth states? ", end=' ')
print(len([x for x in mouth_db.values() if x.recipe is None]) == 0)
print("There are no undetermined entry recipes into mouth states? ", end=' ')
for mouth in mouth_db.values():
    for recipe in mouth.entry_recipe_db.values():
        if recipe is None: 
            print(False) 
            break
else:
    print(True)

print("Linear States: ", end=' ')
print(sorted(linear_db.keys()))
print("Mouth States: ", end=' ')
print(sorted(mouth_db.keys()))
print()
print()
print("Linear States:")
for si, info in linear_db.items():
    print_recipe(si, info.recipe)

# print "Mouth States:"
print_interference_result(mouth_db, Prefix="")


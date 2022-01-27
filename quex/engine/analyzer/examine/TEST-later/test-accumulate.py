# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
import os
import sys
sys.path.insert(0, os.environ["QUEX_PATH"])

from quex.engine.state_machine.core                  import DFA
from quex.engine.operations.se_operations            import SeAccept
from quex.engine.state_machine.TEST_help.many_shapes import *
from quex.engine.analyzer.examine.TEST.helper        import *
from quex.engine.analyzer.examine.acceptance         import RecipeAcceptance
from quex.engine.analyzer.examine.core               import Examiner
from quex.constants import E_IncidenceIDs

if "--hwut-info" in sys.argv:
    print("Accumulation;")
    print("CHOICES: %s;" % get_sm_shape_names())
    sys.exit()

sm, state_n, pic = get_sm_shape_by_name(sys.argv[1])

print(pic)

sm.get_init_state().single_entry.add(SeAccept(4711, 33))
# sm.get_init_state().single_entry.add(SeAccept(E_IncidenceIDs.MATCH_FAILURE))

examiner        = Examiner(sm, RecipeAcceptance)
examiner.categorize()
springs         = examiner.setup_initial_springs()
mouth_ready_set = examiner._accumulate(springs)

print("Mouths ready for interference:")
print("   %s" % sorted(list(mouth_ready_set)))
print()
print("Linear States:")
for si, info in sorted(examiner.linear_db.items()):
    print_recipe(si, info.recipe)

print("Mouth States:")
for si, info in sorted(examiner.mouth_db.items()):
    print_recipe(si, info.recipe)
    for predecessor_si, entry_recipe in info.entry_recipe_db.items():
        print("  from %s:" % predecessor_si)
        print(entry_recipe)


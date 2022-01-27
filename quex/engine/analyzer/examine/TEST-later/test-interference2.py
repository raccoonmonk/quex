# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
import os
import sys
sys.path.insert(0, os.environ["QUEX_PATH"])

from quex.engine.state_machine.core                             import DFA
from quex.engine.operations.se_operations                       import SeAccept
from quex.engine.state_machine.TEST_help.many_shapes import *
from quex.engine.analyzer.examine.TEST.helper                   import *
from quex.engine.analyzer.examine.state_info                    import *
from quex.engine.analyzer.examine.acceptance                    import RecipeAcceptance
from quex.engine.analyzer.examine.core                          import Examiner
from quex.constants import E_AcceptanceCondition
from copy import deepcopy

if "--hwut-info" in sys.argv:
    print("Interference: Inhomogeneous Acceptance;")
    print("CHOICES: 2-entries, 3-entries;")
    print("SAME;")
    sys.exit()

choice  = sys.argv[1].split("-")
entry_n = int(choice[0])

scheme_restore  = [ 
    RecipeAcceptance.RestoreAcceptance 
]
scheme_simple   = [ 
    get_SeAccept(1111, None, False) 
]
scheme_simple2  = [ 
    get_SeAccept(2222, 22,                  True) 
]
scheme_list     = [ 
    get_SeAccept(3333, 33, True), 
    get_SeAccept(4444, 44, True), 
    get_SeAccept(5555, None, True) 
]

examiner = Examiner(DFA(), RecipeAcceptance)
# For the test, only 'examiner.mouth_db' and 'examiner.recipe_type'
# are important.
examiner.mouth_db[1] = get_MouthStateInfoAcceptance(entry_n, scheme_restore, False)
examiner.mouth_db[2] = get_MouthStateInfoAcceptance(entry_n, scheme_simple, False)
examiner.mouth_db[3] = get_MouthStateInfoAcceptance(entry_n, scheme_simple2, False)
examiner.mouth_db[4] = get_MouthStateInfoAcceptance(entry_n, scheme_list, False)

examiner._interference(set([1, 2, 3, 4]))

print_interference_result(examiner.mouth_db)

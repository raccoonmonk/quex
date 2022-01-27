# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
#! /usr/bin/env python
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
from quex.constants import E_AcceptanceCondition, E_R, E_IncidenceIDs
from copy import deepcopy

if "--hwut-info" in sys.argv:
    print("Interference: Inhomogeneous SnapshotMap;")
    print("CHOICES: 2-entries, 3-entries;")
    print("SAME;")
    sys.exit()

choice  = sys.argv[1].split("-")
entry_n = int(choice[0])

ip_offset_scheme_0 = {}
ip_offset_scheme_1 = { 0: -1 } 
ip_offset_scheme_2 = { 0: -1, 1: -2 }
ip_offset_scheme_3 = { 0: -1, 1: -2, 2: -3 }

acceptance_scheme_0 = [ 
    RecipeAcceptance.RestoreAcceptance 
]
acceptance_scheme_1 = [ 
    SeAccept(1111, None, False) 
]
acceptance_scheme_2 = [ 
    SeAccept(2222, None, True) 
]
acceptance_scheme_3 = [ 
    SeAccept(3333, 33, True), 
    SeAccept(4444, 44, True), 
    SeAccept(5555, None, True) 
]


examiner = Examiner(DFA(), RecipeAcceptance)

# For the test, only 'examiner.mouth_db' and 'examiner.recipe_type'
# are important.
examiner.mouth_db[1] = get_MouthStateInfoSnapshotMap(entry_n, acceptance_scheme_0, ip_offset_scheme_0)
examiner.mouth_db[2] = get_MouthStateInfoSnapshotMap(entry_n, acceptance_scheme_1, ip_offset_scheme_1)
examiner.mouth_db[3] = get_MouthStateInfoSnapshotMap(entry_n, acceptance_scheme_2, ip_offset_scheme_2)
examiner.mouth_db[4] = get_MouthStateInfoSnapshotMap(entry_n, acceptance_scheme_3, ip_offset_scheme_3)

examiner._interference(set([1, 2, 3, 4]))

print_interference_result(examiner.mouth_db)


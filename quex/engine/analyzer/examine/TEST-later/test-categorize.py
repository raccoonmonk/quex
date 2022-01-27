# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
#! /usr/bin/env python
import os
import sys
sys.path.insert(0, os.environ["QUEX_PATH"])

from quex.engine.state_machine.core                             import DFA
from quex.engine.state_machine.TEST_help.many_shapes import *
from quex.engine.analyzer.examine.acceptance                    import RecipeAcceptance
from quex.engine.analyzer.examine.core                          import Examiner

if "--hwut-info" in sys.argv:
    print("Categorize into Linear and Mouth States")
    print("CHOICES: %s;" % get_sm_shape_names())
    sys.exit()

sm, state_n, pic = get_sm_shape_by_name(sys.argv[1])

examiner = Examiner(sm, RecipeAcceptance)
examiner.categorize()

if "pic" in sys.argv:
    print(pic)

print("Linear States:", list(examiner.linear_db.keys()))
print("Mouth  States:", list(examiner.mouth_db.keys()))

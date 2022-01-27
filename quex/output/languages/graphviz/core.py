# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.algebra.reverse          as     reverse
import quex.engine.state_machine.construction.combination as     combination
from   quex.engine.misc.file_operations                   import write_safely_and_close
import quex.output.transform_to_encoding                  as     transform_to_encoding

from   quex.blackboard import setup as Setup


class Generator:
    def __init__(self, Mode):
        self.mode = Mode
        self.file_name_main        = "%s.dot"             % self.mode.name
        self.file_name_pre_context = "%s-pre-context.dot" % self.mode.name
        self.file_name_bipd_db     = dict( 
            (sm.get_id(), "%s_%s\.dot" % (Mode.name, sm.get_id()))
            for sm in Mode.bipd_sm_to_be_reversed_db.values()
        )

    def do(self, Option="utf8"):
        """Prepare output in the 'dot' language, that graphviz uses."""
        assert Option in ["utf8", "hex"]
        sm = combination.do(self.mode.core_sm_list)
        sm = transform_to_encoding.do(sm, self.mode.core_sm_list)
        self.__do(sm, self.file_name_main, Option)

        if self.mode.pre_context_sm_to_be_reversed_list:
            sm_list = [ reverse.do(sm) for sm in self.mode.pre_context_sm_to_be_reversed_list ]
            sm = combination.do(sm_list, FilterDominatedOriginsF=False)
            sm = transform_to_encoding.do(sm, sm_list)
            self.__do(sm, self.file_name_pre_context, Option)

        if self.mode.bipd_sm_to_be_reversed_db:
            for sm in self.mode.bipd_sm_to_be_reversed_db.values():
                file_name = self.file_name_bipd_db[sm.get_id()] 
                reversed_sm = reverse.do(transform_to_encoding.do(sm))
                self.__do(reversed_sm, file_name, Option)

    def __do(self, state_machine, FileName, Option="utf8"):
        dot_code = state_machine.get_graphviz_string(NormalizeF=Setup.normalize_f, Option=Option)
        write_safely_and_close(FileName, dot_code)


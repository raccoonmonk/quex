# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.codec_db.core as codec_db
from   quex.engine.state_machine.transformation.base import EncodingTrafo
from   quex.engine.misc.interval_handling            import NumberSet_All, \
                                                            NumberSet

import os
import math

class EncodingTrafoByTable(EncodingTrafo, list):
    DEFAULT_LEXATOM_TYPE_SIZE = None # Byte

    """Provides the information about the relation of character codes in a 
    particular coding to unicode character codes. It is provided in the 
    following form:

           # Codec Values                 Unicode Values
           [ (Source0_Begin, Source0_End, TargetInterval0_Begin), 
             (Source1_Begin, Source1_End, TargetInterval1_Begin),
             (Source2_Begin, Source2_End, TargetInterval2_Begin), 
             ... 
           ]

    """
    def __init__(self, Codec=None, FileName=None, ExitOnErrorF=True):
        assert Codec is not None or FileName is not None

        if FileName is not None:
            file_name  = os.path.basename(FileName)
            file_name, \
            dumped_ext = os.path.splitext(file_name)
            codec_name = file_name.replace(" ", "_").replace("\t", "_").replace("\n", "_")
            file_name  = FileName
        else:
            codec_name, \
            file_name   = codec_db.get_file_name_for_codec_alias(Codec)

        source_set, drain_set = codec_db.load(self, file_name, ExitOnErrorF)

        # With 'table' translation a code point is translated into a single 
        # unit. Thus, only the error range for code unit '0' is determined.
        error_range_by_code_unit_db = {
           0: drain_set.get_complement(NumberSet_All()) # Adapted later
        }

        self.DEFAULT_LEXATOM_TYPE_SIZE = int(math.log(drain_set.least_greater_bound(), 256) + 1.0)

        EncodingTrafo.__init__(self, codec_name, source_set, 
                               error_range_by_code_unit_db)

    def do_transition(self, from_target_map, FromSi, ToSi, BadLexatomSi):
        """Translates to transition 'FromSi' --> 'ToSi' inside the state
        machine according to the translation table.

        'BadLexatomSi' is ignored. This argument is only of interest if
        intermediate states are to be generated. This it not the case for this
        type of transformation.

        RETURNS: [0] True if complete, False else.
                 [1] StateDb to be added (always None, here)
        """
        number_set = from_target_map[ToSi]

        # 'transform_by_table' adapts the 'number_set' in the 'from_target_map'
        # and returns 'True' if and only if the transformation was complete.
        verdict_f = number_set.transform_by_table(self)

        if number_set.is_empty():
            del from_target_map[ToSi]

        return verdict_f, None

    def _do_single(self, Code): 
        """Unicode character is translated to itself.
        """
        number_set = NumberSet.from_range(Code, Code+1)
        number_set.transform_by_table(self)

        # A single code element can only produce a single character!
        assert number_set.has_size_one()
        return [ number_set.get_the_only_element() ]


# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.setup                   import NotificationDB
from   quex.input.code.base               import SourceRef, \
                                                 SourceRef_DEFAULT
from   quex.engine.misc.tools             import typed
from   quex.engine.misc.interval_handling import NumberSet
from   quex.engine.counter                import CountAction, \
                                                 CountActionMap, \
                                                 cc_type_name_db
import quex.engine.misc.error             as     error

from   quex.constants  import E_CharacterCountType
from   quex.blackboard import setup as Setup

from   collections import defaultdict
from   operator    import itemgetter

class CountActionMap_Builder(object):
    """Builder Class for 'CountActionMap'

       .add()         adds an entry about a character set and how it is counted.
       .define_else() adds an entry about how to count the remaining characters.
       .finalize()    returns the result: a 'CountActionMap'.
    ___________________________________________________________________________
    """
    __slots__ = ("__map", "__else")
    def __init__(self):
        """Primarily, the '__map' member stores the list of associations between
        character sets and the count command entry. The '__else' contains the 
        count command which waits to be applied to the remaining set of characters.
        """
        self.__map  = CountActionMap()
        self.__else = None

    def add(self, CharSet, CC_Type, Value, sr):
        if CharSet.is_empty(): 
            error.log("Empty character set found for '%s'." % cc_type_name_db[CC_Type], sr)
        elif CC_Type == E_CharacterCountType.GRID:
            self.__check_grid_specification(Value, sr)
        self.__check_intersection(CC_Type, CharSet, sr)
        self.__map.append((CharSet, CountAction(CC_Type, Value, sr)))

    @typed(sr=SourceRef, Identifier=E_CharacterCountType)
    def define_else(self, CC_Type, Value, sr):
        """Define the '\else' character set which is resolved AFTER everything has been 
        defined.
        """
        if self.__else is not None:
            error.log("'\\else has been defined more than once.", sr, 
                      DontExitF=True)
            error.log("Previously, defined here.", self.__else.sr)
        self.__else = CountAction(CC_Type, Value, sr)

    def finalize(self, GlobalMin, GlobalMax, SourceReference, ForLineColumnCountF=False):
        """After all count commands have been assigned to characters, the 
        remaining character set can be associated with the 'else-CountAction'.
        """
        assert self.__map is not None, \
               ".finalize() has been called more than once with same builder."
        if self.__else is None: 
            else_cmd = CountAction(E_CharacterCountType.COLUMN, 1, SourceRef_DEFAULT)
            error.warning("No '\else' defined in counter setup. Assume '\else => columns 1;'", SourceReference, 
                          SuppressCode=NotificationDB.warning_counter_setup_without_else)
        else:                   
            else_cmd = self.__else
        
        remaining_set = self.__get_remaining_set(GlobalMin, GlobalMax)
        if not remaining_set.is_empty():
            self.__map.append((remaining_set, else_cmd))

        result = self.__map
        self.__map  = None
        self.__else = None
        return result

    def __check_intersection(self, CcType, CharSet, sr):
        """Check whether the given character set 'CharSet' intersects with 
        a character set already mentioned in the map. Depending on the CcType
        of the new candidate certain count commands may be tolerated, i.e. 
        their intersection is not considered.
        """
        # find an entry that occupies the given 'CharSet'
        for character_set, candidate in self.__map:
            if character_set.has_intersection(CharSet): 
                _error_set_intersection(CcType, candidate, sr)
                break

    def __get_remaining_set(self, GlobalMin, GlobalMax):
        """Return the set of characters which are not associated with count commands.
        Restrict the operation to characters from GlobalMin to GlobalMax (inclusively).
        """
        superset = NumberSet()
        for character_set, info in self.__map:
            superset.unite_with(character_set)
        result = superset.get_complement(Setup.buffer_encoding.source_set)

        result.cut_lesser(GlobalMin)
        result.cut_greater_or_equal(GlobalMax)
        return result

    def __check_grid_specification(self, Value, sr):
        if   Value == 0: 
            error.log("A grid count of 0 is nonsense. May be define a space count of 0.", sr)
        elif Value == 1:
            error.warning("Indentation grid counts of '1' are equivalent of to a space\n" + \
                          "count of '1'. The latter is faster to compute.",
                          sr)

    def __str__(self):
        def _db_to_text(title, CountOpInfoList):
            txt = "%s:\n" % title
            for character_set, info in sorted(CountOpInfoList, key=lambda x: x[0].minimum()):
                if type(info.value) in [str, str]:
                    txt += "    %s by %s\n" % (info.value, character_set.get_utf8_string())
                else:
                    txt += "    %3i by %s\n" % (info.value, character_set.get_utf8_string())
            return txt

        db_by_name = defaultdict(list)
        for character_set, info in self.__map:
            name = cc_type_name_db[info.cc_type]
            db_by_name[name].append((character_set, info))

        txt = [
            _db_to_text(cname, count_command_info_list)
            for cname, count_command_info_list in sorted(iter(db_by_name.items()), key=itemgetter(0))
        ]
        return "".join(txt)

def _error_set_intersection(CcType, Before, sr):
    global cc_type_name_db

    error.log("The character set defined in '%s' intersects" % (cc_type_name_db[CcType]),
              sr, DontExitF=True, WarningF=False)
    error.log("with '%s' at this place." % cc_type_name_db[Before.cc_type], 
              Before.sr, DontExitF=False, WarningF=False)


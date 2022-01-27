# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""This implements the basic algorithm for caseless matching
   as described in Unicode Standard Annex #21 "CASE MAPPINGS", Section 1.3.

"""
import quex.engine.codec_db.unicode.parser as     ucs_db_parser
from   quex.engine.misc.interval_handling  import Interval
from   collections import defaultdict

class CaseFoldDb:
    def __init__(self):
        self.lower_to_upper = defaultdict(list)
        self.upper_to_lower = defaultdict(list)

    def get_fold(self, CharacterCode):
        """Get lower and uppercase for a given character code.
        """
        result = []

        for fold in self.upper_to_lower[CharacterCode]:
            if fold not in result: result.append(fold)

        for fold in self.lower_to_upper[CharacterCode]:
            if fold not in result: result.append(fold)

        return result

# A number set shall allow us to judge quickly what characters
# or intervals are subject to case folding.
# covering_set = None

class Db:
    CS    = None
    F     = None
    T     = None
    total = None

    @classmethod
    def init(cls):
        if cls.CS is not None: return

        cls.CS = CaseFoldDb() # common mappings (simple and full)
        cls.F  = CaseFoldDb() # full case folding -> multiple characters sequence
        cls.T  = CaseFoldDb() # turkish case folding to replace normal mapping

        table = ucs_db_parser.parse_table("CaseFolding.txt", 
                                          NumberColumnList=[0], 
                                          NumberListColumnList=[2])

        dbDict = { "C": cls.CS, "S": cls.CS, "F": cls.F, "T": cls.T }

        for row in table:
            upper  = row[0]; assert isinstance(upper, int)
            status = row[1]
            lower  = row[2]; assert isinstance(lower, list)
            sub    = dbDict[status]

            if len(lower) == 1:
                sub.upper_to_lower[upper].append((lower[0],))  # one character
                sub.lower_to_upper[lower[0]].append((upper,))
            elif status == "F":
                sub.upper_to_lower[upper].append(tuple(lower)) # multiple characters
                # Only use scalar values as dictionary keys --> do
                # dot fold multi-value characters to single characters.

def get_fold_set(character_code, flags):
    return get_fold_set_for_interval(Interval(character_code), flags)

def get_fold_set_for_interval(interval, flags):
    """Returns all characters to which the specified CharacterCode
       folds. The flag list corresponds to the flags defined in the
       Unicode Database status field, i.e.

       [Extract from Unicode Document]
         C: common case folding, common mappings shared by both simple 
            and full mappings.
         F: full case folding, mappings that cause strings to grow in length. 
         S: simple case folding, mappings to single characters where different 
            from F.
         T: special case for uppercase I and dotted uppercase I
           - For non-Turkic languages, this mapping is normally not used.
           - For Turkic languages (tr, az), this mapping can be used instead of
             the normal mapping for these characters.  Note that the Turkic
             mappings do not maintain canonical equivalence without additional
             processing. See the discussions of case mapping in the Unicode
             Standard for more information.

    RETURNS: List of character codes.
    """
    s_flag = "s" in flags   # simple case fold
    m_flag = "m" in flags   # multi character case fold
    t_flag = "t" in flags   # 'turkish' special case fold

    Db.init()

    forbidden_fold_set = set()
    if t_flag: # Turkish case folding is different
        forbidden_fold_set.update(list(Db.T.upper_to_lower.keys()) + list(Db.T.lower_to_upper.keys()))

    worklist = list(range(interval.begin, interval.end))
    result   = set((x,) for x in worklist)
    while worklist:
        character_code = worklist.pop()

        folded_set = []
        if character_code not in forbidden_fold_set:
            if s_flag: folded_set.extend(Db.CS.get_fold(character_code))
            if m_flag: folded_set.extend(Db.F.get_fold(character_code))
        if t_flag:     folded_set.extend(Db.T.get_fold(character_code))

        # All 'partners' that are not yet treated need to be added
        # to the 'todo list'. All partners that are not yet in result
        # need to be added.
        worklist.extend(x[0] for x in folded_set if len(x) == 1 and x not in result)
        result.update(folded_set)
       
    return sorted(result)

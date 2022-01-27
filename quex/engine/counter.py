# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# (C) Frank-Rene Schaefer
#
#        .--( LineColumnCount )--------------------------------.
#        |                                                     |
#        | + count_command_map (map: count command --> value)  |
#        '-----------------------------------------------------'
#
#
#        .--( IndentationCount ---> LineColumnCount )----------.
#        |                                                     |
#        | + whitespace_character_set                          |
#        | + bad_space_character_set                           |
#        | + sm_newline                                        |
#        | + sm_newline_suppressor                             |
#        | + sm_suspend_list                                   |
#        '-----------------------------------------------------'
#
# (C) Frank-Rene Schaefer
#______________________________________________________________________________                      

from   quex.input.code.base                        import SourceRef
from   quex.engine.operations.operation_list       import Op
from   quex.engine.misc.tools                      import typed, do_and_delete_if
from   quex.engine.misc.interval_handling          import NumberSet

from   quex.blackboard import setup as Setup
from   quex.constants  import E_CharacterCountType, \
                              E_R
from   collections     import namedtuple, defaultdict
from   operator        import itemgetter


cc_type_db = {
    "columns":  E_CharacterCountType.COLUMN,
    "lines":    E_CharacterCountType.LINE,
    "grid":     E_CharacterCountType.GRID,
}

cc_type_name_db = dict((value, key) for key, value in cc_type_db.items())

count_operation_db_without_reference = {
    E_CharacterCountType.COLUMN: lambda Parameter, Dummy=None, Dummy2=None: [
        Op.ColumnCountAdd(Parameter)
    ],
    E_CharacterCountType.GRID:   lambda Parameter, Dummy=None, Dummy2=None: [
        Op.ColumnCountGridAdd(Parameter)
    ],
    E_CharacterCountType.LINE:   lambda Parameter, Dummy=None, Dummy2=None: [
        Op.LineCountAdd(Parameter),
        Op.AssignConstant(E_R.Column, 1),
    ],
}

count_operation_db_with_reference = {
    E_CharacterCountType.COLUMN: lambda Parameter, ColumnNPerCodeUnit, Dummy=None: [
    ],
    E_CharacterCountType.GRID:   lambda Parameter, ColumnNPerCodeUnit, Dummy=None: [
        Op.ColumnCountReferencePDeltaAdd(E_R.InputP, ColumnNPerCodeUnit, True),
        Op.ColumnCountGridAdd(Parameter),
        Op.ColumnCountReferencePSet(E_R.InputP)
    ],
    E_CharacterCountType.LINE:   lambda Parameter, ColumnNPerCodeUnit, Dummy=None: [
        Op.LineCountAdd(Parameter),
        Op.AssignConstant(E_R.Column, 1),
        Op.ColumnCountReferencePSet(E_R.InputP)
    ],
}

class CountAction(namedtuple("CountAction", ("cc_type", "value", "extra_value", "sr"))):
    def __new__(self, CCType, Value, sr=None, ExtraValue=None):
        return super(CountAction, self).__new__(self, CCType, Value, ExtraValue, sr)

    def get_OpList(self, ColumnCountPerChunk):
        if ColumnCountPerChunk is None:
            db = count_operation_db_without_reference
        else:
            db = count_operation_db_with_reference

        return db[self.cc_type](self.value, ColumnCountPerChunk, self.extra_value)

    def is_equal(self, Other):
        """Two Count Actions are equal, if the CC-Type and the Parameter are
        the same. The source reference (.sr) does not have to be the equal.
        """
        if   self.cc_type != Other.cc_type: return False
        elif self.value != Other.value:     return False
        else:                               return True

class CountActionMap(list):
    """Map: NumberSet --> CountAction
    """
    def clone(self):
        result = CountActionMap()
        for entry in self:
            result.append(entry)
        return result

    def prune(self, SuperSet):
        """Prune all NumberSets in the CountActionMap, so that they fit in the 
        'SuperSet'. If a NumberSets is not a subset of 'SuperSet' at all, then the
        according action is removed.
        """
        def do(element, SuperSet):
            character_set, count_action = element
            character_set.intersect_with(SuperSet)
            return character_set.is_empty()

        do_and_delete_if(self, do, SuperSet)

    def iterable_in_sub_set(self, SubSet):
        """Searches for CountInfo objects where the character set intersects
        with the 'SubSet' given as arguments. 

        YIELDS: [0] NumberSet where the trigger set intersects with SubSet
                [1] Related 'CountAction' object.
        """
        for character_set, count_action in self:
            intersection = SubSet.intersection(character_set)
            if intersection.is_empty(): continue
            yield intersection, count_action

    @typed(CharacterSet=NumberSet)
    def get_count_commands(self, CharacterSet):
        """Finds the count command for column, grid, and newline. This does NOT
        consider 'chunk number per character'. The consideration is on pure 
        character (unicode) level.
        
        RETURNS: [0] column increment (None, if none, -1 if undetermined)
                 [1] grid step size   (None, if none, -1 if undetermined)
                 [2] line increment   (None, if none, -1 if undetermined)

            None --> no influence from CharacterSet on setting.
            '-1' --> no distinct influence from CharacterSet on setting.
                     (more than one possible).

        NOTE: If one value not in (None, -1), then all others must be None.
        """

        db = {
            E_CharacterCountType.COLUMN: None,
            E_CharacterCountType.GRID:   None,
            E_CharacterCountType.LINE:   None,
        }

        for character_set, entry in self:
            if entry.cc_type not in db: 
                continue
            elif character_set.is_superset(CharacterSet):
                db[entry.cc_type] = entry.value
                break
            elif character_set.has_intersection(CharacterSet): 
                db[entry.cc_type] = -1     

        return db[E_CharacterCountType.COLUMN], \
               db[E_CharacterCountType.GRID], \
               db[E_CharacterCountType.LINE]

    def column_grid_line_iterable_pruned(self, CharacterSet):
        """Iterate over count command map. It is assumed that anything in the map
        is 'valid'. 
        """
        considered_set = (E_CharacterCountType.COLUMN, 
                          E_CharacterCountType.GRID, 
                          E_CharacterCountType.LINE)
        for character_set, info in self:
            if character_set.has_intersection(CharacterSet):
                if info.cc_type not in considered_set: continue
                yield character_set.intersection(CharacterSet), info

    def get_column_number_per_code_unit(self):
        """Considers the counter database which tells what character causes
        what increment in line and column numbers. However, only those characters
        are considered which appear in the CharacterSet. 

        RETURNS: None -- If there is NO distinct column increment.
                 >= 0 -- The increment of column number for every character
                         from CharacterSet.
        """
        CharacterSet = Setup.buffer_encoding.source_set
        column_incr_per_character = None
        number_set                = None
        for character_set, info in self.column_grid_line_iterable_pruned(CharacterSet):
            if info.cc_type != E_CharacterCountType.COLUMN: 
                continue
            elif column_incr_per_character is None:       
                column_incr_per_character = info.value
                number_set                = character_set
            elif column_incr_per_character == info.value: 
                number_set.unite_with(character_set)
            else:
                return None

        if column_incr_per_character is None:
            return None                       # TODO: return 0

        # HERE: There is only ONE 'column_n_increment' command. It appears on
        # the character set 'number_set'. If the character set is represented
        # by the same number of chunks, than the column number per chunk is
        # found.
        if not Setup.buffer_encoding.variable_character_sizes_f():
            return column_incr_per_character

        chunk_n_per_character = \
            Setup.buffer_encoding.lexatom_n_per_character(number_set) 
        if chunk_n_per_character is None:
            return None
        else:
            return float(column_incr_per_character) / chunk_n_per_character

    def is_equal(self, Other):
        if len(self) != len(Other):
            return False
        for x, y in zip(self, Other):
            x_number_set, x_count_action = x
            y_number_set, y_count_action = y
            if not x_number_set.is_equal(y_number_set):
                return False
            elif not x_count_action.is_equal(y_count_action):
                return False
        return True

    def __str__(self):
        def _db_to_text(title, CountCmdInfoList):
            txt = "%s:\n" % title
            for character_set, info in sorted(CountCmdInfoList, key=lambda x: x[0].minimum()):
                if type(info.value) in [str, str]:
                    txt += "    %s by %s\n" % (info.value, character_set.get_utf8_string())
                else:
                    txt += "    %3i by %s\n" % (info.value, character_set.get_utf8_string())
            return txt

        db_by_name = defaultdict(list)
        for character_set, info in self:
            name = cc_type_name_db[info.cc_type]
            db_by_name[name].append((character_set, info))

        txt = [
            _db_to_text(cname, count_command_info_list)
            for cname, count_command_info_list in sorted(iter(db_by_name.items()), key=itemgetter(0))
        ]
        return "".join(txt)

class IndentationCount_Pre:
    @typed(sr=SourceRef,PatternListSuspend=list)
    def __init__(self, SourceReference,  
                 PatternWhitespace, PatternBadSpace,
                 PatternNewline, PatternSuppressedNewline, 
                 PatternListSuspend):
        """BadSpaceCharacterSet = None, if there is no definition of bad space.
        """
        self.sr                         = SourceReference
        self.pattern_whitespace         = PatternWhitespace
        self.pattern_badspace           = PatternBadSpace
        self.pattern_newline            = PatternNewline
        self.pattern_suppressed_newline = PatternSuppressedNewline
        self.pattern_suspend_list       = PatternListSuspend

    def clone(self):
        def cloney(X):
            if X is None: return None
            else:         return X.clone()
        return IndentationCount_Pre(self.sr,
                PatternWhitespace        = cloney(self.pattern_whitespace), 
                PatternBadSpace          = cloney(self.pattern_badspace),
                PatternNewline           = cloney(self.pattern_newline), 
                PatternSuppressedNewline = cloney(self.pattern_suppressed_newline), 
                PatternListSuspend       = [cloney(x) for x in self.pattern_suspend_list])

    def __str__(self):
        def sm_str(Name, Pattern):
            if Pattern is None: return ""
            Sm = Pattern.get_cloned_sm()
            if Sm is None: return ""
            msg = "%s:\n" % Name
            if Sm is None: 
                msg += "    <none>\n"
            else:          
                msg += "    %s\n" % Sm.get_string(NormalizeF=True, Option="utf8").replace("\n", "\n    ").strip()
            return msg

        txt = [ 
            sm_str("Whitespace",    self.pattern_whitespace),
            sm_str("Bad",           self.pattern_badspace),
            sm_str("Newline",       self.pattern_newline),
            sm_str("Suppressed Nl", self.pattern_suppressed_newline)
        ]

        if self.pattern_suspend_list is not None:
            txt.extend(
                sm_str("Comment", p)
                for p in self.pattern_suspend_list
            )

        return "".join(txt)



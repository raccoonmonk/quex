# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.input.files.specifier.counter    as     counter
from   quex.input.files.specifier.counter    import LineColumnCount_Default
import quex.input.regular_expression.core    as     regular_expression
from   quex.input.regular_expression.pattern import Pattern_Prep
from   quex.input.code.base                  import SourceRef
import quex.engine.state_machine.algebra.intersection as intersection
from   quex.engine.misc.tools                import all_isinstance
from   quex.engine.misc.tools                import typed, \
                                                    flatten
import quex.engine.misc.error                as     error
from   quex.engine.misc.file_in              import check, \
                                                    skip_whitespace, \
                                                    read_identifier, \
                                                    EndOfStreamException

import quex.blackboard as     blackboard

import types
from   copy import copy
from   itertools import combinations

class SkipRangeData(object): 
    __slots__ = ("opener_pattern",            "closer_pattern", 
                 "opener_suppressor_pattern", "closer_suppressor_pattern")
    def __init__(self, OpenerPattern,     CloserPattern, 
                 OpenerSuppressorPattern, CloserSuppressorPattern):
        # Default: SuppressedCloserSm = \Empty
        # Default: SuppressedOpenerSm = \Empty
        # Suppressed opener is only for skip nested range.
        self.opener_pattern            = OpenerPattern
        self.closer_pattern            = CloserPattern
        self.closer_suppressor_pattern = CloserSuppressorPattern
        self.opener_suppressor_pattern = OpenerSuppressorPattern

    def clone(self):
        return SkipRangeData(OpenerPattern           = self.opener_pattern.clone(),
                             CloserPattern           = self.closer_pattern.clone(),
                             OpenerSuppressorPattern = self.opener_suppressor_pattern.clone(),
                             CloserSuppressorPattern = self.closer_suppressor_pattern.clone())

class OptionSetting:
    __slots__ = ("value", "sr", "mode_name")
    def __init__(self, Value, Sr, ModeName):
        self.value     = Value
        self.sr        = Sr
        self.mode_name = ModeName

    def clone(self):
        def cloney(X):
            if hasattr(X, "clone"): 
                return X.clone()
            else:
                assert type(X) in (str, int, int, float)
                return X
        if   type(self.value) == list:   new_value = [cloney(x) for x in self.value]
        elif type(self.value) == tuple:  new_value = tuple(cloney(x) for x in self.value)
        else:                            new_value = cloney(self.value)
        return OptionSetting(new_value, self.sr, self.mode_name)

#-----------------------------------------------------------------------------------------
# mode_option_info_db: Information about properties of mode options.
#-----------------------------------------------------------------------------------------
class ModeOptionInfo:
    """A ModeOptionInfo is an element of mode_option_info_db."""
    def __init__(self, MultiDefinitionF, OverwriteF, Domain=None, Default=None, ListF=False, InheritedF=True):
        assert type(MultiDefinitionF) == bool
        assert type(OverwriteF) == bool
        assert type(ListF) == bool
        # self.name = Option see comment above
        self.multiple_definition_f = MultiDefinitionF # Can be defined multiple times?
        self.derived_overwrite_f   = OverwriteF       # Does derived definition overwrite base mode's definition?
        self.domain                = Domain
        self.__content_list_f      = ListF
        self.__default_value       = Default
        self.inherited_f           = InheritedF

    def single_setting_f(self):
        """If the option can be defined multiple times and is not overwritten, 
        then there is only one setting for a given name. Otherwise not."""
        return (not self.multiple_definition_f) or self.derived_overwrite_f

    def content_is_list(self):
        return self.__content_list_f

    def default_setting(self, ModeName):
        if self.__default_value is None:
            return None

        if isinstance(self.__default_value, types.FunctionType):
            content = self.__default_value()
        else:
            content = self.__default_value

        return OptionSetting(content, SourceRef(), ModeName)

mode_option_info_db = {
   # -- a mode can be 'inheritable', 'not inheritable', or 'only inheritable'.
   "inheritable":       ModeOptionInfo(False, True, ["no", "yes", "only"], Default="yes", InheritedF=False),
   # -- entry/exit restrictions
   "exit":              ModeOptionInfo(True, False, Default=[], ListF=True, InheritedF=True),
   "entry":             ModeOptionInfo(True, True,  Default=[], ListF=True, InheritedF=False),
   # -- 'skippers' that effectively skip ranges that are out of interest.
   "skip":              ModeOptionInfo(True, False), # "multiple: RE-character-set
   "skip_range":        ModeOptionInfo(True, False), # "multiple: RE-character-string RE-character-string
   "skip_nested_range": ModeOptionInfo(True, False), # "multiple: RE-character-string RE-character-string
   # -- indentation setup information
   "indentation":       ModeOptionInfo(False, False),
   # --line/column counter information
   "counter":           ModeOptionInfo(False, False, Default=LineColumnCount_Default),
}

class OptionDB(dict):
    """Database of Mode Options
    ---------------------------------------------------------------------------

                      option name --> [ OptionSetting ]

    If the 'mode_option_info_db[option_name]' mentions that there can be 
    no multiple definitions or if the options can be overwritten than the 
    list of OptionSetting-s must be of length '1' or the list does not exist.

    ---------------------------------------------------------------------------
    """
    def get(self, Key):                assert False, "'.get()' not supported. Use '.value()'"
    def __getitem__(self, Key):        assert False, "'[]' not supported. Use '.value()'"
    def __setitem__(self, Key, Value): assert False, "'[]' not supported. Use '.enter()'"

    @classmethod
    def from_BaseModeSequence(cls, BaseModeSequence):
        # BaseModeSequence[-1] = mode itself
        mode_name = BaseModeSequence[-1].name

        def setting_list_iterable(BaseModeSequence):
            for i, mode_pp in enumerate(BaseModeSequence):
                option_db = mode_pp.option_db
                for name, info in mode_option_info_db.items():
                    if not info.inherited_f and mode_pp.name != mode_name:
                        continue
                    setting_list = option_db.__get_setting_list(name)
                    if setting_list is None: continue
                    assert    (not mode_option_info_db[name].single_setting_f()) \
                           or (len(setting_list) == 1)  
                    yield name, setting_list

        result = cls()
        for name, setting_list in setting_list_iterable(BaseModeSequence):
            if name != mode_name: setting_list = [x.clone() for x in setting_list]
            result.__enter_setting_list(name, setting_list) 

        # Options which have not been set (or inherited) are set to the default value.
        for name, info in mode_option_info_db.items():
            if   name in result: continue
            elif info.default_setting(mode_name) is None: continue
            result.__enter_setting(name, info.default_setting(mode_name).clone())

        return result

    def enter(self, Name, Value, SourceReference, ModeName):
        """Enters a new definition of a mode option as it comes from the parser.
        At this point, it is assumed that the OptionDB belongs to one single
        ModeParsed and not to a base-mode accumulated Mode. Thus, one
        option can only be set once, otherwise an error is notified.
        """
        global mode_option_info_db
        # The 'verify_word_in_list()' call must have ensured that the following holds
        assert Name in mode_option_info_db

        if self.has(Name) and mode_option_info_db[Name].single_setting_f():
            error.log("Tag <%s: ...> has been defined more than once." % Name, 
                      SourceReference)

        # Is the option of the appropriate value?
        info = mode_option_info_db[Name]
        if info.domain is not None and Value not in info.domain:
            error.log("Tried to set value '%s' for option '%s'. " % (Value, Name) + \
                      "Though, possible for this option are only: %s." % repr(info.domain)[1:-1], 
                      SourceReference)

        setting = OptionSetting(Value, SourceReference, ModeName)
        self.__enter_setting(Name, setting)

    @typed(Setting=(None, OptionSetting))
    def __enter_setting(self, Name, Setting):
        """During building of a ModeParsed. Enters a OptionSetting safely into the 
        OptionDB. It checks whether it is already present.
        """
        info = mode_option_info_db[Name]
        assert (not info.content_is_list()) or     type(Setting.value) == list
        assert (    info.content_is_list()) or not type(Setting.value) == list

        if Name not in self:             dict.__setitem__(self, Name, [ Setting ])
        elif info.multiple_definition_f: dict.__getitem__(self, Name).append(Setting)
        else:                            self.__error_double_definition(Name, Setting)

    @typed(SettingList=[OptionSetting])
    def __enter_setting_list(self, Name, SettingList):
        """During construction of a 'real' Mode object from including consideration
        of base modes. Enter the given setting list, or extend.
        """
        info = mode_option_info_db[Name]
        if   Name not in self:           dict.__setitem__(self, Name, copy(SettingList))
        elif info.derived_overwrite_f:   dict.__setitem__(self, Name, SettingList)
        elif info.multiple_definition_f: dict.__getitem__(self, Name).extend(SettingList)
        else:                            self.__error_double_definition(Name, SettingList[0])

    def has(self, *OptionNameList):
        return any(dict.get(self, option_name) for option_name in OptionNameList)

    def __get_setting_list(self, Name):
        """RETURNS: [ OptionSetting ] for a given option's Name.

        This function does additional checks for consistency.
        """
        setting_list = dict.get(self, Name)
        if setting_list is None: return None

        assert isinstance(setting_list, list) 
        assert all_isinstance(setting_list, OptionSetting)
        assert (not mode_option_info_db[Name].single_setting_f()) or len(setting_list) == 1
        return setting_list

    def value(self, Name):
        """Only scalar options can be asked about their 'value'."""
        setting_list = self.__get_setting_list(Name)
        if setting_list is None: return None
        assert mode_option_info_db[Name].single_setting_f()

        scalar_value = setting_list[0].value
        assert not type(scalar_value) == list
        return scalar_value

    def value_list(self, Name):
        """The content of a value is a sequence, and the return value of this
        function is a concatenated list of all listed option setting values.
        """
        setting_list = self.__get_setting_list(Name)
        if setting_list is None: return None

        info = mode_option_info_db[Name]
        if info.content_is_list():
            result = flatten(
                x.value for x in setting_list
            )
        else:
            result = [ x.value for x in setting_list ]

        return result

    def __error_double_definition(self, Name, OptionNow):
        assert isinstance(OptionNow, OptionSetting)
        OptionBefore = dict.__getitem__(self, Name)[0]
        assert isinstance(OptionBefore, OptionSetting)

        txt = "Option '%s' defined twice in " % Name
        if OptionBefore.mode_name == OptionNow.mode_name:
            txt += "mode '%s'." % OptionNow.mode_name
        else:
            txt += "inheritance tree of mode '%s'." % OptionNow.mode_name
        error.log(txt, OptionNow.sr, DontExitF=True) 

        txt = "Previous definition was here"
        if OptionBefore.mode_name == OptionNow.mode_name:
            txt += " in mode '%s'." % OptionBefore.mode_name
        else:
            txt += "."
        error.log(txt, OptionBefore.sr.file_name, OptionBefore.sr.line_n)

def parse(fh, new_mode):
    """Parses a single mode option.

    RETURNS: [0] name of the option
             [1] setting of the option
    """

    identifier = read_option_start(fh)
    if identifier is None: return None, None

    error.verify_word_in_list(identifier, list(mode_option_info_db.keys()),
                              "mode option", fh)

    if   identifier == "skip":
        value = __parse_skip_option(fh, new_mode, identifier)

    elif identifier in ["skip_range", "skip_nested_range"]:
        value = __parse_range_skipper_option(fh, identifier, new_mode)
        
    elif identifier == "indentation":
        value = counter.parse_IndentationSetup(fh)
        blackboard.required_support_indentation_count_set()

    elif identifier == "counter":
        value = counter.parse_CountActionMap(fh)

    elif identifier in ("entry", "exit"):
        value = read_option_value(fh, ListF=True) # A 'list' of strings
    else:
        value = read_option_value(fh)             # A single string

    return identifier, value

def __parse_skip_option(fh, new_mode, identifier):
    """A skipper 'eats' characters at the beginning of a pattern that belong to
    a specified set of characters. A useful application is most probably the
    whitespace skipper '[ \t\n]'. The skipper definition allows quex to
    implement a very effective way to skip these regions.
    """
    pattern, \
    trigger_set = regular_expression.parse_character_set(fh, ">")

    skip_whitespace(fh)

    if fh.read(1) != ">":
        error.log("missing closing '>' for mode option '%s'." % identifier, fh)
    elif trigger_set.is_empty():
        error.log("Empty trigger set for skipper." % identifier, fh)

    pattern.set_pattern_string("<skip>")
    return pattern, trigger_set

def _assert_pattern_constaints(P, Name, fh):
    if not P:
        error.log("malformed regular expression for 'closer suppressor' in %s." 
                  % Name)
    elif P.has_post_context():
        error.log("%s contains post context." % Name, fh)
    elif P.has_pre_context():
        error.log("%s contains pre context." % Name, fh)

def __parse_range_skipper_option(fh, identifier, new_mode):
    """A non-nesting skipper can contain a full fledged regular expression as opener,
    since it only effects the trigger. Not so the nested range skipper-see below.
    """
    def _parse(Identifier, SubName, fh):
        skip_whitespace(fh)
        pattern = regular_expression.parse(fh, 
                                           Name=Identifier, Terminator=">", 
                                           AllowAcceptanceOnNothingF=False,
                                           AllowPreContextF=False)
        _assert_pattern_constaints(pattern, Identifier, fh)
        pattern.set_pattern_string("<%s %s>" % (Identifier, SubName))
        return pattern

    if identifier == "skip_nested_range": 
        arg_name_list = ("opener", "closer", "closer_suppressor", "opener_suppressor")
        not_intersect = ("opener", "closer", "closer_suppressor", "opener_suppressor")
    else:
        arg_name_list = ("opener", "closer", "closer_suppressor")
        not_intersect = (          "closer", "closer_suppressor")

    argument_db = {}
    for arg_name in arg_name_list:
        if check(fh, ">"): break
        argument_db[arg_name] = _parse(identifier, arg_name, fh)
    else:
        if not check(fh, ">"):
            error.log("missing closing '>' for '%s'" % identifier, fh)

    if len(argument_db) < 2:
        error.log("missing argument %i for '%s'" % (len(argument_db), identifier), fh)

    check_list = [name for name in not_intersect if name in argument_db]
    for i_name, k_name in combinations(check_list, 2):
        i_sm = argument_db[i_name].borrow_sm()
        k_sm = argument_db[k_name].borrow_sm()
        if not intersection.do([i_sm, k_sm]).is_Empty(): 
            error.log("%s: '%s' and '%s' match on common lexemes."
                      % (identifier, i_name, k_name), argument_db[i_name].sr)

    if "opener_suppressor" not in argument_db:
        argument_db["opener_suppressor"] = Pattern_Prep.Empty()

    if "closer_suppressor" not in argument_db:
        argument_db["closer_suppressor"] = Pattern_Prep.Empty()

    return SkipRangeData(argument_db["opener"],            argument_db["closer"], 
                         argument_db["opener_suppressor"], argument_db["closer_suppressor"])

def read_option_start(fh):
    skip_whitespace(fh)

    # (*) base modes 
    if fh.read(1) != "<": 
        return None

    skip_whitespace(fh)
    identifier = read_identifier(fh, OnMissingStr="Missing identifer after start of mode option '<'").strip()

    skip_whitespace(fh)
    if fh.read(1) != ":": error.log("missing ':' after option name '%s'" % identifier, fh)
    skip_whitespace(fh)

    return identifier

def read_option_value(fh, ListF=False):

    position = fh.tell()

    value = ""
    depth = 1
    while 1 + 1 == 2:
        try: 
            letter = fh.read(1)
        except EndOfStreamException:
            fh.seek(position)
            error.log("missing closing '>' of mode option.", fh)

        if letter == "<": 
            depth += 1
        if letter == ">": 
            depth -= 1
            if depth == 0: break
        value += letter

    if not ListF: return value.strip()
    else:         return [ x.strip() for x in value.split() ]


# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.misc.error           as     error
from   quex.engine.misc.tools           import typed
from   quex.engine.misc.file_operations import open_file_or_die
from   quex.engine.misc.file_in         import EndOfStreamException, \
                                               skip_whitespace, \
                                               check_or_die, \
                                               read_identifier, \
                                               read_namespaced_name, \
                                               check, \
                                               read_until_letter
from   quex.input.code.core             import CodeUser, \
                                               CodeUser_NULL
from   quex.input.code.base             import SourceRef, \
                                               SourceRef_VOID
import quex.input.files.code_fragment   as     code_fragment
from   quex.input.setup                 import E_Files, \
                                               NotificationDB
import quex.token_db                    as     token_db
from   quex.blackboard                  import setup as Setup, \
                                               Lng
from   collections import OrderedDict

token_type_code_fragment_db = { 
    "constructor":   CodeUser_NULL, 
    "destructor":    CodeUser_NULL,
    "copy":          None, 
    "body":          CodeUser_NULL,
    "header":        CodeUser_NULL,
    "footer":        CodeUser_NULL,
    "take_text":     None,
    "repetition_n":  None,
}

class TokenTypeDescriptorCore(object):
    __slots__ = ("class_name", "class_name_safe", "class_name_space",
                 "token_id_type_defined_f", "token_contains_token_id_f", "token_id_type", 
                 "open_for_derivation_f", "column_number_type", "line_number_type",
                 "token_repetition_n_member_name", "distinct_db", "union_db",
                 "constructor",  "destructor", "copy", "body", "header", "footer", 
                 "take_text", "repetition_n")
    """Object used during the generation of the TokenTypeDescriptor."""
    def __init__(self, Core=None):
        if Core is None:
            # Consistency is maintained via properties (see below constructor)

            self.class_name       = ""
            self.class_name_safe  = ""
            self.class_name_space = []
            # Consistency maintained via 'set_file_name/get_file_name'
            #    self.get/set_file_name() = Setup.output_token_class_file
            #    implementation           => Setup.output_token_class_file_implementation

            self.token_id_type_defined_f        = False
            self.open_for_derivation_f          = False
            self.token_contains_token_id_f      = True
            self.token_id_type                  = CodeUser("size_t", SourceRef())
            self.column_number_type             = CodeUser("size_t", SourceRef())
            self.line_number_type               = CodeUser("size_t", SourceRef())
            self.token_repetition_n_member_name = CodeUser("", SourceRef())

            self.distinct_db = OrderedDict() # See comment [MEMBER PACKAGING]
            self.union_db    = OrderedDict() # See comment [MEMBER PACKAGING]

            self.constructor  = CodeUser_NULL 
            self.destructor   = CodeUser_NULL
            self.copy         = None 
            self.body         = CodeUser_NULL
            self.header       = CodeUser_NULL
            self.footer       = CodeUser_NULL
            self.take_text    = None
            self.repetition_n = None

        else:
            # Consistency is maintained via properties (see below constructor)
            self.class_name       = Core.class_name
            self.class_name_safe  = Core.class_name_safe
            self.class_name_space = Core.class_name_space
            self.token_id_type    = Core.token_id_type

            # Consistency maintained via 'set_file_name/get_file_name'
            #    self.get/set_file_name() = Setup.output_token_class_file
            #    implementation           => Setup.output_token_class_file_implementation

            self.token_id_type_defined_f        = Core.token_id_type_defined_f
            self.open_for_derivation_f          = Core.open_for_derivation_f
            self.token_contains_token_id_f      = Core.token_contains_token_id_f
            self.column_number_type             = Core.column_number_type
            self.line_number_type               = Core.line_number_type
            self.token_repetition_n_member_name = Core.token_repetition_n_member_name

            self.distinct_db = Core.distinct_db
            self.union_db    = Core.union_db

            self.constructor  = Core.constructor 
            self.destructor   = Core.destructor  
            self.copy         = Core.copy        
            self.body         = Core.body        
            self.header       = Core.header      
            self.footer       = Core.footer      
            self.take_text    = Core.take_text   
            self.repetition_n = Core.repetition_n


    def set_file_name(self, FileName):
        ext = Lng.extension_db[E_Files.HEADER_IMPLEMTATION]
        Setup.output_token_class_file                = FileName
        Setup.output_token_class_file_implementation = FileName + ext

    def __repr__(self):
        txt = ""
        if self.get_file_name() != "": 
            txt += "file name: '%s'\n" % self.get_file_name()
        txt += "class:     '%s'\n" % self.class_name
        if self.open_for_derivation_f: 
            txt += "           (with virtual destructor)\n"
        if self.token_contains_token_id_f == False:
            txt += "           (token id not part of token object)\n"
        txt += "namespace: '%s'\n" % repr(self.class_name_space)[1:-1]
        txt += "type(token_id)      = %s\n" % self.token_id_type.get_text()
        txt += "type(column_number) = %s\n" % self.column_number_type.get_text()
        txt += "type(line_number)   = %s\n" % self.line_number_type.get_text()

        txt += "distinct members {\n"
        # '0' to make sure, that it works on an empty sequence too.
        L = self.distinct_members_type_name_length_max()
        for name, type_code in list(self.distinct_db.items()):
            txt += "    %s%s %s\n" % (type_code.get_text(), " " * (L - len(type_code.get_text())), name)
        txt += "}\n"
        txt += "union members {\n"

        # '0' to make sure, that it works on an empty sequence too.
        L = self.union_members_type_name_length_max()
        for name, type_descr in list(self.union_db.items()):
            if isinstance(type_descr, OrderedDict):
                txt += "    {\n"
                for sub_name, sub_type in list(type_descr.items()):
                    txt += "        %s%s %s\n" % \
                           (sub_type.get_text(), 
                            " " * (L - len(sub_type.get_text())-4), 
                            sub_name)
                txt += "    }\n"
            else:
                txt += "    %s%s %s\n" % \
                       (type_descr.get_text(), 
                        " " * (L - len(type_descr.get_text())), 
                        name)
        txt += "}\n"

        # constructor / copy / destructor
        if not self.constructor.is_whitespace():
            txt += "constructor {\n"
            txt += Lng.SOURCE_REFERENCED(self.constructor)
            txt += "}"
        
        if self.copy is not None:
            txt += "copy {\n"
            txt += Lng.SOURCE_REFERENCED(self.copy)
            txt += "}"

        if not self.destructor.is_whitespace():
            txt += "destructor {\n"
            txt += Lng.SOURCE_REFERENCED(self.destructor)
            txt += "}"

        if not self.body.is_whitespace():
            txt += "body {\n"
            txt += Lng.SOURCE_REFERENCED(self.body)
            txt += "}"

        return txt

    def manually_written(self):
        return False

class TokenTypeDescriptor(TokenTypeDescriptorCore):
    """The final product."""
    def __init__(self, Core, SourceReference=SourceRef_VOID):
        assert isinstance(Core, TokenTypeDescriptorCore)
        TokenTypeDescriptorCore.__init__(self, Core)

        self.sr = SourceReference 

        # (*) Max length of variables etc. for pretty printing
        max_length = 0
        for type_descr in list(self.union_db.values()):
            if isinstance(type_descr, OrderedDict):
                length = 4 + max([0] + [len(x.get_text()) for x in list(type_descr.values())])
            else:
                length = len(type_descr.get_text())
            if length > max_length: max_length = length
        self.__union_members_type_name_length_max = max_length

        max_length = 0
        for name, type_descr in list(self.union_db.items()):
            if isinstance(type_descr, OrderedDict):
                length = 4 + max([0] + [len(x) for x in list(type_descr.keys())])
            else:
                length = len(name)
            if length > max_length: max_length = length
        self.__union_members_variable_name_length_max = max_length

        # 
        self.__distinct_members_type_name_length_max = \
               max([0] + [len(x.get_text()) for x in list(self.distinct_db.values())])
        self.__distinct_members_variable_name_length_max = \
               max([0] + [len(x) for x in list(self.distinct_db.keys())])
        self.__type_name_length_max = \
               max(self.__distinct_members_type_name_length_max,
                   self.__union_members_type_name_length_max)
        self.__variable_name_length_max = \
               max(self.__distinct_members_variable_name_length_max,
                   self.__union_members_variable_name_length_max)

        # (*) Member DB: [member name] --> [type info, access info]
        db = {}
        for name, type_code in list(self.distinct_db.items()):
            db[name] = [type_code, name]
        for name, type_descr in list(self.union_db.items()):
            if isinstance(type_descr, OrderedDict):
                for sub_name, sub_type in list(type_descr.items()):
                    db[sub_name] = [sub_type, "content." + name + "." + sub_name]
            else:
                db[name] = [type_descr, "content." + name]
        self.__member_db = db

    def get_file_name(self):
        return Setup.output_token_class_file

    def type_name_length_max(self):
        return self.__type_name_length_max

    def variable_name_length_max(self):
        return self.__variable_name_length_max

    def distinct_members_type_name_length_max(self):
        return self.__distinct_members_type_name_length_max

    def union_members_type_name_length_max(self):
        return self.__union_members_type_name_length_max

    def get_member_db(self):
        return self.__member_db

    def get_member_access(self, MemberName):
        assert MemberName in self.__member_db, \
               "Member database does not provide member name '%s'.\n" % MemberName + \
               "Available: " + repr(list(self.__member_db.keys()))
        return self.__member_db[MemberName][1]

class TokenTypeDescriptorManual(TokenTypeDescriptorCore):
    """Class to mimik as 'real' TokenTypeDescriptor as defined in 
       quex.input.files.token_type.py. Names and functions must remain
       as they are for compatibility.
    """
    @typed(TokenIDType=CodeUser)
    def __init__(self, FileName):
        TokenTypeDescriptorCore.__init__(self)

        self.__file_name      = FileName

    def get_file_name(self):
        return self.__file_name

    def manually_written(self):
        return True

def setup_TokenTypeDescriptorManual():
    token_db.token_type_definition = \
            TokenTypeDescriptorManual(Setup.extern_token_class_file)
    token_descr = token_db.token_type_definition

    command_line_settings_overwrite(CustomizedTokenTypeF=False)

    fh                   = open_file_or_die(Setup.extern_token_class_file)
    sr                   = SourceRef.from_FileHandle(fh)
    content              = fh.read()
    found_line_n_f   = Lng.Match_column_n_detector.search(content) is not None \
                           or not token_descr.line_number_type.sr.is_void() 
    found_column_n_f = Lng.Match_line_n_detector.search(content) is not None \
                           or not token_descr.column_number_type.sr.is_void()

    if not _validate_stamping(found_line_n_f, found_column_n_f, ErrorF=False, sr=sr):
        error.note("Variables for line and colum numbers in manually written token classes must be named 'line_n'\n"
                   "and 'column_n'. Alternatively, specify '--token-line-n-type' and '--token-column-n-type',\n"
                   "or, consider using '--no-token-stamp'.", sr)

TokenType_StandardMemberList = ["column_n", "line_n", "id"]

__data_name_index_counter = -1
def data_name_index_counter_get():
    global __data_name_index_counter
    __data_name_index_counter += 1
    return __data_name_index_counter

def do(fh, mode_prep_prep_db, CustomizedTokenTypeF):
    if mode_prep_prep_db:
        error.log("Section 'token_type' must appear before first mode definition.", 
                  fh)
    elif Setup.extern_token_class_file:
        error.log("Section 'token_type' is intended to generate a token class.\n" \
                  + "However, the manually written token class file '%s'" \
                  % repr(Setup.extern_token_class_file) \
                  + "has been specified on the command line.", 
                  fh)
    elif token_db.token_type_definition is not None:
        error.log("Section 'token_type' has been defined twice.", 
                  fh, DontExitF=True)
        error.log("Previously defined here.",
                  token_db.token_type_definition.sr)
    else:
        token_db.token_type_definition = parse(fh)

    command_line_settings_overwrite(CustomizedTokenTypeF)

def parse(fh):
    sr         = SourceRef.from_FileHandle(fh)
    descriptor = TokenTypeDescriptorCore()

    if not check(fh, "{"):
        error.log("Missing opening '{' at begin of token_type definition", fh)

    already_defined_list = []
    position             = fh.tell()
    sr_begin             = SourceRef.from_FileHandle(fh)
    while parse_section(fh, descriptor, already_defined_list):
        pass
        
    if not check(fh, "}"):
        fh.seek(position)
        error.log("Missing closing '}' at end of token_type definition.", fh);

    result = TokenTypeDescriptor(descriptor, sr_begin)

    _validate(result, sr)
    return result

def _validate(Descr, sr):
    if     not Descr.get_member_db()             \
       and not Descr.token_id_type_defined_f \
       and Descr.token_id_type.sr.is_void() \
       and Descr.column_number_type.sr.is_void() \
       and Descr.line_number_type.sr.is_void():
        error.log("Section 'token_type' does not define any members, does not\n" + \
                  "modify any standard member types, nor does it define a class\n" + \
                  "different from '%s'." % Setup.token_class_name, sr)

    elif Descr.take_text is None: 
        error.warning(_warning_msg, Descr.sr,
                      SuppressCode=NotificationDB.warning_on_no_token_class_take_text)

    _validate_stamping(not Descr.line_number_type.sr.is_void(),
                       not Descr.column_number_type.sr.is_void(),
                       ErrorF=True, sr=sr)

def _validate_stamping(LineTypePresentF, ColumnTypePresentF, ErrorF, sr):
    if ErrorF: _notify = error.log
    else:      _notify = error.warning

    def notify(Subject):
        _notify("Global configuration enables token stamping with %s numbers.\n" % Subject
                + "But token type definition does not provide '%s_n'." % Subject, sr)

    error_f = False
    if Setup.token_class_support_token_stamp_line_n_f and not LineTypePresentF:
        notify("line")
        error_f = True
    if   Setup.token_class_support_token_stamp_column_n_f and not ColumnTypePresentF:
        notify("column")
        error_f = True

    return not error_f

def parse_section(fh, descriptor, already_defined_list):
    pos = fh.tell()
    try: 
        return __parse_section(fh, descriptor, already_defined_list)
    except EndOfStreamException:
        fh.seek(pos)
        error.error_eof("token_type", fh)

def __parse_section(fh, descriptor, already_defined_list):
    global token_type_code_fragment_db
    assert type(already_defined_list) == list

    SubsectionList = ["name", "file_name", "standard", "distinct", "union", "inheritable", "noid"] \
                      + list(token_type_code_fragment_db.keys())

    position = fh.tell()
    skip_whitespace(fh)
    word = read_identifier(fh)
    if not word:
        fh.seek(position)
        if check(fh, "}"): 
            fh.seek(position) 
            return False
        error.log("Missing token_type section ('standard', 'distinct', or 'union').", fh)

    error.verify_word_in_list(word, SubsectionList, 
                        "Subsection '%s' not allowed in token_type section." % word, 
                        fh)

    if word == "name":
        if not check(fh, "="):
            error.log("Missing '=' in token_type 'name' specification.", fh)
        descriptor.class_name, \
        descriptor.class_name_space, \
        descriptor.class_name_safe = read_namespaced_name(fh, "token_type", 
                                                          NamespaceAllowedF=Setup.language not in ("C",))
        if not check(fh, ";"):
            error.log("Missing terminating ';' in token_type 'name' specification.", fh)

    elif word == "repetition_n":
        member_name = _assignment(fh, "repetition_n")
        member_list = list(descriptor.distinct_db.keys()) + list(descriptor.union_db.keys()) + TokenType_StandardMemberList
        error.verify_word_in_list(member_name, member_list, 
                                  "'%s' specified as repetition counter 'repetition_n'.\n" % member_name
                                  + "But, no such member exists.", fh, ExitF=True)
        descriptor.token_repetition_n_member_name = CodeUser(member_name, 
                                                             SourceRef.from_FileHandle(fh, BeginPos=position))

    elif word == "file_name":
       descriptor.set_file_name(_assignment(fh, "file_name"))

    elif word == "inheritable":
        descriptor.open_for_derivation_f = True
        check_or_die(fh, ";")

    elif word == "noid":
        descriptor.token_contains_token_id_f = False;
        check_or_die(fh, ";")

    elif word in ["standard", "distinct", "union"]:
        if   word == "standard": parse_standard_members(fh, word, descriptor, already_defined_list)
        elif word == "distinct": parse_distinct_members(fh, word, descriptor, already_defined_list)
        elif word == "union":    parse_union_members(fh, word, descriptor, already_defined_list)

        if not check(fh, "}"):
            fh.seek(position)
            error.log("Missing closing '}' at end of token_type section '%s'." % word, fh);

    elif word in list(token_type_code_fragment_db.keys()):
        fragment = code_fragment.parse(fh, word, AllowBriefTokenSenderF=False)        

        if   word == "constructor":  descriptor.constructor  = fragment
        elif word == "destructor":   descriptor.destructor   = fragment
        elif word == "copy":         descriptor.copy         = fragment
        elif word == "body":         descriptor.body         = fragment
        elif word == "header":       descriptor.header       = fragment
        elif word == "footer":       descriptor.footer       = fragment
        elif word == "take_text":    descriptor.take_text    = fragment
        elif word == "repetition_n": descriptor.repetition_n = fragment

    else: 
        assert False, "This code section section should not be reachable because 'word'\n" + \
                      "was checked to fit in one of the 'elif' cases."

    return True
            
def parse_standard_members(fh, section_name, descriptor, already_defined_list):
    if not check(fh, "{"):
        error.log("Missing opening '{' at begin of token_type section '%s'." % section_name, fh);

    position = fh.tell()

    while 1 + 1 == 2:
        try: 
            result = parse_variable_definition(fh) 
        except EndOfStreamException:
            fh.seek(position)
            error.error_eof("standard", fh)

        if result is None: return
        type_code_fragment, name = result[0], result[1]

        __validate_definition(type_code_fragment, name,
                              already_defined_list, StandardMembersF=True)

        if   name == "id":       descriptor.token_id_type      = type_code_fragment
        elif name == "column_n": descriptor.column_number_type = type_code_fragment
        elif name == "line_n":   descriptor.line_number_type   = type_code_fragment
        else:
            assert False # This should have been caught by the variable parser function

        already_defined_list.append([name, type_code_fragment])

def parse_distinct_members(fh, section_name, descriptor, already_defined_list):
    if not check(fh, "{"):
        error.log("Missing opening '{' at begin of token_type section '%s'." % section_name, fh);

    result = parse_variable_definition_list(fh, "distinct", already_defined_list)
    if result == {}: 
        error.log("Missing variable definition in token_type 'distinct' section.", fh)
    descriptor.distinct_db = result

def parse_union_members(fh, section_name, descriptor, already_defined_list):
    if not check(fh, "{"):
        error.log("Missing opening '{' at begin of token_type section '%s'." % section_name, fh);

    result = parse_variable_definition_list(fh, "union", already_defined_list, 
                                            GroupF=True)
    if not result:
        error.log("Missing variable definition in token_type 'union' section.", fh)
    descriptor.union_db = result

def parse_variable_definition_list(fh, SectionName, already_defined_list, GroupF=False):
    position = fh.tell()

    db = OrderedDict() # See comment [MEMBER PACKAGING]
    while 1 + 1 == 2:
        try: 
            result = parse_variable_definition(fh, GroupF=True, already_defined_list=already_defined_list) 
        except EndOfStreamException:
            fh.seek(position)
            error.error_eof(SectionName, fh)

        if result is None: 
            return db

        # The type_descriptor can be:
        #  -- a UserCodeFragment with a string of the type
        #  -- a dictionary that contains the combined variable definitions.
        type_descriptor = result[0]

        # If only one argument was returned it was a 'struct' that requires
        # an implicit definition of the struct that combines the variables.
        if len(result) == 1: name = "data_" + repr(data_name_index_counter_get())
        else:                name = result[1]

        db[name] = type_descriptor

        if len(result) == 1:
            assert isinstance(type_descriptor, OrderedDict)
            # In case of a 'combined' definition each variable needs to be validated.
            for sub_name, sub_type in list(type_descriptor.items()):
                __validate_definition(sub_type, sub_type, already_defined_list, 
                                      StandardMembersF=False)

                already_defined_list.append([sub_name, sub_type])
        else:
            assert type_descriptor.__class__ == CodeUser
            __validate_definition(type_descriptor, name, already_defined_list, 
                                  StandardMembersF=False)
            already_defined_list.append([name, type_descriptor])

def parse_variable_definition(fh, GroupF=False, already_defined_list=[]):
    """PURPOSE: Parsing of a variable definition consisting of 'type' and 'name.
                Members can be mentioned together in a group, which means that
                they can appear simultaneously. Possible expresions are

                (1) single variables:

                              name0 : type;
                              name1 : type[32];
                              name2 : type*;

                (2) combined variables

                              {
                                  sub_name0 : type0;
                                  sub_name1 : type[64];
                                  sub_name2 : type1*;
                              }

       ARGUMENTS: 

        'GroupF'               allows to have 'nested variable groups' in curly brackets

        'already_defined_list' informs about variable names that have been already
                               chosen. It is only used for groups.

       RETURNS:
                 None        on failure to pass a variable definition.
                 array       when a single variable definition was found. 
                                array[0] = UserCodeFragment containing the type. 
                                array[1] = name of the variable.
                 dictionary  if it was a combined variable definition. The dictionary
                               maps: (variable name) ---> (UserCodeFragment with type)
    
    """
    position = fh.tell()

    skip_whitespace(fh)
    name_str = read_identifier(fh)
    if name_str == "":
        if not GroupF or not check(fh, "{"): 
            fh.seek(position); 
            return None
        sub_db = parse_variable_definition_list(fh, "Concurrent union variables", already_defined_list)
        if not check(fh, "}"): 
            fh.seek(position)
            error.log("Missing closing '}' after concurrent variable definition.", fh)
        return [ sub_db ]

    else:
        name_str = name_str.strip()
        if not check(fh, ":"): error.log("Missing ':' after identifier '%s'." % name_str, fh)
        
        if fh.read(1).isspace() == False:
            error.log("Missing whitespace after ':' after identifier '%s'.\n" % name_str \
                    + "The notation has to be: variable-name ':' type ';'.", fh)

        position = fh.tell()
        type_str, i, dummy = read_until_letter(fh, ";", Verbose=True)
        if i == -1: error.log("missing ';'", fh)
        type_str = type_str.strip()

        return [ CodeUser(type_str, SourceRef.from_FileHandle(fh, BeginPos=position)), name_str ]

def __validate_definition(TheCodeFragment, NameStr, 
                          AlreadyMentionedList, StandardMembersF):
    if StandardMembersF:
        error.verify_word_in_list(NameStr, TokenType_StandardMemberList, 
                            "Member name '%s' not allowed in token_type section 'standard'." % NameStr, 
                            TheCodeFragment.sr)

        # Standard Members are all numeric types
        if    TheCodeFragment.contains_string(Lng.Match_string) \
           or TheCodeFragment.contains_string(Lng.Match_vector) \
           or TheCodeFragment.contains_string(Lng.Match_map):
            type_str = TheCodeFragment.get_text()
            error.log("Numeric type required.\n" + \
                      "Example: <token_id: uint16_t>, Found: '%s'\n" % type_str, 
                      TheCodeFragment.sr)
    else:
        if NameStr in TokenType_StandardMemberList:
            error.log("Member '%s' only allowed in 'standard' section." % NameStr,
                      TheCodeFragment.sr)

    for candidate in AlreadyMentionedList:
        if candidate[0] != NameStr: continue 
        error.log("Token type member name '%s' defined twice." % NameStr,
                  TheCodeFragment.sr, DontExitF=True)
        error.log("Previously defined here.",
                  candidate[1].sr)

def _assignment(fh, Name):
    if not check(fh, "="):
        error.log("Missing '=' in token_type '%s' specification." % Name, fh)
    skip_whitespace(fh)
    result = read_until_letter(fh, ";")
    if "\n" in result or " " in result:
        error.log("Missing terminating ';' after '%s' in token_type '%s' specification." % (result, Name), fh)
    return result

def command_line_settings_overwrite(CustomizedTokenTypeF):
    x           = token_db.token_type_definition
    token_class = _token_type_class_naming()

    _token_type_command_line_settings_detect_inadmissible(CustomizedTokenTypeF)

    if not CustomizedTokenTypeF or not x.class_name:
        x.class_name,       \
        x.class_name_space, \
        x.class_name_safe   = read_namespaced_name(token_class, 
                                                   "token class (options --token-class, --tc)",
                                                   NamespaceAllowedF=Setup.language not in ("C",))
    if CustomizedTokenTypeF: 
        return

    sr_cl = SourceRef.from_CommandLine()
    if Setup.token_id_type:
        x.token_id_type = CodeUser(Setup.token_id_type, sr_cl)

    if Setup.token_line_n_type:
        x.line_number_type = CodeUser(Setup.token_line_n_type, sr_cl)
    if Setup.token_column_n_type:
        x.token_column_n_type = CodeUser(Setup.token_column_n_type, sr_cl)
    if Setup.token_repetition_n_member_name:
        x.token_repetition_n_member_name = CodeUser(Setup.token_repetition_n_member_name, sr_cl)

def _token_type_class_naming():
    """ X0::X1::X2::ClassName --> token_class_name = ClassName
                                  token_name_space = ["X0", "X1", "X2"]
        ::ClassName --> token_class_name = ClassName
                        token_name_space = []
    """
    # Default set here => able to detect seting on command line.
    if Setup.token_class: 
        token_class = Setup.token_class
    else:
        if Setup.analyzer_class:
            if Setup.analyzer_name_space:
                token_class = "%s::%s_Token" % ("::".join(Setup.analyzer_name_space), Setup.analyzer_class_name)
            else:
                token_class = "%s_Token" % Setup.analyzer_class_name
        else:
            token_class = "Token"
    return token_class

def _token_type_command_line_settings_detect_inadmissible(CustomizedTokenTypeF):
    """When a token type different from the default definition is given,
    certain things cannot be overwritten on the command line.
    """
    if not CustomizedTokenTypeF: return
    forbidden = [
        (Setup.token_id_type,                  "token id type"),
        (Setup.token_line_n_type,              "token line_n type"),
        (Setup.token_column_n_type,            "token column_n type"),
        (Setup.token_repetition_n_member_name, "token repetition number member name"),
    ]
    # If the customized token class definition defines no name, it may
    # actually be overwritten by the command line settings. Else, not.
    if token_db.token_type_definition.class_name:
        forbidden.append(
           (Setup.token_class_name, "token class name"),
        )
    for x, name in forbidden:
        if not x: continue
        error.log("The %s cannot be defined on the command line, if\n" % name +
                  "a customized 'token_type' section has been defined.")

_warning_msg = \
"""Section token_type does not contain a 'take_text' section. It would be
necessary if the analyzer uses the string accumulator."""

#______________________________________________________________________________
# [MEMBER PACKAGING] 
#
# The classes uses 'OrderedDict' objects for members, so that ihe iteration
# over members happens in the order that they were defined. This supports the
# 'packaging', i.e. the user is able to determine the place where members are
# stored. 
#______________________________________________________________________________

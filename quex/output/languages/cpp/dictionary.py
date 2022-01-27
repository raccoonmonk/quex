# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.code.base                              import CodeFragment
from   quex.engine.analyzer.state.core                   import Processor
from   quex.engine.operations.content_terminal_router    import RouterContentElement
from   quex.engine.operations.operation_list             import E_R
from   quex.engine.analyzer.mega_state.template.state    import TemplateState
from   quex.engine.analyzer.mega_state.path_walker.state import PathWalkerState
from   quex.engine.analyzer.door_id_address_label        import DoorID, \
                                                                DialDB, \
                                                                get_plain_strings
from   quex.engine.misc.string_handling                  import blue_print, \
                                                                pretty_code
from   quex.engine.misc.file_operations                  import open_file_or_die, \
                                                                get_file_content_or_die, \
                                                                write_safely_and_close
import quex.engine.misc.error                            as     error
from   quex.engine.misc.tools                            import typed, \
                                                                do_and_delete_if, \
                                                                none_isinstance, \
                                                                flatten
import quex.output.languages.cpp.templates               as     templates

from   quex.DEFINITIONS  import QUEX_PATH
import quex.token_db     as     token_db
import quex.condition    as     condition
from   quex.blackboard   import setup as Setup, \
                                Lng
from   quex.constants    import E_Files, \
                                E_StateIndices,  \
                                E_IncidenceIDs, \
                                E_TransitionN,   \
                                E_AcceptanceCondition, \
                                E_Count, \
                                E_Op

from   itertools import islice
from   math      import log
import re
import os

code_send_TERMINATE_RETURN = lambda Lng: [
    "%s\n" % Lng.TOKEN_SEND("QUEX_SETTING_TOKEN_ID_TERMINATION"),
    '%s\n' % Lng.PURE_RETURN
]

code_ON_BUFFER_OVERFLOW = lambda Lng: [
"""
    /* Try to double the size of the buffer, by default.                      */
    if( ! QUEX_NAME(Buffer_nested_negotiate_extend)(&self.buffer, 2.0) ) {
        QUEX_NAME(MF_error_code_set_if_first)(&self, E_Error_Buffer_Overflow_LexemeTooLong);
        QUEX_NAME(Buffer_print_overflow_message)(&self.buffer);
    }
"""                         
]

code_Empty  = lambda Lng: []

code_Empty2 = lambda Lng, ModeName: []

class Language(dict):
    #------------------------------------------------------------------------------
    # Define Regular Expressions
    #------------------------------------------------------------------------------
    Match_Lexeme              = re.compile("\\bLexeme\\b", re.UNICODE)
    Match_LexemeBegin         = re.compile("\\bLexemeBegin\\b", re.UNICODE)
    Match_string              = re.compile("\\bstring\\b", re.UNICODE) 
    Match_vector              = re.compile("\\bvector\\b", re.UNICODE) 
    Match_map                 = re.compile("\\bmap\\b", re.UNICODE)
    Match_include             = re.compile(r"#[ \t]*include[ \t]*[\"<]([^\">]+)[\">]")
    Match_Lexeme              = re.compile("\\bLexeme\\b", re.UNICODE)
    Match_QUEX_NAME_lexeme    = re.compile("\\bQUEX_NAME\\(lexeme_", re.UNICODE)
    Match_QUEX_NAME           = re.compile(r"\bQUEX_NAME\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_GNAME          = re.compile(r"\bQUEX_GNAME\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_NAME_TOKEN     = re.compile(r"\bQUEX_NAME_TOKEN\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_GNAME_TOKEN    = re.compile(r"\bQUEX_GNAME_TOKEN\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_NAME_LIB       = re.compile(r"\bQUEX_NAME_LIB\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_STD            = re.compile(r"\bQUEX_STD\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_GSTD           = re.compile(r"\bQUEX_GSTD\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_GNAME_LIB      = re.compile(r"\bQUEX_GNAME_LIB\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_SETTING        = re.compile(r"\bQUEX_SETTING_([A-Z_0-9]+)\b")
    Match_QUEX_PURE_SETTING   = re.compile(r"\bQUEX_<PURE>SETTING_([A-Z_0-9]+)\b")
    Match_QUEX_OPTION         = re.compile(r"\bQUEX_OPTION_([A-Z_0-9]+)\b")
    Match_QUEX_CLASS_BEGIN    = re.compile(r"\bQUEX_CLASS_BEGIN\(([A-Z_a-z0-9]+),([A-Z_a-z0-9]+)\)")
    Match_QUEX_CLASS_END      = re.compile(r"\bQUEX_CLASS_END\(([A-Z_a-z0-9]+)\)")
    Match_QUEX_BASE           = re.compile(r"\bQUEX_BASE")
    # Note: When the first two are replaced, the last cannot match anymore.
    Match_QUEX_INCLUDE_GUARD_LEXEME_CONVERTER = re.compile(r"\bQUEX_LC_INCLUDE_GUARD__([a-zA-Z_0-9]+)\b")
    Match_QUEX_INCLUDE_GUARD_TOKEN            = re.compile(r"\bQUEX_TOKEN_INCLUDE_GUARD__([a-zA-Z_0-9]+)\b")
    Match_QUEX_INCLUDE_GUARD_QUEX             = re.compile(r"\bQUEX_INCLUDE_GUARD__QUEX__([a-zA-Z_0-9]+)\b")
    Match_QUEX_INCLUDE_GUARD                  = re.compile(r"\bQUEX_INCLUDE_GUARD__([a-zA-Z_0-9]+)\b")
    Match_QUEX_TOKEN_MEMBER_REPETITION_N = re.compile(r"\bQUEX_TOKEN_MEMBER_REPETITION_N\b") 
    Match_QUEX_TOKEN_ID_IS_REPEATABLE         = re.compile(r"\bQUEX_TOKEN_ID_IS_REPETITION\b") 
    # Detectors that give a hint, whether line and column number are defined!
    # (This does not have to work 100%, since it only causes a note, if not found)
    Match_line_n_detector   = re.compile(r"\bline_n\b", re.UNICODE)
    Match_column_n_detector = re.compile(r"\bcolumn_n\b", re.UNICODE)

    CommentDelimiterList      = [["//", "\n"], ["/*", "*/"]]
    
    CODE_BASE                 = "quex/code_base/"
    LEXEME_CONVERTER_DIR      = "lib/lexeme_converter"

    DEFAULT_STD_LIB_NAMING    =  ("", ["std"]) # (prefix, namespace)
                              
    INLINE                    = "inline"
    ON_AFTER_MATCH_THEN_RETURN = "FLUSH;"   
    PURE_RETURN               = "return;"
    UNREACHABLE               = "__quex_assert_no_passage();"
    ELSE                      = "else {"
    ELSE_FOLLOWS              = "} else {"
    ELSE_SIMPLE               = "else"
    END_IF                    = "}"
    FALSE                     = "false"
    TRUE                      = "true"
    OR                        = "||"
    AND                       = "&&"

    PATH_ITERATOR_INCREMENT   = "++(path_iterator);"
    VIRTUAL_DESTRUCTOR_PREFIX = "virtual "

    STANDARD_TYPE_DB          = {
        1: "uint8_t", 2: "uint16_t", 4: "uint32_t", 8: "uint64_t",
    }

    all_extension_db = {
        "": { 
              E_Files.SOURCE:              ".cpp",
              E_Files.HEADER:              "",
              E_Files.HEADER_IMPLEMTATION: ".i",
        },
        "++": { 
              E_Files.SOURCE:              ".c++",
              E_Files.HEADER:              ".h++",
              E_Files.HEADER_IMPLEMTATION: ".i++",
        },
        "pp": { 
              E_Files.SOURCE:              ".cpp",
              E_Files.HEADER:              ".hpp",
              E_Files.HEADER_IMPLEMTATION: ".ipp",
        },
        "cc": { 
              E_Files.SOURCE:              ".cc",
              E_Files.HEADER:              ".hh",
              E_Files.HEADER_IMPLEMTATION: ".ii",
        },
        "xx": { 
              E_Files.SOURCE:              ".cxx",
              E_Files.HEADER:              ".hxx",
              E_Files.HEADER_IMPLEMTATION: ".ixx",
        },
    }
    extension_db = None # To be set by 'setup' to one of 'all_extension_db'

    event_prolog_db = {
        E_IncidenceIDs.MATCH:                code_Empty2,
        E_IncidenceIDs.AFTER_MATCH:          code_Empty2,
        E_IncidenceIDs.MODE_ENTRY:           lambda Lng, ModeName: [ Lng.CALL_MODE_HAS_ENTRY_FROM(ModeName) ],
        E_IncidenceIDs.MODE_EXIT:            lambda Lng, ModeName: [ Lng.CALL_MODE_HAS_EXIT_TO(ModeName) ],
        E_IncidenceIDs.BUFFER_BEFORE_CHANGE: code_Empty2,
        E_IncidenceIDs.BUFFER_OVERFLOW:      code_Empty2,
        E_IncidenceIDs.INDENTATION_INDENT:   code_Empty2,
        E_IncidenceIDs.INDENTATION_NODENT:   code_Empty2,
        E_IncidenceIDs.INDENTATION_DEDENT:   code_Empty2,
        E_IncidenceIDs.INDENTATION_MISFIT:   lambda Lng, ModeName: [ Lng.RAISE_ERROR_FLAG(Lng.error_code_db[E_IncidenceIDs.INDENTATION_MISFIT]) ],
        E_IncidenceIDs.INDENTATION_BAD:      lambda Lng, ModeName: [ Lng.RAISE_ERROR_FLAG(Lng.error_code_db[E_IncidenceIDs.INDENTATION_BAD]) ],
        E_IncidenceIDs.BAD_LEXATOM:          lambda Lng, ModeName: [ Lng.RAISE_ERROR_FLAG(Lng.error_code_db[E_IncidenceIDs.BAD_LEXATOM]) ],
        E_IncidenceIDs.MATCH_FAILURE:        lambda Lng, ModeName: [ Lng.RAISE_ERROR_FLAG(Lng.error_code_db[E_IncidenceIDs.MATCH_FAILURE]) ],
        E_IncidenceIDs.LOAD_FAILURE:         lambda Lng, ModeName: [ Lng.RAISE_ERROR_FLAG(Lng.error_code_db[E_IncidenceIDs.LOAD_FAILURE]) ],
        E_IncidenceIDs.SKIP_RANGE_OPEN:      lambda Lng, ModeName: [ Lng.RAISE_ERROR_FLAG(Lng.error_code_db[E_IncidenceIDs.SKIP_RANGE_OPEN]) ],
        E_IncidenceIDs.END_OF_STREAM:        code_Empty2,
    }

    event_handler_default_db = {
        E_IncidenceIDs.MATCH:                code_Empty,
        E_IncidenceIDs.AFTER_MATCH:          code_Empty,
        E_IncidenceIDs.MODE_ENTRY:           code_Empty,
        E_IncidenceIDs.MODE_EXIT:            code_Empty,
        E_IncidenceIDs.BUFFER_BEFORE_CHANGE: code_Empty,
        E_IncidenceIDs.BUFFER_OVERFLOW:      code_ON_BUFFER_OVERFLOW,
        E_IncidenceIDs.INDENTATION_INDENT:   lambda Lng: [ Lng.TOKEN_SEND("QUEX_SETTING_TOKEN_ID_INDENT") ],
        E_IncidenceIDs.INDENTATION_NODENT:   lambda Lng: [ Lng.TOKEN_SEND("QUEX_SETTING_TOKEN_ID_NODENT") ],
        E_IncidenceIDs.INDENTATION_DEDENT:   lambda Lng: [ Lng.TOKEN_SEND_N("N", "QUEX_SETTING_TOKEN_ID_DEDENT") ],
        E_IncidenceIDs.INDENTATION_MISFIT:   code_Empty,
        E_IncidenceIDs.INDENTATION_BAD:      code_Empty,
        E_IncidenceIDs.BAD_LEXATOM:          code_send_TERMINATE_RETURN,
        E_IncidenceIDs.MATCH_FAILURE:        code_send_TERMINATE_RETURN,
        E_IncidenceIDs.LOAD_FAILURE:         code_send_TERMINATE_RETURN,
        E_IncidenceIDs.SKIP_RANGE_OPEN:      code_send_TERMINATE_RETURN,
        E_IncidenceIDs.END_OF_STREAM:        code_send_TERMINATE_RETURN,
    }

    error_code_db = {
        E_IncidenceIDs.MATCH_FAILURE:     "E_Error_OnFailure",       
        E_IncidenceIDs.SKIP_RANGE_OPEN:   "E_Error_OnSkipRangeOpen",  
        E_IncidenceIDs.INDENTATION_MISFIT:"E_Error_OnIndentationMisfit", 
        E_IncidenceIDs.INDENTATION_BAD:   "E_Error_OnIndentationBad", 
        E_IncidenceIDs.BAD_LEXATOM:       "E_Error_OnBadLexatom",     
        E_IncidenceIDs.LOAD_FAILURE:      "E_Error_OnLoadFailure",    
    }
            

    def __init__(self):      
        self.__analyzer                           = None
        self.__code_generation_reload_label       = None
        self.__code_generation_on_reload_fail_adr = None
        self.__debug_unit_name                    = "<undefined>"
        assert self.ON_AFTER_MATCH_THEN_RETURN.endswith(";")
        self.__re_FLUSH                          = re.compile(r"\b%s\b" % self.ON_AFTER_MATCH_THEN_RETURN[:-1])
        # NOTE: 'END_OF_STREAM' is not an error, it is the event of input 
        #       stream exhaustion.
        #       E_IncidenceIDs.END_OF_STREAM:   "",                         

    def ASSERT(self, Condition):
        return "__quex_assert(%s);" % Condition

    def FORWARD_DECLARATION(self, ClassName): 
        return "class %s;" % ClassName

    def SAFE_IDENTIFIER(self, String):
        if not String:
            return ""

        def _safe(L):
            if len(L) != 1:
                error.log("The underlying python build cannot handle character '%s'." % L)
            if L.isalpha() or L.isdigit() or L == "_": return L.lower()
            elif L == ":":                             return "_"
            else:                                      return "_x%x_" % ord(L)
        return "".join(_safe(letter) for letter in String)

    def event_handler(self, Mode, EventId):
        return self.SOURCE_REFERENCED(Mode.incidence_db.get(EventId)) 

    def INCLUDE_GUARD(self, Filename):
        if Filename: return self.SAFE_IDENTIFIER(Filename).upper()
        else:        return ""

    def INCREMENT_ITERATOR_THEN_ASSIGN(self, Iterator, Value):
        return "*(%s)++ = %s;" % (Iterator, Value)

    def OP(self, Big, Op, Small):
        return "%s %s %s" % (Big, Op, Small)

    def SWITCH(self, txt, Name, SwitchF):
        if SwitchF: txt = txt.replace("$$SWITCH$$ %s" % Name, "#define    %s" % Name)
        else:       txt = txt.replace("$$SWITCH$$ %s" % Name, "/* #define %s */" % Name)
        return txt

    def BUFFER_SEEK(self, Position):
        return "QUEX_NAME(Buffer_seek)(&me->buffer, %s)" % Position

    def open_template(self, PathTail):
        full_path = os.path.normpath(os.path.join(QUEX_PATH, PathTail))
        return get_file_content_or_die(full_path)

    def open_template_fh(self, PathTail):
        full_path = os.path.normpath(os.path.join(QUEX_PATH, PathTail))
        return open_file_or_die(full_path)

    def token_template_file(self):         return "%s/token/TXT-Cpp"                         % self.CODE_BASE
    def token_template_i_file(self):       return "%s/token/TXT-Cpp.i"                       % self.CODE_BASE
    def token_default_file(self):          return "%s/token/CppDefault.qx"                   % self.CODE_BASE
    def analyzer_template_file(self):      return "%s/analyzer/TXT-Cpp"                      % self.CODE_BASE
    def analyzer_template_i_file(self):    return "%s/analyzer/TXT-Cpp.i"                    % self.CODE_BASE
    def analyzer_configuration_file(self): return "%s/analyzer/configuration/TXT"            % self.CODE_BASE

    def _template_converter(self, Basename):
        path = os.path.join(QUEX_PATH, self.CODE_BASE, "lexeme_converter", Basename)
        return get_file_content_or_die(path)
    def template_converter_character_functions(self):     
        return self._template_converter("TXT-character-functions-from-encoding")
    def template_converter_character_functions_standard(self, EncodingName): 
        return self._template_converter("TXT-character-functions-from-%s" % EncodingName)
    def template_converter_string_functions(self):
        return self._template_converter("TXT-string-functions")
    def template_converter_header(self):       
        return self._template_converter("TXT-header")
    def template_converter_implementation(self):
        return self._template_converter("TXT-implementation")

    def file_name_converter_header(self, Suffix): 
        return os.path.join(Setup.output_directory, "lib/lexeme", 
                            "converter-from-%s" % Suffix)
    def file_name_converter_implementation(self, Suffix): 
        return os.path.join(Setup.output_directory, "lib/lexeme", 
                            "converter-from-%s.i" % Suffix)

    def UNDEFINE_SELF(self):
        return "#   ifdef     self\n" \
               "#       undef self\n" \
               "#   endif\n" 
    def DEFINE_SELF(self, Name):
        return self.UNDEFINE_SELF() + \
               "#   define self (*((QUEX_TYPE_ANALYZER*)%s))\n" % Name\

    def MODE_DEFINITION(self, ModeNameList):
        if not ModeNameList: return ""
        L = max(len(m) for m in ModeNameList)
        return "\n".join(
            "#   define %s%s    (&QUEX_NAME(%s))" % (name, " " * (L- len(name)), name)
            for name in ModeNameList
        ) + "\n"

    def MODE_UNDEFINITION(self, ModeNameList):
        if not ModeNameList: return ""
        return "\n".join(
            "#   undef %s" % name for name in ModeNameList
        ) + "\n"

    def register_analyzer(self, TheAnalyzer):
        self.__analyzer = TheAnalyzer

    def unregister_analyzer(self):
        # Unregistering an analyzer ensures that no one else works with the 
        # analyzer on something unrelated.
        self.__analyzer = None

    def BINARY_OPERATION_LIST(self, Operator, ConditionList):
        condition_list = [ c for c in ConditionList if c ]
        if not condition_list: 
            return []
        elif len(condition_list) == 1: 
            return [ condition_list[0] ]
        else:
            result = [ "(%s)" % condition_list[0] ]
            for cnd in condition_list[1:]:
                result.append(" %s " % Operator)
                result.append("(%s)" % cnd)
            return result

    @property
    def analyzer(self):
        return self.__analyzer

    def _get_log2_if_power_of_2(self, X):
        assert type(X) != tuple
        if not isinstance(X, int):
            return None

        log2 = log(X, 2)
        if not log2.is_integer(): return None
        return int(log2)
            
    def __getattr__(self, Attr): 
        # Thanks to Rami Al-Rfou' who mentioned that this is the only thing to 
        # be adapted to be compliant with current version of PyPy.
        try:             return self[Attr] 
        except KeyError: raise AttributeError

    def LEXEME_START_SET(self, PositionStorage=None):
        if PositionStorage is None: return "me->buffer._lexeme_start_p = me->buffer._read_p;"
        else:                       return "me->buffer._lexeme_start_p = %s;" % PositionStorage
    def LEXEME_START_P(self):                      return "me->buffer._lexeme_start_p"
    def LEXEME_NULL(self):                         return "LexemeNull"
    def LEXEME_LENGTH(self):                       return "((size_t)(me->buffer._read_p - me->buffer._lexeme_start_p))"

                                                    
    DEFINE_COUNT_COLUMN_NUMBER   = ["#define LineNEnd   me->counter._line_number_at_end",
                                    "#define LineN      me->counter._line_number_at_begin"]
    DEFINE_COUNT_LINE_NUMBER     = ["#define ColumnNEnd me->counter._column_number_at_end",
                                    "#define ColumnN    me->counter._column_number_at_begin"]
    UNDEFINE_COUNT_COLUMN_NUMBER = ["#undef ColumnN", "#undef ColumnNEnd"]
    UNDEFINE_COUNT_LINE_NUMBER   = ["#undef LineN",   "#undef LineNEnd"]

    def DEFINE_COUNTER_VARIABLES(self):
        define_txt = []
        undefine_txt = []
        if Setup.count_column_number_f:
            define_txt.extend(self.DEFINE_COUNT_COLUMN_NUMBER)
            undefine_txt.extend(self.UNDEFINE_COUNT_COLUMN_NUMBER)
        if Setup.count_line_number_f:
            define_txt.extend(self.DEFINE_COUNT_LINE_NUMBER)
            undefine_txt.extend(self.UNDEFINE_COUNT_LINE_NUMBER)

        return "\n".join(define_txt) + "\n", \
               "\n".join(undefine_txt) + "\n"

    def DEFINE_LEXEME_VARIABLES(self):
        return blue_print(cpp_lexeme_macro_setup, [
            ["$$LEXEME_LENGTH$$",  self.LEXEME_LENGTH()],
            ["$$INPUT_P$$",        self.INPUT_P()],
        ])

    def UNDEFINE_LEXEME_VARIABLES(self):
        return cpp_lexeme_macro_clean_up

    def DEFAULT_TOKEN_COPY(self, X, Y):
        return "QUEX_GSTD(memcpy)((void*)%s, (void*)%s, sizeof(QUEX_TYPE_TOKEN));\n" % (X, Y)

    def INPUT_P(self):                             return "me->buffer._read_p"
    def INPUT_P_TO_LEXEME_START(self):             return "me->buffer._read_p = me->buffer._lexeme_start_p;"
    def INPUT_P_DEREFERENCE(self, Offset=0): 
        if Offset == 0:  return "*(me->buffer._read_p)"
        elif Offset > 0: return "*(me->buffer._read_p + %i)" % Offset
        else:            return "*(me->buffer._read_p - %i)" % - Offset
    def LEXEME_TERMINATING_ZERO_SET(self, RequiredF):
        if not RequiredF: return ""
        return "QUEX_LEXEME_TERMINATING_ZERO_SET(&me->buffer);\n"

    def INDENTATION_HANDLER_CALL(self, ModeName):
        name = self.NAME_IN_NAMESPACE_MAIN("%s_on_indentation" % ModeName)
        return "    %s(me, (QUEX_TYPE_INDENTATION)me->counter._column_number_at_end, LexemeNull);\n" % name

    def INDENTATION_BAD_HANDLER_CALL(self, ModeName):
        name = self.NAME_IN_NAMESPACE_MAIN("%s_on_indentation_bad" % ModeName)
        return "    %s(me);\n" % name

    def STORE_LAST_CHARACTER(self, BeginOfLineSupportF):
        if not BeginOfLineSupportF: return ""
        # TODO: The character before lexeme start does not have to be written
        # into a special register. Simply, make sure that '_lexeme_start_p - 1'
        # is always in the buffer. This may include that on the first buffer
        # load '\n' needs to be at the beginning of the buffer before the
        # content is loaded. Not so easy; must be carefully approached.
        return "    %s\n" % self.ASSIGN("me->buffer._lexatom_before_lexeme_start", 
                                        self.INPUT_P_DEREFERENCE(-1))

    def UNDEFINE(self, NAME):
        return "\n#undef %s\n" % NAME

    @typed(Txt=(CodeFragment))
    def SOURCE_REFERENCED(self, Cf, PrettyF=False):
        if Cf is None:    return ""
        elif not PrettyF: text = Cf.get_text()
        else:             text = "".join(pretty_code(Cf.get_code()))

        return "%s%s%s" % (
            self._SOURCE_REFERENCE_BEGIN(Cf.sr),
            text,
            self._SOURCE_REFERENCE_END(Cf.sr)
        )

    def _SOURCE_REFERENCE_BEGIN(self, SourceReference):
        """Return a code fragment that returns a source reference pragma. If 
        the source reference is void, no pragma is required. 
        """
        if SourceReference.is_void(): return ""
        return "\n%s\n" % self.LINE_PRAGMA(SourceReference.file_name, SourceReference.line_n)

    def LINE_PRAGMA(self, Path, LineN):
        if LineN >= 2**15: 
            return '#   line %i "%s" /* was %i; ISO C89: 0 <= line number <= 32767 */' \
                    % (2**15 - 1, Path, LineN) 
        elif LineN <= 0:     
            return '#   line %i "%s" /* was %i; ISO C89: 0 <= line number <= 32767 */' \
                    % (1, Path, LineN) 
        else:
            return '#   line %i "%s"' % (LineN, Path) 

    def _SOURCE_REFERENCE_END(self, SourceReference=None):
        """Return a code fragment that returns a source reference pragma which
        tells about the file where the code has been pasted. If the SourceReference
        is provided, it may be checked wether the 'return pragma' is necessary.
        If not, an empty string is returned.
        """
        if SourceReference is None or not SourceReference.is_void(): 
            return '\n<<<<LINE_PRAGMA_WITH_CURRENT_LINE_N_AND_FILE_NAME>>>>\n'
        else:
            return ""

    def NAMESPACE_OPEN(self, NameList):
        if not NameList: return ""
        return " ".join(("    " * i + "namespace %s {" % name) for i, name in enumerate(NameList))

    def NAMESPACE_CLOSE(self, NameList):
        if not NameList: return ""
        return " ".join("} /* close %s */" % name for name in NameList)

    def NAMESPACE_REFERENCE(self, NameList, TrailingDelimiterF=True):
        if NameList and NameList[0]: result = "::".join(NameList)
        else:                        result = ""
        if TrailingDelimiterF: return result + "::"
        else:                  return result

    @typed(Name=(None, str,str), NameList=(None, list))
    def NAME_IN_NAMESPACE(self, Name, NameList):
        if NameList and NameList[0]: 
            return "%s%s" % (self.NAMESPACE_REFERENCE(NameList), Name)
        elif Name:
            return Name
        else:
            return ""

    def COMMENT(self, Comment):
        """Eliminated Comment Terminating character sequence from 'Comment'
           and comment it into a single line comment.
           For compatibility with C89, we use Slash-Star comments only, no '//'.
        """
        comment = Comment.replace("/*", "SLASH_STAR").replace("*/", "STAR_SLASH")
        return "/* %s */\n" % comment

    def ML_COMMENT(self, Comment, IndentN=4):
        indent_str = " " * IndentN
        comment = Comment.replace("/*", "SLASH_STAR").replace("*/", "STAR_SLASH").replace("\n", "\n%s * " % indent_str)
        return "%s/* %s\n%s */\n" % (indent_str, comment, indent_str)

    def COMMENT_STATE_MACHINE(self, txt, SM):
        txt.append(self.ML_COMMENT(
                        "BEGIN: STATE MACHINE\n"        + \
                        SM.get_string(NormalizeF=False) + \
                        "END: STATE MACHINE")) 

    def TOKEN_SET_MEMBER(self, Member, Value):
        return "self.token_p()->%s = %s;" % (Member, Value)

    def TOKEN_SEND(self, TokenName):
        return "self.send(%s);" % TokenName

    def TOKEN_SEND_N(self, N, TokenName):
        return "self.send_n(%s, (size_t)%s);\n" % (TokenName, N)

    def TOKEN_SEND_TEXT(self, TokenName, Begin, End):
        return "self.send_text(%s, %s, %s);" % (TokenName, Begin, End)

    def DEFAULT_COUNTER_FUNCTION_NAME(self, ModeName):
        return self.NAME_IN_NAMESPACE_MAIN("%s_counter_on_arbitrary_lexeme" % ModeName)

    def DEFAULT_COUNTER_CALL(self, ModeName, EndPosition):
        end_position_str = self.REGISTER_NAME(EndPosition)
        return "%s((QUEX_TYPE_ANALYZER*)me, LexemeBegin, %s);\n" % (self.DEFAULT_COUNTER_FUNCTION_NAME(ModeName), end_position_str)

    @typed(TypeStr=(str,str), MaxTypeNameL=(int,int), VariableName=(str,str))
    def CLASS_MEMBER_DEFINITION(self, TypeStr, MaxTypeNameL, VariableName):
        return "    %s%s %s;" % (TypeStr, " " * (MaxTypeNameL - len(TypeStr)), VariableName)

    def VARIABLE_DECLARATION(self, variable):
        if not condition.do(variable.condition):
            return ""

        if variable.constant_f: const_str = "const "
        else:                   const_str = ""

        init_value_str = self._interpreted_initial_value(variable.initial_value)

        return "%s%s %s%s;" % (const_str, variable.type, variable.name, init_value_str)

    def MEMBER_VARIABLE_DECLARATION(self, variable):
        return self.VARIABLE_DECLARATION(variable)

    def MEMBER_FUNCTION_DECLARATION(self, signature):
        if not condition.do(signature.condition):
            return ""
        def argument_str(arg_type, arg_name, default):
            if default:
                return "%s %s = %s" % (arg_type, arg_name, default) 
            else:
                return "%s %s" % (arg_type, arg_name) 
        argument_list_str = ", ".join(argument_str(arg_type, arg_name, default) 
                                      for arg_type, arg_name, default in signature.argument_list)
        if signature.return_type != "void": return_str = "return "
        else:                               return_str = ""

        call_argument_list  = ["this"] + [ arg_name for arg_type, arg_name, default in signature.argument_list ]
        call_definition_str = "QUEX_NAME(MF_%s)(%s)" % (signature.function_name,
                                                        ", ".join(call_argument_list))
        return "%s %s(%s) { %s%s; }" % (signature.return_type, signature.function_name, 
                                        argument_list_str, return_str, call_definition_str)

    def MEMBER_FUNCTION_ASSIGNMENT(self, MemberFunctionSignatureList):
        return ""

    def REGISTER_NAME(self, Register):
        return {
            E_R.EndOfStreamP:    "(me->buffer.input.end_p)",
            E_R.BufferFrontP:    "(me->buffer._memory._front)",
            E_R.InputP:          "(me->buffer._read_p)",
            E_R.InputPBeforeReload: "read_p_before_reload",
            E_R.PositionDelta:      "position_delta",
            E_R.Column:          "(me->counter._column_number_at_end)",
            E_R.Line:            "(me->counter._line_number_at_end)",
            E_R.LexemeStartP:    "(me->buffer._lexeme_start_p)",
            E_R.MinRequiredBufferPositionWithoutLexemeStartP: 
                                 "QUEX_GNAME(Buffer_get_min_position_without_lexeme_start_p)(&me->buffer, &position[0], PositionRegisterN)",
            E_R.BackupStreamPositionOfLexemeStartP: 
                                  "(me->buffer._backup_lexatom_index_of_lexeme_start_p)",
            E_R.LexemeStartBeforeReload: 
                                "(lexeme_start_before_reload_p)",
            E_R.CountReferenceP: "count_reference_p",
            E_R.LexemeEnd:       "LexemeEnd",
            E_R.Counter:         "counter",
            E_R.LoopRestartP:    "loop_restart_p",
            E_R.BackupP:         "backup_p",
            E_R.LoadResult:      "load_result",
        }[Register]

    def DEFINE_NESTED_RANGE_COUNTER(self):
        return "#define Counter %s" % self.REGISTER_NAME(E_R.Counter)

    def DEFINE_BAD_LEXATOM(self):
        return "#define BadLexatom ((me->buffer._read_p > me->buffer._memory._front && me->buffer._read_p <= me->buffer.input.end_p) ? (me->buffer._read_p[-1]) : (QUEX_TYPE_LEXATOM)-1)"

    def UNDEFINE_BAD_LEXATOM(self):
        return "#undef BadLexatom"

    def COMMAND_LIST(self, OpList, dial_db=None):
        return [ 
            "%s\n" % self.COMMAND(cmd, dial_db) for cmd in OpList
        ]

    @typed(dial_db=(None, DialDB))
    def COMMAND(self, Op, dial_db=None):
        if Op.id == E_Op.ReturnFromLexicalAnalysis:
            return self.PURE_RETURN

        if Op.id == E_Op.Accepter:
            txt = []
            for i, element in enumerate(Op.content):
                block = "last_acceptance = %s; __quex_debug(\"last_acceptance = %s\\n\");\n" \
                        % (self.ACCEPTANCE(element.acceptance_id), self.ACCEPTANCE(element.acceptance_id))
                txt.extend(
                    self.IF_ACCEPTANCE_CONDITION_SET(i==0, 
                                                     element.acceptance_condition_set, 
                                                     block)
                )
            return "".join(txt)

        elif Op.id == E_Op.IfAcceptanceConditionSetPositionAndGoto:
            block = self.position_and_goto(Op.content.router_element, dial_db)
            txt   = self.IF_ACCEPTANCE_CONDITION_SET(True, 
                                                     Op.content.acceptance_condition_set,
                                                     block)
            return "".join(txt)

        elif Op.id == E_Op.RouterByLastAcceptance:
            case_list = [
                (self.ACCEPTANCE(element.acceptance_id), 
                 self.position_and_goto(element, dial_db))
                for element in Op.content
            ]

            txt = self.BRANCH_TABLE_ON_STRING("last_acceptance", case_list)
            result = "".join(self.GET_PLAIN_STRINGS(txt, dial_db))
            return result

        elif Op.id == E_Op.RouterOnStateKey:
            case_list = [
                (state_key, self.GOTO(door_id, dial_db)) for state_key, door_id in Op.content
            ]
            if Op.content.register == E_R.PathIterator:
                key_txt = "path_iterator - path_walker_%i_path_base" % Op.content.mega_state_index 
            elif Op.content.register == E_R.TemplateStateKey:
                key_txt = "state_key"
            else:
                assert False

            txt = self.BRANCH_TABLE(key_txt, case_list)
            result = "".join(self.GET_PLAIN_STRINGS(txt, dial_db))
            return result

        elif Op.id == E_Op.QuexDebug:
            return '__quex_debug("%s");\n' % Op.content.string

        elif Op.id == E_Op.QuexAssertNoPassage:
            return self.UNREACHABLE

        elif Op.id == E_Op.PasspartoutCounterCall:
            return self.DEFAULT_COUNTER_CALL(Op.content.mode_name, Op.content.end_position)

        elif Op.id == E_Op.GotoDoorId:
            return self.GOTO(Op.content.door_id, dial_db)

        elif Op.id == E_Op.GotoDoorIdIfCounterEqualZero:
            return "if( %s == 0 ) %s\n" % (self.REGISTER_NAME(E_R.Counter), 
                                           self.GOTO(Op.content.door_id, dial_db))

        elif Op.id == E_Op.GotoDoorIdIfInputPNotEqualPointer:
            return "if( %s != %s ) %s\n" % (self.INPUT_P(), 
                                            self.REGISTER_NAME(Op.content.pointer), 
                                            self.GOTO(Op.content.door_id, dial_db))
        elif Op.id == E_Op.GotoDoorIdIfInputPEqualPointer:
            return "if( %s == %s ) %s\n" % (self.INPUT_P(), 
                                            self.REGISTER_NAME(Op.content.pointer), 
                                            self.GOTO(Op.content.door_id, dial_db))

        elif Op.id == E_Op.IndentationHandlerCall:
            return self.INDENTATION_HANDLER_CALL(Op.content.mode_name)

        elif Op.id == E_Op.IndentationBadHandlerCall:
            return self.INDENTATION_BAD_HANDLER_CALL(Op.content.mode_name)

        elif Op.id == E_Op.Assign:
            txt = "%s = %s" % (self.REGISTER_NAME(Op.content[0]), self.REGISTER_NAME(Op.content[1]))
            if Op.content.condition == "COLUMN":
                txt = "$$<count-column> %s$$" % txt
            return "    %s;\n" % txt

        elif Op.id == E_Op.AssignConstant:
            register = Op.content.register
            value    = Op.content.value 

            if  register == E_R.Column:
                assignment = "%s = (size_t)%s" % (self.REGISTER_NAME(register), value)
                return "    $$<count-column> %s;$$\n" % assignment
            elif register == E_R.Line:
                assignment = "%s = (size_t)%s" % (self.REGISTER_NAME(register), value)
                return "    $$<count-line> %s;$$\n" % assignment
            else:
                assignment = "%s = %s" % (self.REGISTER_NAME(register), value)
                return "    %s;\n" % assignment

        elif Op.id == E_Op.AssignPointerDifference:
            return "    %s = %s - %s;\n" % (self.REGISTER_NAME(Op.content.result), 
                                            self.REGISTER_NAME(Op.content.big),
                                            self.REGISTER_NAME(Op.content.small))

        elif Op.id == E_Op.PointerAssignMin:
            txt = "%s = %s < %s ? %s : %s" % (self.REGISTER_NAME(Op.content.result), 
                                              self.REGISTER_NAME(Op.content.a),
                                              self.REGISTER_NAME(Op.content.b),
                                              self.REGISTER_NAME(Op.content.a),
                                              self.REGISTER_NAME(Op.content.b))
            if Op.content.condition == "COLUMN":
                txt = "$$<count-column> %s$$" % txt
            return "    %s;\n" % txt

        elif Op.id == E_Op.PointerAdd:
            txt = "%s = &%s[%s]" % (self.REGISTER_NAME(Op.content.pointer), 
                                    self.REGISTER_NAME(Op.content.pointer),
                                    self.REGISTER_NAME(Op.content.offset))
            if Op.content.condition == "COLUMN":
                txt = "$$<count-column> %s$$" % txt
            return "    %s;\n" % txt

        elif Op.id == E_Op.ColumnCountSet:
            return self.COUNTER_COLUM_SET(Op.content.value)

        elif Op.id == E_Op.ColumnCountShift:
            return self.COUNTER_SHIFT_COLUMN_COUNT()

        elif Op.id == E_Op.ColumnCountAdd:
            if not Op.content.value or Op.content.factor == 0:
                return ""
            else:
                return "%s\n" % self.COUNTER_COLUM_ADD("(size_t)%s" % self.VALUE_STRING(Op.content.value),
                                                       Op.content.factor)

        elif Op.id == E_Op.ColumnCountGridAdd:
            return "".join(self.COUNTER_COLUMN_GRID_STEP(Op.content.grid_size, Op.content.step_n))

        elif Op.id == E_Op.ColumnCountReferencePSet:
            pointer_name = self.REGISTER_NAME(Op.content.pointer)
            offset       = Op.content.offset
            reference_p  = E_R.CountReferenceP
            return self.REFERENCE_P_RESET(pointer_name, offset, reference_p)

        elif Op.id == E_Op.ColumnCountReferencePDeltaAdd:
            reference_p  = E_R.CountReferenceP
            return self.REFERENCE_P_COLUMN_ADD(self.REGISTER_NAME(Op.content.pointer), 
                                               Op.content.column_n_per_chunk, 
                                               Op.content.subtract_one_f,
                                               reference_p) 
        elif Op.id == E_Op.LineCountShift:
            return self.COUNTER_SHIFT_LINE_COUNT()

        elif Op.id == E_Op.LineCountAdd:
            if not Op.content.value or Op.content.factor == 0:
                return ""
            else:
                return "%s\n" % self.COUNTER_LINE_ADD("(size_t)%s" % self.VALUE_STRING(Op.content.value),
                                                       Op.content.factor)

        elif Op.id == E_Op.StoreInputPosition:
            # Assume that checking for the pre-context is just overhead that 
            # does not accelerate anything.
            if Op.content.offset == 0:
                return "    position[%i] = me->buffer._read_p; __quex_debug(\"position[%i] = input_p;\\n\");\n" \
                       % (Op.content.position_register, Op.content.position_register)
            else:
                return "    position[%i] = me->buffer._read_p - %i; __quex_debug(\"position[%i] = input_p - %i;\\n\");\n" \
                       % (Op.content.position_register, Op.content.offset, Op.content.position_register, Op.content.offset)

        elif Op.id == E_Op.PreContextOK:
            value = Op.content.acceptance_condition_id 
            return   "    pre_context_%i_fulfilled_f = 1;\n"                         % value \
                   + "    __quex_debug(\"pre_context_%i_fulfilled_f = true\\n\");\n" % value

        elif Op.id == E_Op.TemplateStateKeySet:
            value = Op.content.state_key
            return   "    state_key = %i;\n"                      % value \
                   + "    __quex_debug(\"state_key = %i\\n\");\n" % value

        elif Op.id == E_Op.PathIteratorSet:
            offset_str = ""
            if Op.content.offset != 0: offset_str = " + %i" % Op.content.offset
            txt =   "    path_iterator  = path_walker_%i_path_%i%s;\n"                   \
                  % (Op.content.path_walker_id, Op.content.path_id, offset_str)        \
                  + "    __quex_debug(\"path_iterator = (Pathwalker: %i, Path: %i, Offset: %s)\\n\");\n" \
                  % (Op.content.path_walker_id, Op.content.path_id, offset_str)
            return txt

        elif Op.id == E_Op.PrepareAfterReload:
            on_success_adr = Op.content.on_success_door_id.related_address
            on_failure_adr = Op.content.on_failure_door_id.related_address

            dial_db.mark_address_as_routed(on_success_adr)
            dial_db.mark_address_as_routed(on_failure_adr)

            return   "    target_state_index = %s; target_state_else_index = %s;\n"  \
                   % (self.ADRESS_LABEL_REFERENCE(on_success_adr), 
                      self.ADRESS_LABEL_REFERENCE(on_failure_adr))                                                       

        elif Op.id == E_Op.LexemeResetTerminatingZero:
            return "    QUEX_LEXEME_TERMINATING_ZERO_UNDO(&me->buffer);\n"

        elif Op.id == E_Op.InputPDereference:
            return "    %s\n" % self.ASSIGN("input", self.INPUT_P_DEREFERENCE())

        elif Op.id == E_Op.Increment:
            return "    ++%s;\n" % self.REGISTER_NAME(Op.content.register)

        elif Op.id == E_Op.Decrement:
            return "    --%s;\n" % self.REGISTER_NAME(Op.content.register)

        else:
            assert False, "Unknown command '%s'" % Op.id

    def SAFE_STRING(self, String):
        def get(Letter):
            if Letter in ['\\', '"', '\n', '\t', '\r', '\a', '\v']: return "\\" + Letter
            else:                                                   return Letter 

        return "".join(get(letter) for letter in String)

    def TERMINAL_CODE(self, TerminalStateList, TheAnalyzer, dial_db): 
        text = [
            templates._terminal_state_prolog
        ]
        terminal_door_id_list = []
        for terminal in sorted(TerminalStateList, key=lambda x: str(x.incidence_id())):
            terminal_door_id_list.append(terminal.door_id)

            t_txt = ["%s\n    __quex_debug(\"* TERMINAL %s\\n\");\n" % \
                     (self.LABEL(terminal.door_id), self.SAFE_STRING(terminal.name()))]
            code  = terminal.code(dial_db)
            assert none_isinstance(code, list)
            t_txt.extend(code)
            t_txt.append("\n")

            text.extend(t_txt)

        text.append(
            "if(0) {\n"
            "    /* Avoid unreferenced labels. */\n"
        )
        text.extend(
            "    %s\n" % self.GOTO(door_id, dial_db)
            for door_id in terminal_door_id_list
        )
        text.append("}\n")
        return text

    @typed(dial_db=DialDB)
    def ANALYZER_FUNCTION(self, ModeName, Setup, VariableDefs, 
                          FunctionBody, dial_db, ModeNameList):
        return templates._analyzer_function(ModeName, Setup, VariableDefs, 
                                            FunctionBody, dial_db, ModeNameList)

    def REENTRY_PREPARATION(self, PreConditionIDList, OnAfterMatchCode, dial_db):
        return templates.reentry_preparation(self, PreConditionIDList, OnAfterMatchCode, dial_db)

    @typed(dial_db=DialDB)
    def HEADER_DEFINITIONS(self, dial_db):
        return blue_print(cpp_header_definition_str, [
            ("$$CONTINUE_WITH_ON_AFTER_MATCH$$", self.LABEL_STR_BY_ADR(DoorID.continue_with_on_after_match(dial_db).related_address)),
            ("$$RETURN_WITH_ON_AFTER_MATCH$$",   self.LABEL_STR_BY_ADR(DoorID.return_with_on_after_match(dial_db).related_address)),
        ])

    def RETURN_THIS(self, Value):
        return "return %s;" % Value

    def CALL_MODE_HAS_ENTRY_FROM(self, ModeName):
        return   "#   ifdef QUEX_OPTION_ASSERTS\n" \
               + "    QUEX_NAME(%s).has_entry_from(FromMode);\n" % ModeName \
               + "#   endif\n"

    def CALL_MODE_HAS_EXIT_TO(self, ModeName):
        return   "#   ifdef QUEX_OPTION_ASSERTS\n" \
               + "    QUEX_NAME(%s).has_exit_to(ToMode);\n" % ModeName \
               + "#   endif\n"

    def ADRESS_LABEL_REFERENCE(self, Adr):
        if Setup.computed_gotos_f: return "&&_%i" % Adr
        else:                      return "%i" % Adr

    @typed(DoorId=DoorID)
    def GOTO(self, DoorId, dial_db):
        if DoorId.last_acceptance_f():
            if Setup.computed_gotos_f:
                return "goto *last_acceptance;"
            else:
                return "goto QUEX_TERMINAL_ROUTER;" # last_acceptance supposed to be set!

        return self.GOTO_ADDRESS(DoorId.related_address, dial_db)


    def LABEL_PLAIN(self, Label):
        return "%s:" % Label.strip()

    @typed(DoorId=DoorID)
    def LABEL(self, DoorId):
        return "%s:" % self.LABEL_STR_BY_ADR(DoorId.related_address)

    @typed(DoorId=DoorID)
    def LABEL_STR(self, DoorId):
        return "%s" % self.LABEL_STR_BY_ADR(DoorId.related_address)

    def LABEL_STR_BY_ADR(self, Adr):
        return "_%s" % Adr

    def GOTO_BY_VARIABLE(self, VariableName):
        if Setup.computed_gotos_f:
            return "goto *%s;" % VariableName 
        else:
            return "{ target_state_index = %s; goto QUEX_LABEL_STATE_ROUTER; }" % VariableName

    def GOTO_STRING(self, LabelStr):
        return "goto %s;" % LabelStr

    @typed(dial_db=DialDB)
    def GOTO_ADDRESS(self, Address, dial_db):
        dial_db.mark_address_as_gotoed(Address)
        return "goto %s;" % self.LABEL_STR_BY_ADR(Address)

    def COUNTER_SHIFT_VALUES(self):
        return self.COUNTER_SHIFT_COLUMN_COUNT() + self.COUNTER_SHIFT_LINE_COUNT()

    def COUNTER_SHIFT_COLUMN_COUNT(self):
        if condition.do("count-column"): return "    me->counter._column_number_at_begin = me->counter._column_number_at_end;"
        else:                            return "" 

    def COUNTER_SHIFT_LINE_COUNT(self):
        if condition.do("count-line"): return "    me->counter._line_number_at_begin = me->counter._line_number_at_end;"
        else:                          return "" 

    def COUNTER_LINE_ADD(self, Arg, Factor=1):
        arg = Arg
        if Factor != 1: arg = self.MULTIPLY_WITH(arg, Factor)
        if condition.do("count-line"): return "    me->counter._line_number_at_end += (%s); __quex_debug_counter();" % arg
        else:                          return ""

    def COUNTER_COLUM_ADD(self, Arg, Factor=1):
        arg = Arg
        if Factor != 1 and Factor != E_Count.VOID: arg = self.MULTIPLY_WITH(arg, Factor)

        if condition.do("count-column"): return "    me->counter._column_number_at_end += (%s); __quex_debug_counter();" % arg
        else:                            return ""

    def COUNTER_COLUM_SET(self, Arg):
        if condition.do("count-column"): return "    me->counter._column_number_at_end = (%s); __quex_debug_counter();" % Arg
        else:                            return ""

    def COUNTER_COLUMN_GRID_STEP(self, GridWidth, StepN=1):
        """A grid step is an addition which depends on the current value 
        of a variable. It sets the value to the next valid value on a grid
        with a given width. The general solution is 

                  x  = (x - x % GridWidth) # go back to last grid.
                  x += GridWidth           # go to next grid step.

        For 'GridWidth' as a power of '2' there is a slightly more
        efficient solution.
        """
        assert GridWidth > 0
        TypeName     = "size_t"
        VariableName = "self.counter._column_number_at_end"

        grid_with_str = self.VALUE_STRING(GridWidth)
        log2          = self._get_log2_if_power_of_2(GridWidth)
        if log2 is not None:
            # For k = a potentials of 2, the expression 'x - x % k' can be written as: x & ~mask(log2) !
            # Thus: x = x - x % k + k = x & mask + k
            mask = (1 << int(log2)) - 1
            if mask != 0: cut_str = "%s &= ~ ((%s)0x%X)" % (VariableName, TypeName, mask)
            else:         cut_str = ""
        else:
            cut_str = "%s -= (%s %% (%s))" % (VariableName, VariableName, grid_with_str)

        add_str = "%s += %s + 1" % (VariableName, self.MULTIPLY_WITH(grid_with_str, StepN))

        result = []
        result.append("$$<count-column>--------------------------------------------\n")
        result.append("%s -= 1;\n"        % VariableName)
        if cut_str: result.append("%s;\n" % cut_str)
        result.append("%s;\n"             % add_str)
        result.append("$$----------------------------------------------------------\n")

        return result

    def MULTIPLY_WITH(self, FactorStr, NameOrValue):
        if isinstance(NameOrValue, str):
            return "%s * %s" % (FactorStr, self.VALUE_STRING(NameOrValue))

        x = NameOrValue

        if x == 0:
            return "0"
        elif x == 1:
            return FactorStr
        elif x < 1:
            x    = int(round(1.0 / x))
            log2 = self._get_log2_if_power_of_2(x)
            if log2 is not None:
                return "%s >> %i" % (FactorStr, int(log2))
            else:
                return "%s / %s" % (FactorStr, self.VALUE_STRING(x))
        else:
            log2 = self._get_log2_if_power_of_2(x)
            if log2 is not None:
                return "%s << %i" % (FactorStr, int(log2))
            else:
                return "%s * %s" % (FactorStr, self.VALUE_STRING(x))

    def VALUE_STRING(self, NameOrValue):
        if isinstance(NameOrValue, str):
            return "%s" % NameOrValue # "self.%s" % NameOrValue
        elif hasattr(NameOrValue, "is_integer") and NameOrValue.is_integer():
            return "%i" % NameOrValue
        else:
            return "%s" % NameOrValue

    def REFERENCE_P_COLUMN_ADD(self, IteratorName, ColumnCountPerChunk, SubtractOneF, RegReferencePointer):
        """Add reference pointer count to current column. There are two cases:
           (1) The character at the end is part of the 'constant column count region'.
               --> We do not need to go one back. 
           (2) The character at the end is NOT part of the 'constant column count region'.
               --> We need to go one back (SubtractOneF=True).

           The second case happens, for example, when a 'grid' (tabulator) character is
           hit. Then, one needs to get before the tabulator before one jumps to the 
           next position.
        """
        minus_one = { True: " - 1", False: "" }[SubtractOneF]
        delta_str = "(%s - %s%s)" % (IteratorName, self.REGISTER_NAME(RegReferencePointer), minus_one)
        return "%s\n" % self.COUNTER_COLUM_ADD("(size_t)(%s)" % self.MULTIPLY_WITH(delta_str, ColumnCountPerChunk))

    def REFERENCE_P_RESET(self, IteratorName, Offset, RegReferencePointer):
        name = self.REGISTER_NAME(RegReferencePointer)
        if   Offset > 0:
            return "$$<count-column> %s = %s + %i;$$\n" % (name, IteratorName, Offset) 
        elif Offset < 0:
            return "$$<count-column> %s = %s - %i;$$\n" % (name, IteratorName, - Offset) 
        else:
            return "$$<count-column> %s = %s;$$\n" % (name, IteratorName)

    def INCLUDE(self, Path, Condition=None):
        if   not Path:                    return ""
        elif not condition.do(Condition): return ""
        else:                             return "#include \"%s\"" % Path

    def ENGINE_TEXT_EPILOG(self):
        if Setup.analyzer_derived_class_file: header = self.INCLUDE(Setup.analyzer_derived_class_file)
        else:                                 header = self.INCLUDE(Setup.output_header_file)
        footer = self.FOOTER_IN_IMPLEMENTATION()
        return cpp_implementation_headers_txt.replace("$$HEADER$$", header) \
                                             .replace("$$FOOTER$$", footer)

    def FOOTER_IN_IMPLEMENTATION(self):
        return ""
    
    def MODE_GOTO(self, Mode):
        return "self.enter_mode(%s);" % Mode

    def MODE_GOSUB(self, Mode):
        return "self.push_mode(%s);" % Mode

    def MODE_RETURN(self):
        return "self.pop_mode();"

    def NAME_IN_NAMESPACE_MAIN(self, Name):
        return "QUEX_NAME(%s)" % Name

    def ACCEPTANCE(self, AcceptanceID):
        if   AcceptanceID == E_IncidenceIDs.MATCH_FAILURE: return "((QUEX_TYPE_ACCEPTANCE_ID)-1)"
        elif AcceptanceID == E_IncidenceIDs.BAD_LEXATOM:   return "((QUEX_TYPE_ACCEPTANCE_ID)-2)"
        else:                                              return "%i" % AcceptanceID

    @typed(Condition=list)
    def IF_PLAIN(self, FirstF, Condition, Consequence):
        if not Condition:
            if FirstF: return [ "%s" % "".join(Consequence) ]
            else:      return [ "else { %s }" % "".join(Consequence) ]
        else:
            if not FirstF: else_str = "else "
            else:          else_str = ""
            return [ 
                "%sif( %s ) {\n" % (else_str, " ".join(Condition)),
                "%s\n" % "".join(Consequence), 
                "}\n" 
            ]

    def IF(self, LValue, Operator, RValue, FirstF=True, SimpleF=False, SpaceF=False):
        if isinstance(RValue, str): condition = "%s %s %s"   % (LValue, Operator, RValue)
        else:                                 condition = "%s %s 0x%X" % (LValue, Operator, RValue)
        if not SimpleF:
            if FirstF: return "if( %s ) {\n"          % condition
            else:      return "\n} else if( %s ) {\n" % condition
        else:
            if FirstF: 
                if SpaceF: return "if     ( %s ) " % condition
                else:      return "if( %s ) "      % condition
            else:          return "else if( %s ) " % condition

    def IF_INPUT(self, Condition, Value, FirstF=True, NewlineF=True):
        return self.IF("input", Condition, Value, FirstF, SimpleF=not NewlineF)

    def IF_X(self, Condition, Value, Index, Length):
        """Index  = index of decision in list of if-else-if.
           Length = total number of decisions in if-else-if block.

        Calls 'IF' with the 'SpaceF=True' so that the first if-statement
        contains a 'pretty space' that makes it aligned with the remaining 
        decisions.
        """
        return self.IF("input", Condition, Value, Index==0, SimpleF=True, SpaceF=(Length>2))

    def IF_ACCEPTANCE_CONDITION_SET(self, FirstF, AccConditionSet, Consequence):
        def append_if_pre_context(acc_condition_id, result):
            if acc_condition_id == E_AcceptanceCondition.BEGIN_OF_LINE:
                code = "me->buffer._lexatom_before_lexeme_start == '\\n'"
            elif acc_condition_id == E_AcceptanceCondition.BEGIN_OF_STREAM:
                code = "QUEX_NAME(Buffer_is_begin_of_stream)(&me->buffer)"
            elif isinstance(acc_condition_id, int):
                code = "pre_context_%i_fulfilled_f" % acc_condition_id
            else:
                return False
            result.append(code)
            return True

        def append_if_post_context(acc_condition_id, result):
            if acc_condition_id == E_AcceptanceCondition.END_OF_STREAM:
                code = "QUEX_NAME(Buffer_is_end_of_stream)(&me->buffer)"
            else:
                return False
            result.append(code)
            return True

        remainder = list(AccConditionSet)
        pre_condition_list = []
        do_and_delete_if(remainder, append_if_pre_context, pre_condition_list)
        post_condition_list = []
        do_and_delete_if(remainder, append_if_post_context, post_condition_list)

        # Combinate logically: Or(pre-contexts) And Or(post-contexts)
        pre_combined  = self.BINARY_OPERATION_LIST(self.OR, pre_condition_list)
        post_combined = self.BINARY_OPERATION_LIST(self.OR, post_condition_list)
        all_combined  = self.BINARY_OPERATION_LIST(self.AND, ["".join(pre_combined), 
                                                              "".join(post_combined)])

        return self.IF_PLAIN(FirstF, all_combined, Consequence)

    def PRE_CONTEXT_RESET(self, PreConditionIDList):
        if PreConditionIDList is None: return ""
        return "".join([
            "    %s\n" % self.ASSIGN("pre_context_%s_fulfilled_f" % acceptance_condition_id, 0)
            for acceptance_condition_id in PreConditionIDList
        ])

    def TRANSITION_MAP_TARGET(self, Interval, Target):
        assert isinstance(Target, str)
        if not Setup.comment_transitions_f or Interval is None:
            return Target
        else:
            return "%s %s" % (Target, self.COMMENT(Interval.get_utf8_string()))

    def ASSIGN(self, X, Y):
        return "%s = %s;" % (X, Y)

    def ASSIGN_MIN_REQUIRED_POSITION_TO_LEXEME_START_P(self):
        return self.ASSIGN_MIN_REQUIRED_POSITION_TO_LEXEME_START_P()

    def SIGNATURE(self, Prolog, FunctionName, ReturnType, ArgList):
        return "%s %s %s(%s)" % (Prolog, ReturnType, FunctionName, 
                                 ", ".join("%s %s" % (type_str, name_str) for type_str, name_str in ArgList))

    def debug_unit_name_set(self, Name):
        self.__debug_unit_name = Name

    def STATE_DEBUG_INFO(self, TheState, GlobalEntryF):
        assert isinstance(TheState, Processor)
        name = self.__debug_unit_name

        if isinstance(TheState, TemplateState):
            return "    __quex_debug_template_state(\"%s\", %i, state_key);\n" \
                   % (name, TheState.index)
        elif isinstance(TheState, PathWalkerState):
            return "    __quex_debug_path_walker_state(\"%s\", %i, path_walker_%s_path_base, path_iterator);\n" \
                   % (name, TheState.index, TheState.index)
        elif GlobalEntryF: 
            return "    __quex_debug_init_state(\"%s\", %i);\n" \
                   % (name, TheState.index)
        elif TheState.index == E_StateIndices.DROP_OUT:
            return "    __quex_debug(\" Drop-Out Catcher\\n\");\n"
        elif isinstance(TheState.index, int):
            return "    __quex_debug_state(%i);\n" % TheState.index
        else:
            return ""

    @typed(X=RouterContentElement)
    def POSITIONING(self, X):
        Positioning = X.positioning
        Register    = X.position_register
        if   Positioning == E_TransitionN.VOID: 
            return   "    __quex_assert(position[%i] != (void*)0);\n" % Register \
                   + "    me->buffer._read_p = position[%i];\n" % Register
        # "_read_p = lexeme_start_p + 1" is done by TERMINAL_FAILURE. 
        elif Positioning == E_TransitionN.LEXEME_START_PLUS_ONE: 
            return "    %s = %s + 1;\n" % (self.INPUT_P(), self.LEXEME_START_P())
        elif Positioning > 0:     
            return "    me->buffer._read_p -= %i;\n" % Positioning
        elif Positioning == 0:    
            return ""
        else:
            assert False 

    def CONDITION_SEQUENCE(self, ConditionList, ConsequenceList, ElseConsequence=None):
        assert all(type(condition) == list for condition in ConditionList)
        txt = flatten(
            self.IF_PLAIN((i==0), cc[0], Consequence=cc[1])
            for i, cc in enumerate(zip(ConditionList, ConsequenceList))
        )
        if ElseConsequence:
            txt.extend([self.ELSE, ElseConsequence, self.END_IF])
        return txt

    def COMPARISON_SEQUENCE(self, IntervalEffectSequence, get_decision):
        """Get a sequence of comparisons that map intervals to effects as given
        by 'IntervalEffectSequence'. The if-statements are coming out of 
        'get_decision'. The 'IntervalEffectSequence' is a list of pairs

                          (Interval, Effect-Text)

        meaning, that if 'input' is inside Interval, the 'Effect-Text' shall be
        executed.

        RETURNS: C-code that implements the comparison sequences.
        """
        L = len(IntervalEffectSequence)

        if   L == 0: return []
        elif L == 1: return ["%s\n" % IntervalEffectSequence[0][1]]

        sequence = [
            (get_decision(entry[0], i, L), entry[1])
            for i, entry in enumerate(IntervalEffectSequence)
        ]

        max_L = max(len(cause) for cause, effect in sequence)

        return [
            "%s %s%s\n" % (cause, " " * (max_L - len(cause)), effect)
            for cause, effect in sequence
        ]

    def CASE_STR(self, Format):
        return {
            "hex": "case 0x%X: ", 
            "dec": "case %i: "
        }[Format]

    def CASE_SELECT(self, Variable, CaseCodeList, Default):
        txt = ["switch( %s ) {\n" % Variable ]

        done_set = set([])
        for case, code in CaseCodeList:
            if case in done_set: continue
            done_set.add(case)
            txt.append("case %s: {\n" % case)
            if type(code) == list: txt.extend(code)
            else:                  txt.append(code)
            txt.append("}\n")

        txt.append("default: {\n")
        if type(code) == list: txt.extend(code)
        else:                  txt.append(code)
        txt.append("}\n")


        txt.append("}\n")

        return txt

    def BRANCH_TABLE(self, Selector, CaseList, CaseFormat="hex", DefaultConsequence=None):
        case_str = self.CASE_STR(CaseFormat)

        def case_integer(item, C, get_content):
            if item is None: return ["default: %s\n" % get_content(C)]
            return [ "%s %s\n" % (case_str % item, get_content(C)) ]

        return self._branch_table_core(Selector, CaseList, case_integer, DefaultConsequence)

    def BRANCH_TABLE_ON_STRING(self, Selector, CaseList):
        def case_string(item, C, get_content):
            if item is None: return ["default: %s\n" % get_content(C)]
            return [ "case %s: %s\n" % (item, get_content(C)) ]

        return self._branch_table_core(Selector, CaseList, case_string)

    def BRANCH_TABLE_ON_INTERVALS(self, Selector, CaseList, CaseFormat="hex", 
                                  DefaultConsequence=None):
        case_str = self.CASE_STR(CaseFormat)

        def case_list(From, To):
            return "".join("%s" % (case_str % i) for i in range(From, To))

        def case_list_iterable(item):
            # Next number divisible by '8' and greater than first_border
            first_border = int(item.begin / 8) * 8 + 8
            # Last number divisible by '8' and lesser than last_border
            last_border  = int((item.end - 1) / 8) * 8

            if first_border != item.begin:
                yield "%s\n" % case_list(item.begin, first_border)
            for begin in range(first_border, last_border-7, 8):
                yield "%s\n" % case_list(begin, begin + 8)
            yield "%s" % case_list(last_border, item.end)

        def case_interval(item, C, get_content):
            if item is None: return ["default: %s\n" % get_content(C)]

            size = item.end - item.begin
            if size == 1: 
                txt = [ case_str % (item.end-1) ]
            elif size <= 8: 
                txt = [ case_list(item.begin, item.end) ]
            else:
                txt = [
                    text
                    for text in case_list_iterable(item)
                ] 
            txt.append("%s\n" % get_content(C))
            return txt

        return self._branch_table_core(Selector, CaseList, case_interval, 
                                       DefaultConsequence)

    def _branch_table_core(self, Selector, CaseList, get_case, DefaultConsequence=None):

        def get_content(C):
            if type(C) == list: return "".join(C)
            else:               return C

        def iterable(CaseList, DefaultConsequence):
            if not CaseList:
                if DefaultConsequence is not None:
                    yield None, DefaultConsequence
                    return

            item, effect = CaseList[0]
            for item_ahead, effect_ahead in CaseList[1:]:
                if effect_ahead == effect: 
                    yield item, ""
                else:
                    yield item, effect
                item   = item_ahead
                effect = effect_ahead
            yield item, effect
            if DefaultConsequence is not None:
                yield None, DefaultConsequence

        if not CaseList and not DefaultConsequence:
            return []

        # TODO: Express as 'CASE_SELECT'
        txt = [ "switch( %s ) {\n" % Selector ]
        txt.extend(
            flatten(
                get_case(item, text, get_content)
                for item, text in iterable(CaseList, DefaultConsequence)
            )
        )
        txt.append("}\n")
        return txt

    def REPLACE_INDENT(self, txt_list, Start=0):
        for i, x in enumerate(islice(txt_list, Start, None), Start):
            if isinstance(x, int): txt_list[i] = "    " * x
        return txt_list

    def INDENT(self, txt_list, Add=1, Start=0):
        for i, x in enumerate(islice(txt_list, Start, None), Start):
            if isinstance(x, int): txt_list[i] += Add

    def GET_PLAIN_STRINGS(self, txt_list, dial_db):
        self.REPLACE_INDENT(txt_list)
        return get_plain_strings(txt_list, dial_db)

    def _interpreted_initial_value(self, Value):
        if Value == "<goto-label-void>": 
            if Setup.computed_gotos_f: return "(QUEX_TYPE_GOTO_LABEL)0"
            else:                      return "(QUEX_TYPE_GOTO_LABEL)-1"
        else:
            return Value

    def VARIABLE_DEFINITION(self, variable, LT, LN):
        variable_type = variable.variable_type
        variable_init = self._interpreted_initial_value(variable.initial_value)
        variable_name = variable.name

        if variable.element_n is not None: 
            if variable.element_n != 0:
                variable_name += "[%s]" % repr(variable.element_n)
            else:
                variable_type += "*"
                variable_init  = ["0x0"]

        if variable_init is None: 
            value = "/* un-initilized */"
        else:
            if type(variable_init) != list: variable_init = [ variable_init ]
            value = " = " + "".join(variable_init)

        return "    %s%s %s%s%s;" % (variable_type, " " * (LT - len(variable_type)), 
                                     variable_name, " " * (LN - len(variable_name)),
                                     value)

    def VARIABLE_DEFINITIONS(self, VariableDB):
        # ROBUSTNESS: Require 'target_state_index' and 'target_state_else_index'
        #             ALWAYS. Later, they are referenced in dead code to avoid
        #             warnings of unused variables.
        # BOTH: -- Used in QUEX_GOTO_STATE in case of no computed goto-s.
        #       -- During reload.
        VariableDB.require("target_state_index")
        VariableDB.require("target_state_else_index")

        if not VariableDB: return ""

        variable_list = list(VariableDB.get().values())

        LN = max(len(v.name) for v in variable_list)
        LT = max(len(v.variable_type) for v in variable_list)

        return "\n".join(
            self.VARIABLE_DEFINITION(variable, LT, LN)
            for variable in sorted(variable_list, key=lambda v: not v.priority_f)
            if condition.do(variable.condition)
        ) + "\n"

    def RAISE_ERROR_FLAG(self, Name):
        return "self.error_code_set_if_first(%s);\n" % Name

    def suspicious_RETURN_in_event_handler(self, IncidenceId, EventHandlerTxt):
        if     IncidenceId not in self.error_code_db \
           and IncidenceId != E_IncidenceIDs.END_OF_STREAM: return False
        return self.__re_FLUSH.search(EventHandlerTxt) is not None

    @typed(dial_db=DialDB)
    def RELOAD_PROCEDURE(self, ForwardF, dial_db, variable_db):
        assert self.__code_generation_reload_label is None

        if ForwardF: txt = cpp_reload_forward_str
        else:        txt = cpp_reload_backward_str

        variable_db.require_registers([E_R.LoadResult])

        adr_bad_lexatom  = DoorID.incidence(E_IncidenceIDs.BAD_LEXATOM, dial_db).related_address
        adr_load_failure = DoorID.incidence(E_IncidenceIDs.LOAD_FAILURE, dial_db).related_address

        txt = blue_print(txt, [
            ("$$ON_BAD_LEXATOM$$",               self.LABEL_STR_BY_ADR(adr_bad_lexatom)),
            ("$$ON_LOAD_FAILURE$$",              self.LABEL_STR_BY_ADR(adr_load_failure)),
            ("$$LOAD_RESULT$$",                  self.REGISTER_NAME(E_R.LoadResult)),
            ("$$BUFFER_LOAD_FW$$",               self.NAME_IN_NAMESPACE_MAIN("Buffer_load_forward")),
            ("$$BUFFER_LOAD_BW$$",               self.NAME_IN_NAMESPACE_MAIN("Buffer_load_backward")),
            ("$$GOTO target_state_index$$",      self.GOTO_BY_VARIABLE("target_state_index")),
            ("$$GOTO target_state_else_index$$", self.GOTO_BY_VARIABLE("target_state_else_index")),
        ])

        dial_db.mark_address_as_gotoed(adr_bad_lexatom)
        dial_db.mark_address_as_gotoed(adr_load_failure)

        return txt 

    def straighten_open_line_pragmas_new(self, Txt, FileName):
        if Txt is None: return None

        line_pragma_txt = self._SOURCE_REFERENCE_END().strip()

        new_content = []
        for line_n, line in enumerate(Txt.splitlines(), start=1):
            if line.strip() != line_pragma_txt:
                new_content.append(line)
            else:
                new_content.append(self.LINE_PRAGMA(FileName, line_n))
        return "\n".join(new_content)
        
    def straighten_open_line_pragmas(self, FileName):
        line_pragma_txt = self._SOURCE_REFERENCE_END().strip()

        new_content = []
        line_n      = 1 # NOT: 0!
        fh          = open_file_or_die(FileName)
        while 1 + 1 == 2:
            line = fh.readline()
            line_n += 1
            if not line: 
                break
            elif line.strip() != line_pragma_txt:
                new_content.append(line)
            else:
                line_n += 1
                new_content.append(self.LINE_PRAGMA(FileName, line_n))
        fh.close()
        write_safely_and_close(FileName, "".join(new_content))

    @typed(X=RouterContentElement, dial_db=DialDB)
    def position_and_goto(self, X, dial_db):
        """Generate code to (i) position the input pointer and
                            (ii) jump to terminal.
        """
        door_id = DoorID.incidence(X.acceptance_id, dial_db)
        dial_db.mark_address_as_gotoed(door_id.related_address)
        return [
           self.POSITIONING(X),
           self.GOTO(door_id, dial_db)
        ]

    def FRAME_IN_NAMESPACE_MAIN(self, Code):
        open_str  = self.NAMESPACE_OPEN(Setup.analyzer_name_space)
        close_str = self.NAMESPACE_CLOSE(Setup.analyzer_name_space)
        if open_str:  open_str = "%s\n" % open_str
        if close_str: close_str = "%s\n" % close_str
        return "".join([open_str, Code, close_str])

    def HELP_IF_CONFIGURATION_BY_CMAKE(self, SettingList):
        if not Setup.configuration_by_cmake_f: return ""
        txt = [
            "/*______________________________________________________________________________"
            "   Configuration by CMake."
            "   Template to be pasted into 'CMakeLists.txt'."
            ""
        ]
        txt.extend([
            "set(QUEX_%s_SETTING_%s_EXT %s)" % (Setup.analyzer_name_safe, name, value) 
            for name, value in SettingList 
        ])
        txt.extend([
            "",
            "configure_file(",
            '    "%s"' % Setup.output_configuration_file_cmake,
            '    "%s"' % Setup.output_configuration_file,
            ')',
            "______________________________________________________________________________*/"
        ])

        return "\n".join(txt)

    def ERROR_IF_DEFINED_AND_NOT_CONFIGURATION_BY_MACRO(self, ShortNameList):
        def ifdefined(Name, FirstF):
            condition_str = "defined(QUEX_<PURE>SETTING_%s_EXT) || defined(QUEX_%s_SETTING_%s_EXT)" % (Name, Setup.analyzer_name_safe, Name)
            if FirstF:
                return "#if    %s" %  condition_str
            else:
                return "   ||  %s" %  condition_str
            
        if Setup.configuration_by_macros_f:
            return ""
        else:
            return "\n".join([
                " \\\n".join(ifdefined(name, i==0) for i, name in enumerate(ShortNameList)),
                "#   error \"*_EXT macro detected but code not generated with '--config-by-macro'\"",
                "#endif"
            ])

    def QUEX_TYPE_DEF(self, Original, TypeName):
        type_name = "%s_%s" % (Setup.analyzer_class_name, TypeName)

        if Setup.configuration_by_cmake_f:
            original_type_str = "@QUEX_TYPE_%s_%s@" % (Setup.analyzer_name_safe, Original) 
        else:
            original_type_str = Original

        if Setup.configuration_by_macros_f:
            return "\n".join([
                "#ifdef QUEX_TYPE_%s_EXT" % TypeName,
                "   typedef QUEX_TYPE_%s_EXT %s;" % (TypeName, type_name),
                "#else",
                "   typedef %s %s;" % (original_type_str, type_name),
                "#endif",
            ])
        elif Setup.configuration_by_cmake_f:
            return "typedef @QUEX_TYPE_%s_%s@ %s;" % (Setup.analyzer_name_safe, Original, type_name) 
        else:
            return "typedef %s %s;" % (Original, type_name) 

    def QUEX_SETTING(self, Name):
        return "QUEX_%s_SETTING_%s" % (Setup.analyzer_name_safe, Name)

    def QUEX_SETTING_DEF(self, Name, Value):
        """If 'configuration_by_macros_f' is set, then setting parameters may
        be defined by according macros on the command line.
        """
        variable_name = self.QUEX_SETTING(Name)
        if Setup.configuration_by_cmake_f:
            value_str = "@QUEX_%s_SETTING_%s_EXT@" % (Setup.analyzer_name_safe, Name)
        else:
            value_str = "%s" % Value

        if Setup.configuration_by_macros_f:
            return "\n".join([
                "#if   defined(QUEX_<PURE>SETTING_%s_EXT)" % Name,
                "#   define %s QUEX_<PURE>SETTING_%s_EXT"  % (variable_name, Name),
                "#elif defined(QUEX_%s_SETTING_%s_EXT)"    % (Setup.analyzer_name_safe, Name),
                "#   define %s QUEX_%s_SETTING_%s_EXT"     % (variable_name, Setup.analyzer_name_safe, Name),
                "#else",
                "#   define %s %s"                         % (variable_name, value_str),
                "#endif",
            ])
        else:
            return "#define %s %s" % (variable_name, value_str)
                   
    def adapt_to_configuration(self, Txt):
        if not Txt: return Txt

        # Types
        if Setup.token_class_only_f: replacements = self.type_replacements(True)
        else:                        replacements = self.type_replacements()

        # Namespaces
        token_descr = token_db.token_type_definition
        _, stdlib_namespace = self.standard_lib_naming()
        replacements.extend([
            ("QUEX_NAMESPACE_MAIN_OPEN",   self.NAMESPACE_OPEN(Setup.analyzer_name_space)),
            ("QUEX_NAMESPACE_MAIN_CLOSE",  self.NAMESPACE_CLOSE(Setup.analyzer_name_space)),
            ("QUEX_NAMESPACE_QUEX_OPEN",   self.NAMESPACE_OPEN(Setup._quex_lib_name_space)),
            ("QUEX_NAMESPACE_QUEX_CLOSE",  self.NAMESPACE_CLOSE(Setup._quex_lib_name_space)),
            ("QUEX_NAMESPACE_QUEX_STDLIB_OPEN",  self.NAMESPACE_OPEN(stdlib_namespace)),
            ("QUEX_NAMESPACE_QUEX_STDLIB_CLOSE", self.NAMESPACE_CLOSE(stdlib_namespace)),
        ])
        if token_descr:
            replacements.extend([
                ("QUEX_NAMESPACE_TOKEN_OPEN",  self.NAMESPACE_OPEN(token_descr.class_name_space)),
                ("QUEX_NAMESPACE_TOKEN_CLOSE", self.NAMESPACE_CLOSE(token_descr.class_name_space))
            ])

        # Inline
        replacements.append(
            ("QUEX_INLINE", self.INLINE)
        )

        # TokenIds
        def tid(Name):
            return "%s%s" % (Setup.token_id_prefix, Name)

        replacements.extend([
            ("QUEX_SETTING_TOKEN_ID_UNINITIALIZED",  tid("UNINITIALIZED")),
            ("QUEX_SETTING_TOKEN_ID_TERMINATION",    tid("TERMINATION")),
            ("QUEX_SETTING_TOKEN_ID_INDENT",         tid("INDENT")),
            ("QUEX_SETTING_TOKEN_ID_DEDENT",         tid("DEDENT")),
            ("QUEX_SETTING_TOKEN_ID_NODENT",         tid("NODENT")),
        ])

        replacements.extend([
            ("QUEX_LEXEME_TERMINATING_ZERO_SET",  "QUEX_%s_LEXEME_TERMINATING_ZERO_SET" % Setup.analyzer_name_safe),
            ("QUEX_LEXEME_TERMINATING_ZERO_UNDO", "QUEX_%s_LEXEME_TERMINATING_ZERO_UNDO" % Setup.analyzer_name_safe),
        ])

        txt = blue_print(Txt, replacements)

        txt = self.replace_class_definitions(txt)

        txt = self.Match_QUEX_SETTING.sub(r"QUEX_%s_SETTING_\1" % Setup.analyzer_name_safe, txt)
        txt = self.Match_QUEX_PURE_SETTING.sub(r"QUEX_SETTING_\1", txt)
        # txt = self.Match_QUEX_OPTION.sub(r"%s_OPTION_\1" % Setup.analyzer_class_name, txt)

        # QUEX_BASE 
        txt = self.replace_base_reference(txt)

        # QUEX_TOKEN
        token_descr = token_db.token_type_definition
        if token_descr and token_db.support_repetition():
            member_name = token_descr.token_repetition_n_member_name.get_text()
            if not hasattr(token_descr, "get_member_db") or member_name not in token_descr.get_member_db():
                access = member_name
            else:
                access = token_descr.get_member_db()[member_name][1]
            txt = self.Match_QUEX_TOKEN_MEMBER_REPETITION_N.sub(access, txt)
            txt = self.Match_QUEX_TOKEN_ID_IS_REPEATABLE.sub(self.CHECK_TOKEN_ID_REPEATABLE(), txt)

        if token_descr:
            # Include guards of token files are named according to token class.
            txt = self.Match_QUEX_INCLUDE_GUARD_TOKEN.sub(r"QUEX_INCLUDE_GUARD_%s__TOKEN__\1" 
                                                          % token_descr.class_name_safe, txt)

        # QUEX_NAME
        txt = self.replace_naming(txt)

        # INCLUDE GUARDS_______________________________________________________
        txt = self.Match_QUEX_INCLUDE_GUARD_LEXEME_CONVERTER.sub(r"QUEX_INCLUDE_GUARD_%s__%s__\1"              
                                                                 % (Setup.analyzer_name_safe, Lng.SAFE_IDENTIFIER(Setup.buffer_encoding_name)),
                                                                 txt)
        # LIB_QUEX include guards are the same for all lexers
        txt = self.Match_QUEX_INCLUDE_GUARD_QUEX.sub(r"QUEX_INCLUDE_GUARD_LIB_QUEX__\1", txt)
        # Replace general include guard last.
        # (Cannot change previous include guards)
        txt = self.Match_QUEX_INCLUDE_GUARD.sub(r"QUEX_INCLUDE_GUARD_%s__\1"              
                                                % Setup.analyzer_name_safe, txt)
        return txt

    def replace_class_definitions(self, txt):
        txt = self.Match_QUEX_CLASS_BEGIN.sub(r"class \1 QUEX_<PURE>SETTING_USER_CLASS_DECLARATION_EPILOG_EXT : public \2 {\npublic:\n", txt)
        txt = self.Match_QUEX_CLASS_END.sub(r"};", txt)
        return txt

    def replace_base_reference(self, txt):
        return self.Match_QUEX_BASE.sub("(*me)", txt) 

    def CHECK_TOKEN_ID_REPEATABLE(self):
        if token_db.token_repetition_token_id_list == ("<<ALL>>",):
            return "(true)"
        elif token_db.token_repetition_token_id_list:
            return "(%s) " % " || ".join("(ID) == %s%s" % (Setup.token_id_prefix, token_id)
                                         for token_id in token_db.token_repetition_token_id_list)
        else:
            return "NULL == \"repeated token sending, but no token ids specified as '\\\\repeatable'\""

    def replace_naming(self, txt):
        def _replace(txt, local_re, global_re, Prefix, NameSpace):
            txt = local_re.sub(r"%s\1" % self.name_spaced_prefix(Prefix), txt) 
            txt = global_re.sub(r"%s\1" % self.name_spaced_prefix(Prefix, NameSpace), txt)
            return txt

        # StdLib Functions
        prefix, namespace = self.standard_lib_naming()
        txt = _replace(txt, self.Match_QUEX_STD, self.Match_QUEX_GSTD,
                       prefix, namespace)
        # Analyzer
        txt = _replace(txt, self.Match_QUEX_NAME, self.Match_QUEX_GNAME,
                       Setup.analyzer_class_name, Setup.analyzer_name_space)

        # Token
        token_descr = token_db.token_type_definition
        if token_descr:
            txt = _replace(txt, self.Match_QUEX_NAME_TOKEN, self.Match_QUEX_GNAME_TOKEN,
                           token_descr.class_name, token_descr.class_name_space)

        # QuexLib
        txt = _replace(txt, self.Match_QUEX_NAME_LIB, self.Match_QUEX_GNAME_LIB,
                       Setup._quex_lib_prefix, Setup._quex_lib_name_space)

        return txt

    def standard_lib_naming(self):
        if Setup.standard_library_usage_f and not Setup.standard_library_tiny_f:
            return self.DEFAULT_STD_LIB_NAMING
        else:
            return Setup._quex_lib_prefix, Setup._quex_lib_name_space

    def name_spaced_prefix(self, Prefix, NameSpace=None):
        if Prefix: prefix = "%s_" % Prefix
        else:      prefix = ""
        
        return self.NAME_IN_NAMESPACE(prefix, NameSpace)

    def type_replacements(self, DirectF=False):
        token_descr = token_db.token_type_definition
        if DirectF:
            type_memento         = "(void*)"
            type0_memento        = "(void*)"
            type_lexatom         = Setup.lexatom.type
            type_acceptance_id   = "int"
            type_indentation     = "int"
            if Setup.computed_gotos_f: type_goto_label  = "void*"
            else:                      type_goto_label  = "int32_t"
            if token_descr:
                type_token_id        = token_descr.token_id_type.get_text()
                type_token_line_n    = token_descr.line_number_type.get_text()
                type_token_column_n  = token_descr.column_number_type.get_text()
        else:
            def namespaced(Raw):
                return self.NAME_IN_NAMESPACE("%s_%s" % (Setup.analyzer_class_name, Raw), Setup.analyzer_name_space)
            type_memento         = namespaced("Memento")
            type0_memento        = "%s_Memento" % Setup.analyzer_class_name
            type_lexatom         = namespaced("lexatom_t")
            type_acceptance_id   = namespaced("acceptance_id_t")
            type_indentation     = namespaced("indentation_t")
            type_goto_label      = namespaced("goto_label_t")
            if token_descr:
                type_token_id        = namespaced("token_id_t")
                type_token_line_n    = namespaced("token_line_n_t")
                type_token_column_n  = namespaced("token_column_n_t")


        result = [
             ("QUEX_TYPE_ANALYZER",        self.NAME_IN_NAMESPACE(Setup.analyzer_class_name, Setup.analyzer_name_space)),
             ("QUEX_TYPE0_ANALYZER",       Setup.analyzer_class_name),
             ("QUEX_TYPE_MEMENTO",         type_memento),
             ("QUEX_TYPE0_MEMENTO",        type0_memento),
             ("QUEX_TYPE_LEXATOM",         type_lexatom),
             ("QUEX_TYPE_ACCEPTANCE_ID",   type_acceptance_id),
             ("QUEX_TYPE_INDENTATION",     type_indentation),
             ("QUEX_TYPE_GOTO_LABEL",      type_goto_label),
        ]

        if token_descr:
            result.extend([
               ("QUEX_TYPE_TOKEN",          self.NAME_IN_NAMESPACE(token_descr.class_name, token_descr.class_name_space)),
               ("QUEX_TYPE0_TOKEN",         token_descr.class_name),
               ("QUEX_TYPE_TOKEN_ID",       type_token_id),
               ("QUEX_TYPE_TOKEN_LINE_N",   type_token_line_n),
               ("QUEX_TYPE_TOKEN_COLUMN_N", type_token_column_n),
            ])
        return result

cpp_implementation_headers_txt = """
$$HEADER$$
$$INC: implementations.i$$

$$FOOTER$$
"""

cpp_reload_forward_str = """
    __quex_debug3("RELOAD_FORWARD: success->%i; failure->%i", 
                  (int)target_state_index, (int)target_state_else_index);
    __quex_assert(*(me->buffer._read_p) == QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER);
    
    __quex_debug_reload_before();                 
    /* Callbacks: 'on_buffer_before_change()' and 'on_buffer_overflow()'
     * are called during load process upon occurrence.                        */
    $$LOAD_RESULT$$ = $$BUFFER_LOAD_FW$$(&me->buffer, (QUEX_TYPE_LEXATOM**)position, PositionRegisterN);
    __quex_debug_reload_after($$LOAD_RESULT$$);

    switch( $$LOAD_RESULT$$ ) {
    case E_LoadResult_DONE: {
        /* FallbackN must be maintained at any cost!                          */
        __quex_assert(   ! me->buffer.input.lexatom_index_begin
                      || ! me->buffer._lexeme_start_p
                      ||   me->buffer._lexeme_start_p - me->buffer.content_begin(&me->buffer) >= me->buffer._fallback_n);
        __quex_assert(   ! me->buffer.input.lexatom_index_begin
                      || ! me->buffer._read_p
                      ||   me->buffer._read_p        - me->buffer.content_begin(&me->buffer) >= me->buffer._fallback_n);
        $$GOTO target_state_index$$      
    }
    case E_LoadResult_NO_MORE_DATA:   $$GOTO target_state_else_index$$ 
    case E_LoadResult_ENCODING_ERROR: goto $$ON_BAD_LEXATOM$$;
    case E_LoadResult_OVERFLOW:       QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_Buffer_Overflow_LexemeTooLong); FLUSH;
    default:                          __quex_assert(false);
    }
"""

cpp_reload_backward_str = """
    __quex_debug3("RELOAD_BACKWARD: success->%i; failure->%i", 
                  (int)target_state_index, (int)target_state_else_index);
    __quex_assert(input == QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER);

    __quex_debug_reload_before();                 
    /* Callbacks: 'on_buffer_before_change()' and 'on_buffer_overflow()'
     * are called during load process upon occurrence.                        */
    $$LOAD_RESULT$$ = $$BUFFER_LOAD_BW$$(&me->buffer);
    __quex_debug_reload_after($$LOAD_RESULT$$);

    switch( $$LOAD_RESULT$$ ) {
    case E_LoadResult_DONE:           $$GOTO target_state_index$$      
    case E_LoadResult_NO_MORE_DATA:   $$GOTO target_state_else_index$$ 
    case E_LoadResult_ENCODING_ERROR: goto $$ON_BAD_LEXATOM$$;
    case E_LoadResult_FAILURE:        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_OnLoadFailure); FLUSH; 
    default:                          __quex_assert(false);
    }
"""

cpp_header_definition_str = """
$$INC: buffer/Buffer$$
$$INC: token/TokenQueue$$

#ifdef    CONTINUE
#   undef CONTINUE
#endif
#define   CONTINUE do { goto $$CONTINUE_WITH_ON_AFTER_MATCH$$; } while(0)

#ifdef    FLUSH
#   undef FLUSH
#endif
#define   FLUSH   do { goto $$RETURN_WITH_ON_AFTER_MATCH$$; } while(0)
"""

cpp_lexeme_macro_setup = """
    /* Lexeme setup: 
     *
     * There is a temporary zero stored at the end of each lexeme, if the action 
     * references to the 'Lexeme'. 'LexemeNull' provides a reference to an empty
     * zero terminated string.                                                    */
#if defined(QUEX_OPTION_ASSERTS)
#   define Lexeme       QUEX_NAME(access_Lexeme)((const char*)__FILE__, (size_t)__LINE__, &me->buffer)
#   define LexemeBegin  QUEX_NAME(access_LexemeBegin)((const char*)__FILE__, (size_t)__LINE__, &me->buffer)
#   define LexemeL      QUEX_NAME(access_LexemeL)((const char*)__FILE__, (size_t)__LINE__, &me->buffer)
#   define LexemeEnd    QUEX_NAME(access_LexemeEnd)((const char*)__FILE__, (size_t)__LINE__, &me->buffer)
#else
#   define Lexeme       (me->buffer._lexeme_start_p)
#   define LexemeBegin  Lexeme
#   define LexemeL      $$LEXEME_LENGTH$$
#   define LexemeEnd    $$INPUT_P$$
#endif

#define LexemeNull      (&QUEX_NAME(LexemeNull))
"""

cpp_lexeme_macro_clean_up = """
#   undef Lexeme
#   undef LexemeBegin
#   undef LexemeEnd
#   undef LexemeNull
#   undef LexemeL
"""


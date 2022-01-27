# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
import quex.engine.misc.error                   as     error
from   quex.engine.misc.file_operations         import open_file_or_die
from   quex.engine.misc.file_in                 import EndOfStreamException, \
                                                       check, \
                                                       check_end_of_file, \
                                                       parse_identifier_assignment, \
                                                       read_identifier, \
                                                       read_integer, \
                                                       skip_whitespace
import quex.input.files.mode                    as     mode
import quex.input.files.section_define          as     section_define
import quex.input.files.section_token           as     section_token
import quex.input.files.token_type              as     token_type
import quex.input.files.code_fragment           as     code_fragment
from   quex.input.code.base                     import CodeFragment_NULL
from   quex.input.setup                         import NotificationDB
from   quex.output.token.id_generator           import token_id_db_enter, prepare_default_standard_token_ids
from   quex.input.code.base                     import SourceRef, SourceRef_VOID
from   quex.input.code.core                     import CodeUser
from   quex.blackboard                          import setup as Setup, Lng
import quex.blackboard                          as     blackboard
import quex.token_db                            as     token_db
from   quex.input.regular_expression.exception  import RegularExpressionException

def do(file_list):
    if not file_list and not (Setup.token_class_only_f or Setup.converter_only_f): 
        error.log("No input files.")

    mode_parsed_db = {} # mode name --> ModeParsed object
    #                      # later: ModeParsed is transformed into Mode objects.
    initial_mode      = CodeUser([], SourceRef_VOID)


    # If a foreign token-id file was presented even the standard token ids
    # must be defined there.
    if not Setup.extern_token_id_file:
        prepare_default_standard_token_ids()

    for file_name in file_list:
        error.insight("File '%s'" % file_name)
        fh = open_file_or_die(file_name, CodecCheckF=True, Encoding="utf-8-sig")

        # Read all modes until end of file
        try:
            while 1 + 1 == 2:
                parse_section(fh, mode_parsed_db, initial_mode)
        except EndOfStreamException:
            pass # ... next, please!
        except RegularExpressionException as x:
            error.log(x.message, fh)
        
    if token_db.token_type_definition is None:
        _parse_default_token_definition(mode_parsed_db)

    _token_consistency_check()

    return mode_parsed_db, initial_mode

def parse_section(fh, mode_parsed_db, initial_mode=None, CustomizedTokenTypeF=True):
    position = fh.tell()
    word     = ""
    try:
        skip_whitespace(fh)
        word = read_identifier(fh)
        if not word: 
            _check_stream_issues(fh)
        else:
            _parse_section(fh, position, word, mode_parsed_db, initial_mode, CustomizedTokenTypeF)

    except UnicodeDecodeError as x:
        if x.start == 0: extra_str = " (Probably wrong byte order mark)."
        else:            extra_str = "."
        error.log("Quex requires ASCII or UTF8 input character format.\n" \
                  "Found encoding error at position '%s'%s" % (x.start, extra_str), fh)

    except EndOfStreamException as x:
        fh.seek(position)
        if word: error.error_eof(word, fh)
        else:    raise x

def _parse_section(fh, position, section_name, mode_parsed_db, initial_mode, CustomizedTokenTypeF):
    """  -- 'mode { ... }'        => define a mode
         -- 'start = ...;'        => define the name of the initial mode
         -- 'header { ... }'      => define code that is to be pasted on top
                                     of the engine (e.g. "#include<...>")
         -- 'body { ... }'        => define code that is to be pasted in the class' body
                                     of the engine (e.g. "public: int  my_member;")
         -- 'constructor { ... }' => define code that is to be pasted in the class' constructor
                                     of the engine (e.g. "my_member = -1;")
         -- 'destructor { ... }'  => define code that is to be pasted in the class' destructor
                                     of the engine (e.g. "my_member = -1;")
         -- 'print { ... }'       => define code that is to be pasted in the class' print function.
                                     of the engine (e.g. "my_member = -1;")
         -- 'define { ... }'      => define patterns shorthands such as IDENTIFIER for [a-z]+
         -- 'token { ... }'       => define token ids
         -- 'token_type { ... }'  => define a customized token type
    """ 
    if _parse_code_fragment_sections(section_name, fh):
        return

    elif section_name == "start":
        _parse_start_mode_definition(fh, initial_mode)
        return

    elif section_name == "define":
        section_define.parse(fh)
        error.insight("Section '%s'" % section_name)
        return

    elif section_name == "token":       
        section_token.do(fh)
        return

    elif section_name == "token_type":       
        token_type.do(fh, mode_parsed_db, CustomizedTokenTypeF)
        return

    elif section_name == "mode":
        if Setup.token_class_only_f:
            error.log("Mode definition found in input files, while in token class\n"
                      "generation mode.", fh)
        # When the first mode is parsed, a token_type definition must be 
        # present. If not, the default token type definition is considered.
        if token_db.token_type_definition is None:
            _parse_default_token_definition(mode_parsed_db)

        mode.parse(fh, mode_parsed_db)
        return

    else:
        # This case should have been caught by the 'verify_word_in_list' function
        assert False

def _parse_default_token_definition(mode_parsed_db):
    sub_fh = Lng.open_template_fh(Lng.token_default_file())
    parse_section(sub_fh, mode_parsed_db, CustomizedTokenTypeF=False)
    sub_fh.close()
    token_type.command_line_settings_overwrite(CustomizedTokenTypeF=False)

def _parse_start_mode_definition(fh, initial_mode):
    mode_name = parse_identifier_assignment(fh)
    if mode_name == "":
        error.log("Missing mode_name after 'start ='", fh)

    elif not blackboard.initial_mode.sr.is_void():
        error.log("start mode defined more than once!", fh, DontExitF=True)
        error.log("previously defined here", blackboard.initial_mode.sr)
     
    initial_mode.set([mode_name], SourceRef.from_FileHandle(fh))

def _token_consistency_check():
    if not token_db.token_repetition_token_id_list: 
        return
    elif token_db.support_repetition():
        return

    hint = ""
    if Setup.extern_token_class_file:
        hint = " (possibly specify '--token-repetition-n-member-name')"
    error.log("Token with option '\\repeatable' defined, but current token class does not\n"
              "support implicit token repetition%s." % hint, token_db.token_repetition_source_reference_example)

def _parse_code_fragment_sections(section_name, fh):
    error.verify_word_in_list(section_name, blackboard.all_section_title_list, 
                              "Unknown quex section '%s'" % section_name, fh)

    if section_name in list(blackboard.fragment_db.keys()):
        element_name = blackboard.fragment_db[section_name]
        fragment     = code_fragment.parse(fh, section_name, AllowBriefTokenSenderF=False)        
        blackboard.__dict__[element_name] = fragment
        return True
    else:
        _notify_deprecated_sections(fh, section_name)
        return False

def _notify_deprecated_sections(fh, section_name):
    if section_name == "init":
        error.log("Section 'init' is no longer supported.\n"
                  "Keyword 'constructor' is provided instead.\n"
                  "Use 'destructor' to define destructor code.\n", fh)

    elif section_name == "repeated_token":
        error.log("Section 'repeated_token' is no longer supported.\n"
                  "specify '\\repeatable' after a token definition in section 'token' to\n"
                  "to allow implicit repetitions of its kind.\n"
                  "\n"
                  "EXAMPLE: token {\n"
                  "            TOKEN_A = 4711 \\repeatable;\n"
                  "            TOKEN_B        \\repeatable;\n"
                  "         }\n", fh)

def _check_stream_issues(fh):
    position = fh.tell()
    content  = fh.read()
    if content.count('\0') > 1:
        error.log("Quex requires ASCII or UTF8 input character format.\n" \
                  "File contains one or more '0' characters. Is it UTF16/UTF32 encoded?.", fh)
    fh.seek(position)

    if check_end_of_file(fh):
        raise EndOfStreamException()
    elif fh.tell() != 0:
        error.log("Missing section title", fh)


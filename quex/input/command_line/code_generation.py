# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.input.command_line.validation  as     validation
from   quex.input.setup                    import global_character_type_db,  \
                                                  command_line_args_defined, \
                                                  command_line_arg_position
from   quex.input.files.token_type         import setup_TokenTypeDescriptorManual
from   quex.input.files.token_id_file      import parse as token_id_file_parse
from   quex.output.languages.core          import db as output_language_db
from   quex.engine.misc.file_in            import read_namespaced_name
import quex.engine.misc.error              as     error 
from   quex.engine.misc.unistream          import UniStream

from   quex.blackboard import setup as Setup
from   quex.constants  import E_Compression

from   operator import itemgetter
import re


def prepare(command_line, argv):
    """RETURN:  True, if process needs to be started.
                False, if job is done.
    """

    # (*) Output programming language        
    Setup.language = Setup.language.upper()
    error.verify_word_in_list(Setup.language, list(output_language_db.keys()),
                              "Programming language '%s' is not supported." % Setup.language)
    Setup.language_db  = output_language_db[Setup.language]()

    # (*) Classes and their namespace
    __setup_analyzer_class(Setup)
    if Setup.extern_token_class_file: _setup_external_token_class_file()
    __setup_token_id_prefix(Setup)

    _line_and_column_counting_consistency(Setup)

    # Is the output file naming scheme provided by the extension database
    # (Validation must happen immediately)
    Setup.language_db.extension_db = Setup.language_db.all_extension_db.get(Setup.output_file_naming_scheme)
    if Setup.language_db.extension_db is None:
        error.log("File extension scheme '%s' is not provided for language '%s'.\n" \
                  % (Setup.output_file_naming_scheme, Setup.language) + \
                  "Available schemes are: %s." % repr(sorted(Setup.language_db.all_extension_db.keys()))[1:-1])

    if Setup.__buffer_lexatom_size_in_byte == "wchar_t":
        error.log("Since Quex version 0.53.5, 'wchar_t' can no longer be specified\n"
                  "with option '--buffer-element-size' or '-bes'. Please, specify\n"
                  "'--buffer-element-type wchar_t' or '--bet'.")

    Setup.buffer_setup(Setup.__buffer_lexatom_type,
                       Setup.__buffer_lexatom_size_in_byte,
                       Setup.buffer_encoding_name, 
                       Setup.buffer_encoding_file) 

    type_info = global_character_type_db.get(Setup.lexatom.type)
    if     type_info is not None and len(type_info) >= 4 \
       and type_info[3] != -1 and Setup.lexatom.size_in_byte != -1 \
       and type_info[3] != Setup.lexatom.size_in_byte:
        error.log("\nBuffer element type ('--bet' or '--buffer-element-type') was set to '%s'.\n" \
                  % Setup.lexatom.type \
                  + "It is well known to be of size %s[byte]. However, the buffer element size\n" \
                  % type_info[3] \
                  + "('-b' or '--buffer-element-type') was specified as '%s'.\n\n" \
                  % Setup.lexatom.size_in_byte \
                  + "Quex can continue, but the result is questionable.\n", \
                  DontExitF=True)

    if Setup.extern_token_id_specification: 
        if len(Setup.extern_token_id_specification) > 3: 
            error.log("Option '--foreign-token-id-file' received > 3 followers.\n"
                      "Found: %s" % str(Setup.extern_token_id_specification)[1:-1])
        if len(Setup.extern_token_id_specification) > 1:
            Setup.token_id_foreign_definition_file_region_begin_re = \
                    __compile_regular_expression(Setup.extern_token_id_specification[1], "token id region begin")
        if len(Setup.extern_token_id_specification) > 2:
            Setup.token_id_foreign_definition_file_region_end_re = \
                    __compile_regular_expression(Setup.extern_token_id_specification[2], "token id region end")
        Setup.extern_token_id_file = \
                Setup.extern_token_id_specification[0]

        token_id_file_parse(Setup.extern_token_id_file)

    # AFTER: Setup.extern_token_id_file !!!
    Setup.prepare_output_directory()
    if Setup.language not in ["DOT"]: Setup.prepare_all_file_names()

    # (*) Compression Types
    compression_type_list = []
    for name, ctype in [("compression_template_f",         E_Compression.TEMPLATE),
                        ("compression_template_uniform_f", E_Compression.TEMPLATE_UNIFORM),
                        ("compression_path_f",             E_Compression.PATH),
                        ("compression_path_uniform_f",     E_Compression.PATH_UNIFORM)]:
        if command_line_args_defined(command_line, name):
            compression_type_list.append((command_line_arg_position(name), ctype))

    compression_type_list.sort(key=itemgetter(0))
    Setup.compression_type_list = [x[1] for x in compression_type_list]

    validation.do(Setup, command_line, argv)

    # (*) return Setup ___________________________________________________________________
    return True

def __compile_regular_expression(Str, Name):
    tmp = Str.replace("*", "\\*")
    tmp = tmp.replace("?", "\\?")
    tmp = tmp.replace("{", "\\{")
    tmp = tmp.replace("}", "\\}")
    try:
        return re.compile(tmp)
    except:
        error.log("Invalid %s: %s" % (Name, Str))

def __setup_analyzer_class(Setup):
    """ X0::X1::X2::ClassName --> analyzer_class_name = ClassName
                                  analyzer_name_space = ["X0", "X1", "X2"]
        ClassName --> analyzer_class_name = ClassName
                      analyzer_name_space = []
    """
    # Default set here => able to detect seting on command line.
    if not Setup.analyzer_class: analyzer_class = "Lexer"
    else:                        analyzer_class = Setup.analyzer_class

    Setup.analyzer_class_name, \
    Setup.analyzer_name_space, \
    Setup.analyzer_name_safe   = \
         read_namespaced_name(analyzer_class, 
                              "analyzer class (options -o, --analyzer-class)",
                              NamespaceAllowedF=Setup.language not in ("C",))
    if Setup.show_name_spaces_f:
        print("FSM: {")
        print("     class_name:  %s;" % Setup.analyzer_class_name)
        print("     name_space:  %s;" % repr(Setup.analyzer_name_space)[1:-1])
        print("     name_prefix: %s;" % Setup.analyzer_name_safe)   
        print("}")

    Setup.analyzer_derived_class_name,       \
    Setup.analyzer_derived_class_name_space, \
    Setup.analyzer_derived_class_name_safe = \
         read_namespaced_name(Setup.analyzer_derived_class_name, 
                              "derived analyzer class (options --derived-class, --dc)",
                              AllowEmptyF=True,
                              NamespaceAllowedF=Setup.language not in ("C",))
    if not Setup.quex_lib:
        if Setup.language == "C": quex_lib = "quex"
        else:                     quex_lib = "quex::"

    Setup._quex_lib_prefix,     \
    Setup._quex_lib_name_space, \
    Setup._quex_lib_name_safe   = read_namespaced_name(quex_lib, 
                                        "Naming of Quex-Lib functions. (options --quex-lib, --ql)",
                                        AllowEmptyF=True,
                                        NamespaceAllowedF=Setup.language not in ("C",))
def _setup_external_token_class_file():
    if not Setup.token_class:
        error.log("When an external token class file is defined, the class name and name space\n"
                  "must be defined on the command line.\n"
                  "Use option '--token-class'.\n")
    elif not Setup.token_id_type:
        error.log("When an external token class file is defined, the token-id type\n"
                  "must be defined on the command line.\n"
                  "Use option '--token-id-type'.\n")

    setup_TokenTypeDescriptorManual()

def __setup_token_id_prefix(Setup):
    Setup.token_id_prefix_plain,        \
    Setup.token_id_prefix_name_space,   \
    dummy                             = \
         read_namespaced_name(UniStream(Setup.token_id_prefix, "<command line>"), 
                              "token prefix (options --token-id-prefix)", 
                              AllowEmptyF=True,
                              NamespaceAllowedF=Setup.language not in ("C",))
    if len(Setup.token_id_prefix_name_space) != 0 and Setup.language.upper() == "C":
         error.log("Token id prefix cannot contain a namespaces if '--language' is set to 'C'.")

def _line_and_column_counting_consistency(Setup):
    # (*) Line and Column number counting
    if Setup.__no_count_line_and_column_f:
        Setup.count_line_number_f   = False
        Setup.count_column_number_f = False

    if Setup.__no_token_class_support_token_stamp_f:
        Setup.token_class_support_token_stamp_line_n_f   = False  
        Setup.token_class_support_token_stamp_column_n_f = False 

    #   -- stamping of counts without counting is nonsense
    if not Setup.count_line_number_f:
        Setup.token_class_support_token_stamp_line_n_f   = False  
    if not Setup.count_column_number_f:
        Setup.token_class_support_token_stamp_column_n_f = False  


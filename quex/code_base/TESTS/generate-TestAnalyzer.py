# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import os
import sys

sys.path.insert(0, os.environ["QUEX_PATH"])

import quex.input.command_line.core              as command_line
import quex.input.files.mode                     as mode
import quex.input.files.core                     as quex_file_parser
from   quex.input.files.specifier.mode_db        import ModeDb_Builder
import quex.output.analyzer.core                 as analyzer_class
import quex.output.analyzer.adapt                as adapt
import quex.output.languages.cpp.templates       as templates
import quex.output.token.core     as token_class
# from   quex.TESTS.code.TEST.include_guard import better_name
import quex.core                        as core

from   quex.blackboard                  import Lng, \
                                               setup as Setup
import quex.blackboard                  as     blackboard
from   quex.input.code.base             import CodeFragment, CodeFragment_NULL, SourceRef_VOID

# re_include_guard = re.compile(r"__QUEX_INCLUDE_[A-Z_a-z0-9]*")
output_dir = None

Setup._debug_QUEX_TYPE_LEXATOM_EXT =True

blackboard.header = CodeFragment(
"""
extern bool UserConstructor_UnitTest_return_value;
extern bool UserReset_UnitTest_return_value;
extern bool UserMementoPack_UnitTest_return_value;
""")
blackboard.class_constructor_extension = CodeFragment("return UserConstructor_UnitTest_return_value;")
blackboard.reset_extension             = CodeFragment("return UserReset_UnitTest_return_value;")
blackboard.memento_pack_extension      = CodeFragment("return UserMementoPack_UnitTest_return_value;")

def code(Language):
    global output_dir
    global tail_str
    command_line.do(["-i", "nothing.qx", "-o", "TestAnalyzer", 
                     # "--token-repetition-n-member-name", "number",
                     "--odir", output_dir, "--language", Language,
                     "--debug-QUEX_TYPE_LEXATOM_EXT", 
                     "--config-by-macros"])
    mode_prep_prep_db, dummy = quex_file_parser.do(Setup.input_mode_files)
    mode_db = ModeDb_Builder.do(mode_prep_prep_db)

    blackboard.initial_mode = CodeFragment("M", SourceRef_VOID)


    core._generate(mode_db)

    return mode_db

def add_engine_stuff(mode_db, FileName, TokenClassImplementationF=False):

    global output_dir
    dummy, \
    member_function_signature_list = analyzer_class.do(mode_db, "")

    # FSM class implementation
    #
    analyzer_class_implementation  = "#ifndef QUEX_OPTION_UNIT_TEST_NO_IMPLEMENTATION_IN_HEADER_EXT\n"
    analyzer_class_implementation += analyzer_class.do_implementation(mode_db, 
                                                                      member_function_signature_list)
    analyzer_class_implementation += "\n"
    # analyzer_class_implementation += templates.get_implementation_header(Setup)
    analyzer_class_implementation += "\n"
    analyzer_class_implementation += "bool UserConstructor_UnitTest_return_value = true;\n"
    analyzer_class_implementation += "bool UserReset_UnitTest_return_value       = true;\n"
    analyzer_class_implementation += "bool UserMementoPack_UnitTest_return_value = true;\n"
    analyzer_class_implementation += "#endif /* QUEX_OPTION_UNIT_TEST_NO_IMPLEMENTATION_IN_HEADER_EXT */\n"

    with open(FileName, "a") as fh:
        fh.write("\n%s\n" % adapt.do(analyzer_class_implementation, output_dir))

    if not TokenClassImplementationF:
        return

    dummy,                     \
    token_class_implementation = token_class.do()

    with open(FileName, "a") as fh:
        fh.write("#ifndef QUEX_OPTION_UNIT_TEST_NO_IMPLEMENTATION_IN_HEADER_EXT\n")
        fh.write("%s\n" % adapt.do(token_class_implementation, output_dir))

        # fh.write("#else  /* QUEX_OPTION_UNIT_TEST_NO_IMPLEMENTATION_IN_HEADER_EXT */\n")
        # fh.write("bool UserConstructor_UnitTest_return_value = true;\n")
        # fh.write("bool UserReset_UnitTest_return_value       = true;\n")
        # fh.write("bool UserMementoPack_UnitTest_return_value = true;\n")
        fh.write("#endif /* QUEX_OPTION_UNIT_TEST_NO_IMPLEMENTATION_IN_HEADER_EXT */\n")

    Lng.straighten_open_line_pragmas(FileName)

def append_variable_definitions(FileName):
    global output_dir
    fh = open(FileName)
    content = fh.read()
    fh.close()
    fh = open(FileName, "w")
    fh.write("%s\n" % adapt.do(content, output_dir))
    fh.write("\n")
    fh.write("bool UserConstructor_UnitTest_return_value = true;\n")
    fh.write("bool UserReset_UnitTest_return_value       = true;\n")
    fh.write("bool UserMementoPack_UnitTest_return_value = true;\n")
    fh.close()

if "computed-gotos" in sys.argv:
    dir_suffix = "_cg"
    Setup.computed_gotos_f = True
else:
    dir_suffix = ""

if "emm" in sys.argv:
    dir_suffix += "_emm"
    Setup.memory_management_extern_f = True
else:
    Setup.memory_management_extern_f = False

if "C++" in sys.argv:
    output_dir = "test_cpp%s" % dir_suffix
    mode_db = code("C++")
    # os.system("cp test_cpp/TestAnalyzer Debug_TestAnalyzer")
    add_engine_stuff(mode_db, "%s/TestAnalyzer" % output_dir, TokenClassImplementationF=True)
    os.rename("%s/TestAnalyzer.cpp" % output_dir, 
              "%s/TestAnalyzer-dummy.cpp" % output_dir)
    append_variable_definitions("%s/TestAnalyzer-dummy.cpp" % output_dir)

elif "C" in sys.argv:
    output_dir = "test_c%s" % dir_suffix
    mode_db = code("C")
    add_engine_stuff(mode_db, "%s/TestAnalyzer.h" % output_dir,
                     TokenClassImplementationF=True)
    os.rename("%s/TestAnalyzer.c" % output_dir, 
              "%s/TestAnalyzer-dummy.c" % output_dir)
    append_variable_definitions("%s/TestAnalyzer-dummy.c" % output_dir)

else:
    print("pass 'C' or C++' as first command line argument")


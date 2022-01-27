# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#
# PURPOSE: Instantiate all or some of the code base directories/files.
#
# $1 = target directory.
# $* = directories to be instantiated from code base.
#
# '--adapt' adapts a given list of files to a specific include base.
# '--specify' adapts a given list of files to a specific include base.
#  
# $1 = target directory
# $* = file name list
#
# (C) Frank-Rene Schaefer
#______________________________________________________________________________
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "../../../")))

from   quex.input.code.core                     import CodeUser
from   quex.input.code.base                     import SourceRef

import quex.output.languages.cpp.source_package as     source_package
import quex.input.files.token_type              as     token_type
import quex.output.analyzer.adapt               as     adapt
from   quex.output.languages.core               import db
import quex.token_db                            as     token_db
from   quex.blackboard                          import setup as Setup, \
                                                       Lng
from   tempfile import NamedTemporaryFile


if "--lang-C" in sys.argv: 
    sys.argv.remove("--lang-C")
    Setup.language             = "C"
    Setup.language_db          = db["C"]()
    Setup._quex_lib_prefix     = "quex"
    Setup._quex_lib_name_space = []
    Setup._quex_lib_name_safe  = "quex"
else:                      
    Setup.language             = "C++"
    Setup.language_db          = db["C++"]()
    Setup._quex_lib_prefix     = ""
    Setup._quex_lib_name_space = ["quex"]
    Setup._quex_lib_name_safe  = "quex"

if "--tiny-stdlib" in sys.argv:
    sys.argv.remove("--tiny-stdlib")
    Setup.standard_library_tiny_f = True


Setup.analyzer_class_name     = "TestAnalyzer"

# Generate a temporary file containing a dumb token class where Quex will not
# complain about line and column numbers not being defined.
fh = NamedTemporaryFile("w")
fh.write("class Token { size_t line_n; size_t column_n; size_t number; };")
fh.seek(0)
Setup.extern_token_class_file = fh.name

token_db.support_take_text    = lambda : True
token_db.support_repetition   = lambda : True
token_db.support_token_stamp_line_n   = lambda : True
token_db.support_token_stamp_column_n = lambda : True

token_type.setup_TokenTypeDescriptorManual()
token_db.token_type_definition.token_repetition_n_member_name = CodeUser("repetition_n", SourceRef())
token_db.token_type_definition.class_name      = "TestAnalyzer_Token"
token_db.token_type_definition.class_name_safe = "TestAnalyzer_Token"
token_db.token_repetition_token_id_list        = ("<<ALL>>",)

if len(sys.argv) < 2:
    print("Error: require at least target directory.")
    sys.exit()

if "--adapt" in sys.argv or "-a" in sys.argv:
    target_dir      = sys.argv[2]
    input_file_list = sys.argv[3:]

    for input_file in input_file_list:
        with open(input_file) as fh:
            txt = fh.read()
        txt = adapt.produce_include_statements(target_dir, txt)
        with open(input_file, "w") as fh:
            fh.write(txt)

elif "--specify" in sys.argv:
    sys.argv.remove("--specify")
    Setup.analyzer_class_name = sys.argv[1]
    target_dir                = sys.argv[2]
    input_file_list           = sys.argv[3:]
    token_name                = "Token"
    for input_file in input_file_list:
        with open(input_file) as fh:
            txt = fh.read()

        txt = adapt.do(txt, target_dir)
        output_file = os.path.join(target_dir, os.path.basename(input_file))
        with open(output_file, "w") as fh:
            fh.write(txt)

else:
    target_dir    = sys.argv[1]
    code_dir_list = sys.argv[2:]
    if not code_dir_list: code_dir_list = None
    try:    os.mkdir(target_dir)
    except: print("Directory '%s' already exists." % target_dir)
    source_package.do(target_dir, code_dir_list)
fh.close()

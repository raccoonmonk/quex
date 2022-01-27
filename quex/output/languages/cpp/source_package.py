# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.file_operations import open_file_or_die, \
                                               write_safely_and_close 
from   quex.engine.misc.tools           import flatten
import quex.output.analyzer.adapt       as     adapt
from   quex.blackboard                  import Lng, setup as Setup
from   quex.DEFINITIONS                 import QUEX_PATH

import os

def do(OutputDir, DirList=None):
    file_set = __collect_files(DirList)
    __copy_files(OutputDir, file_set)

dir_db = {
    "": [
        "definitions",
        "include-guard-undef",
        "declarations",
        "implementations.i",
        "implementations-inline.i",
    ],
    "lexeme/": [
        "basics",
        "basics.i",
    ],
    "token/": [
        "receiving",
        "receiving.i",
        "TokenQueue",
        "TokenQueue.i",
        "CDefault.qx",
        "CppDefault.qx" 
    ],
    "extra/post_categorizer/": [
        "PostCategorizer",
        "PostCategorizer.i",
    ],
    "extra/accumulator/": [
        "Accumulator",
        "Accumulator.i",
    ],
    "buffer/lexatoms/": [
        "LexatomLoader", 
        "LexatomLoader.i",
        "LexatomLoader_navigation.i",
        "LexatomLoader_Plain",
        "LexatomLoader_Plain.i",
        "LexatomLoader_Converter",
        "LexatomLoader_Converter.i",
        "LexatomLoader_Converter_RawBuffer.i",
    ],
    "buffer/": [
        "asserts",
        "asserts.i",
        "Buffer",
        "Buffer_print",
        "Buffer_print.i",
        "Buffer.i",
        "BufferMemory.i",
        "Buffer_navigation.i",
        "Buffer_fill.i",
        "Buffer_move.i",
        "Buffer_load.i",
        "Buffer_nested.i",
        "Buffer_callbacks.i",
        "Buffer_invariance.i",
    ],
    "analyzer/": [
        "Mode",
        "Mode.i",
        "asserts",
        "asserts.i",
        "configuration/undefine",
        "configuration/validation",
        "Counter",
        "Counter.i",
        "struct/include-stack",
        "struct/include-stack.i",
        "struct/constructor",
        "struct/constructor.i",
        "struct/reset",
        "struct/reset.i",
        "struct/include-stack",
        "struct/include-stack.i",
        "member/misc",
        "member/misc.i",
        "member/mode-handling",
        "member/mode-handling.i",
        "member/navigation",
        "member/navigation.i",
        "adaptors/Feeder",
        "adaptors/Feeder.i",
        "adaptors/Gavager",
        "adaptors/Gavager.i",
        "Statistics",
        "Statistics.i"
    ],
    "quex/": [
        "asserts",
        "types.h",
        "debug_print", 
        "standard_functions", "enums", "operations",
        "bom",            "bom.i",  
        "StrangeStream",
        "MemoryManager",  "MemoryManager.i", "MemoryManager_UnitTest.i",
        "tiny_stdlib",    "tiny_stdlib.i"
    ],
    "quex/compatibility/": [
        "borland_stdint.h",
        "msc_stdint.h",
    ],
    "quex/byte_loader/": [
        "ByteLoader",         "ByteLoader.i",
        "ByteLoader_FILE",    "ByteLoader_FILE.i",
        "ByteLoader_POSIX",   "ByteLoader_POSIX.i",
        "ByteLoader_OSAL",    "ByteLoader_OSAL.i",
        "ByteLoader_stream",  "ByteLoader_stream.i",
        "ByteLoader_Memory",  "ByteLoader_Memory.i",
        "ByteLoader_Monitor", "ByteLoader_Monitor.i",
    ],
    "quex/converter/": [
        "Converter",               "Converter.i",
        "iconv/Converter_IConv",   "iconv/Converter_IConv.i",
        "icu/Converter_ICU",       "icu/Converter_ICU.i",
        "icu/special_headers.h",
        "iconv/special_headers.h",
    ],
    # "lexeme_converter/": [ ], DEPRECATED ...
}

def dir_db_get_files(Dir):
    global dir_db

    def condition(path):
        if Setup.standard_library_usage_f:
            if path.endswith("quex/tiny_stdlib"): return False
            if path.endswith("quex/tiny_stdlib.i"): return False
        return True

    if   not Dir: return []
    elif Dir[-1] != "/": Dir += "/"

    return [
        os.path.join(directory, path)
        for directory, file_list in dir_db.items() if directory.startswith(Dir)
        for path in file_list
        if condition(path)
    ]

def __collect_files(DirList):
    if DirList is None: dir_list = list(dir_db.keys()) 
    else:               dir_list = DirList

    if not Setup.implement_lib_quex_f:
        dir_list = [ d for d in dir_list if not d.startswith("quex/") ]
    if not Setup.implement_lib_lexeme_f:
        dir_list = [ d for d in dir_list if not d.startswith("lexeme/") ]

    result = set(flatten(
        dir_db_get_files(d) for d in dir_list
    ))

    if not Setup.token_class_only_f:
        result.update(dir_db[""])
    return result

def __copy_files(OutputDir, FileSet):
    include_db = [
        ("declarations",      "$$INCLUDE_TOKEN_CLASS_DEFINITION$$",     Lng.INCLUDE(Setup.output_token_class_file)),
        ("implementations.i", "$$INCLUDE_TOKEN_CLASS_IMPLEMENTATION$$", Lng.INCLUDE(Setup.output_token_class_file_implementation)),
        ("token/TokenQueue",  "$$INCLUDE_TOKEN_CLASS_DEFINITION$$",     Lng.INCLUDE(Setup.output_token_class_file)),
        ("token/TokenQueue",  "$$INCLUDE_LEXER_CLASS_DEFINITION$$",     Lng.INCLUDE(Setup.output_header_file))
    ]
    if Setup.language != "C++":
        include_db.append(
            ("implementations-inline.i", "$$INCLUDE_TOKEN_CLASS_IMPLEMENTATION$$", Lng.INCLUDE(Setup.output_token_class_file_implementation))
        )
    else:
        include_db.append(
            ("implementations-inline.i", "$$INCLUDE_TOKEN_CLASS_IMPLEMENTATION$$", "")
        )

    for path, dummy, dummy in include_db:
        directory, basename = os.path.split(path)
        assert (not directory and basename in dir_db[""]) \
               or (basename in dir_db["%s/" % directory])

    file_pair_list,   \
    out_directory_set = __get_source_drain_list(OutputDir, FileSet)

    # Make directories
    # Sort according to length => create parent directories before child.
    for directory in sorted(out_directory_set, key=len):
        if os.access(directory, os.F_OK) == True: continue
        os.makedirs(directory) # create parents, if necessary

    # Copy
    for source_file, drain_file in file_pair_list:
        content = open_file_or_die(source_file, "r").read()
        for path, origin, replacement in include_db:
            if not source_file.endswith(path): continue
            content = content.replace(origin, replacement)

        content = adapt.do(content, OutputDir, OriginalPath=source_file)
        write_safely_and_close(drain_file, content)

def __get_source_drain_list(OutputDir, FileSet):
    input_directory          = os.path.join(QUEX_PATH, Lng.CODE_BASE)
    output_directory         = os.path.join(OutputDir, "lib")

    file_pair_list = [ 
        (os.path.join(input_directory, source), 
         os.path.join(output_directory, source))
         for source in FileSet 
    ]
    out_directory_set = set(
        os.path.dirname(drain) for source, drain in file_pair_list
    )

    return file_pair_list, out_directory_set

# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
#
import quex.input.files.core                     as     quex_file_parser
import quex.input.files.mode                     as     mode
from   quex.input.code.core                      import CodeUser
#                                                
from   quex.engine.misc.tools                    import flatten
import quex.engine.misc.error                    as     error
from   quex.engine.misc.file_operations          import write_safely_and_close
from   quex.input.files.specifier.mode_db        import ModeDb_Builder
#
import quex.input.files.consistency_check        as     consistency_check
import quex.output.core.engine                   as     engine_generator
import quex.output.analyzer.core                 as     analyzer_class
import quex.output.analyzer.adapt                as     adapt
import quex.output.analyzer.configuration        as     configuration 
import quex.output.analyzer.lexeme_converter     as     lexeme_converter 
import quex.output.token.core                    as     token_class
import quex.output.token.id_generator            as     token_id_maker
import quex.output.analyzer.modes                as     mode_classes
import quex.output.languages.graphviz.core       as     grapviz_generator
import quex.output.languages.cpp.source_package  as     source_package

import quex.token_db   as     token_db
from   quex.blackboard import setup as Setup, \
                              Lng
import quex.blackboard as     blackboard
import quex.condition  as     condition

import os

def do():
    """Generates state machines for all modes. Each mode results into 
       a separate state machine that is stuck into a virtual function
       of a class derived from class 'quex_mode'.
    """
    if Setup.language == "DOT": 
        return do_plot()
    elif Setup.converter_only_f:
        mode_db = None
    elif Setup.token_class_only_f:
        mode_parsed_db, \
        user_defined_initial_mode = quex_file_parser.do(Setup.input_mode_files)
        assert not mode_parsed_db
        mode_db = None
    else:
        mode_db = _parse_modes_and_build(Setup.input_mode_files)

    condition.mode_db = mode_db # Announce!

    if not mode_db and not Setup.token_class_only_f and not Setup.converter_only_f:
        return
    else:
        _configure_output_directory()
        _generate(mode_db)
        _show_name_spaces()

def _parse_modes_and_build(InputFileList):
    mode_parsed_db, \
    user_defined_initial_mode = quex_file_parser.do(InputFileList)

    if not mode_parsed_db: 
        if not blackboard.dfa_command_executed_f: 
             error.log("Missing mode definition in input files.")
        return None
        
    initial_mode = _determine_initial_mode(mode_parsed_db, 
                                           user_defined_initial_mode) 
    consistency_check.initial_mode(mode_parsed_db.values(), initial_mode)
    blackboard.initial_mode = initial_mode

    mode_db = ModeDb_Builder.do(mode_parsed_db)

    return mode_db

def _configure_output_directory():
    if os.path.isfile(Setup.output_directory):
        error.log("The name '%s' is already a file and may not be used as output directory." 
                  % Setup.output_directory)
    elif os.path.isdir(Setup.output_directory):
        if os.access(Setup.output_directory, os.W_OK) == False:
            error.log("The directory '%s' is not writeable." 
                      % Setup.output_directory)
    elif Setup.output_directory:
        try:
            os.mkdir(Setup.output_directory)
        except:
            error.warning("Cannot create directory '%s'." % Setup.output_directory)
    else:
        return

def _generate(mode_db):
    if Setup.converter_only_f:
        content_table = lexeme_converter.do()
        do_converter_info(content_table[0][1], content_table[1][1])
        _write_all(content_table)
        source_package.do(Setup.output_directory, ["quex", "lexeme"])
        return

    content_table = _get_token_class()

    if Setup.token_class_only_f:
        if Setup.implement_lib_lexeme_f:
           content_table.extend(lexeme_converter.do())
        _write_all(content_table)
        if Setup.implement_lib_quex_f:
            source_package.do(Setup.output_directory, ["quex", "lexeme"])
        return

    else:
        content = token_id_maker.do(Setup)
        if content is not None:
            content_table.append((content, Setup.output_token_id_file_ref))
        content_table.extend(_get_analyzers(mode_db))
        content_table.extend(lexeme_converter.do()) # [Optional]
        _write_all(content_table)

        source_package.do(Setup.output_directory)
        return

def do_plot():
    mode_db = _parse_modes_and_build(Setup.input_mode_files)

    for m in mode_db.values():        
        plotter = grapviz_generator.Generator(m)
        plotter.do(Option=Setup.character_display)

def do_converter_info(HeaderFileName, SourceFileName):
    print("  Generate character and string converter functions")
    print()
    print("     from encoding: %s;" % Setup.buffer_encoding.name)
    print("          type:     %s;" % Setup.lexatom.type)
    print("     to:            utf8, utf16, utf32, 'char', and 'wchar_t'.")
    print()
    print("     header: %s" % HeaderFileName)
    print("     source: %s" % SourceFileName)
    print()

def do_token_class_info():
    token_descr      = token_db.token_type_definition
    token_class_name = Lng.NAME_IN_NAMESPACE(token_descr.class_name, token_descr.class_name_space) 
    info_list = [
        ## "  --token-id-prefix  %s" % Setup.token_id_prefix,
        "  --token-class-file %s" % Setup.output_token_class_file,
        "  --token-class      %s" % token_class_name,
        "  --lexatom-type     %s" % Setup.lexatom.type,
    ]
    if not token_descr.token_id_type.sr.is_void():
        info_list.append("  --token-id-type    %s" % token_descr.token_id_type.get_text())
    if not token_descr.line_number_type.sr.is_void():
        info_list.append("  --token-line-n-type    %s" % token_descr.line_number_type.get_text())
    if not token_descr.column_number_type.sr.is_void():
        info_list.append("  --token-column-n-type    %s" % token_descr.column_number_type.get_text())
    if not token_descr.token_repetition_n_member_name.sr.is_void():
        info_list.append("  --token-repetition-n-member-name %s" % token_descr.token_repetition_n_member_name.get_text())
    if token_db.support_take_text():
        info_list.append("  --token-class-support-take-text")
    if not token_db.support_token_stamp_line_n():
        info_list.append("  --no-token-stamp-line-count")
    if not token_db.support_token_stamp_column_n():
        info_list.append("  --no-token-stamp-column-count")

    print("info: Analyzers using this token class must be generated with")
    print("info:")
    for line in info_list:
        print("info:    %s" % line)
    print("info:")
    print("info: Header: \"%s\"" % token_db.token_type_definition.get_file_name()) 
    print("info: Source: \"%s\"" % Setup.output_token_class_file_implementation)

    comment = ["<<<QUEX-OPTIONS>>>\n"]
    for line in info_list:
        if line.find("--token-class-file") != -1: continue
        comment.append("%s\n" % line)
    comment.append("<<<QUEX-OPTIONS>>>")
    return Lng.ML_COMMENT("".join(comment), IndentN=0)

def _get_analyzers(mode_db): 

    configuration_header              = configuration.do(mode_db)

    analyzer_header, \
    member_function_signature_list    = analyzer_class.do(mode_db, Epilog="") 

    mode_implementation               = mode_classes.do(mode_db)
    function_analyzers_implementation = _analyzer_functions_get(mode_db)
    analyzer_implementation           = analyzer_class.do_implementation(mode_db, 
                                                                         member_function_signature_list) 

    engine_txt = "\n".join([Lng.ENGINE_TEXT_EPILOG(),
                            mode_implementation,
                            function_analyzers_implementation,
                            analyzer_implementation,
                            "\n"])

    if Setup.configuration_by_cmake_f:
        configuration_file_name = Setup.output_configuration_file_cmake
    else:
        configuration_file_name = Setup.output_configuration_file

    return [
        (configuration_header, configuration_file_name),
        (analyzer_header,      Setup.output_header_file),
        (engine_txt,           Setup.output_code_file),
    ]

def _analyzer_functions_get(ModeDB):
    mode_name_list = list(ModeDB.keys())  

    code = flatten( 
        engine_generator.do_with_counter(mode, mode_name_list) for mode in ModeDB.values() 
    )

    code.append(
        engine_generator.comment_match_behavior(iter(ModeDB.values()))
    )

    # generate frame for analyser code
    return Lng.FRAME_IN_NAMESPACE_MAIN("".join(code))

def _get_token_class():
    """RETURNS: [0] List of (source code, file-name)
                [1] Source code for global lexeme null declaration
    """
    class_token_header,        \
    class_token_implementation = token_class.do()

    if Setup.token_class_only_f:
        class_token_header = do_token_class_info() + class_token_header

    result = [
        (class_token_header,         token_db.token_type_definition.get_file_name()),
        (class_token_implementation, Setup.output_token_class_file_implementation),
    ]
    # Filter files that do not carry content
    return [ pair for pair in result if pair[0].strip() ]

def _write_all(content_table):

    content_table = [
        (adapt.do(x[0], Setup.output_directory), x[1]) for x in content_table
    ]
    content_table = [
        (Lng.straighten_open_line_pragmas_new(x[0], x[1]), x[1]) for x in content_table
    ]

    done = set()
    for content, file_name in content_table:
        assert file_name not in done
        done.add(file_name)
        if not content: continue
        write_safely_and_close(file_name, content)

def _show_name_spaces():
    if Setup.show_name_spaces_f:
        token_descr = token_db.token_type_definition
        if token_descr:
            print("Token: {")
            print("     class_name:  %s;" % token_descr.class_name)
            print("     name_space:  %s;" % repr(token_descr.class_name_space)[1:-1])
            print("     name_prefix: %s;" % token_descr.class_name_safe)   
            print("}")

def _determine_initial_mode(ModeDb, initial_mode_user_defined):
    assert not Setup.token_class_only_f
    assert not Setup.converter_only_f
    assert ModeDb

    implemented_mode_list = [m for m in ModeDb.values() if m.option_db.value("inheritable") != "only"]

    if not implemented_mode_list: 
        error.log("There is no mode that can be implemented---all existing modes are 'inheritable only'.\n" + \
                  "modes are = " + repr(mode_name_list)[1:-1],
                  Prefix="consistency check")

    if not initial_mode_user_defined.is_empty():
        return initial_mode_user_defined

    prototype = implemented_mode_list[0]
    if len(implemented_mode_list) > 1:
        error.log("No start mode defined via 'start' while more than one applicable mode exists.\n" + \
                  "Use for example 'start = %s;' in the quex source file to define an initial mode." \
                  % prototype.name)

    else:
        return CodeUser(prototype.name, SourceReference=prototype.sr)



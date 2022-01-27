# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
from   quex.engine.misc.string_handling import blue_print
import quex.output.analyzer.modes       as     mode_classes
from   quex.output.analyzer.adapt       import declare_member_functions
import quex.output.token.id_generator   as     token_id_maker

from   quex.DEFINITIONS import QUEX_PATH, \
                               QUEX_VERSION
import quex.token_db    as     token_db
import quex.blackboard  as     blackboard
from   quex.blackboard  import setup as Setup, \
                               Lng

def do(ModeDB, Epilog):
    assert not Epilog # If this never triggers, delete 'Epilog'
    assert token_db.token_type_definition is not None

    LexerClassName = Setup.analyzer_class_name

    # -- instances of mode classes as members of the lexer
    mode_object_members_txt,     \
    mode_specific_functions_txt, \
    friend_txt                   = mode_classes.get_related_code_fragments(ModeDB)

    # -- define a pointer that directly has the type of the derived class
    if Setup.analyzer_derived_class_name:
        analyzer_derived_class_name    = Setup.analyzer_derived_class_name
        derived_class_type_declaration = Lng.FORWARD_DECLARATION(Setup.analyzer_derived_class_name)
    else:
        analyzer_derived_class_name    = Setup.analyzer_class_name
        derived_class_type_declaration = ""

    token_class_file_name = token_db.token_type_definition.get_file_name()
    token_class_name      = token_db.token_type_definition.class_name
    token_class_name_safe = token_db.token_type_definition.class_name_safe

    template_code_txt     = Lng.open_template(Lng.analyzer_template_file())

    template_code_txt, \
    member_function_signature_list = declare_member_functions(template_code_txt)

    txt = blue_print(template_code_txt, [
        ["$$___SPACE___$$",                      " " * (len(LexerClassName) + 1)],
        ["$$CLASS_BODY_EXTENSION$$",             Lng.SOURCE_REFERENCED(blackboard.class_body_extension)],
        ["$$LEXER_CLASS_NAME$$",                 LexerClassName],
        ["$$LEXER_CLASS_NAME_SAFE$$",            Setup.analyzer_name_safe],
        ["$$LEXER_CONFIG_FILE$$",                Setup.output_configuration_file],
        ["$$LEXER_DERIVED_CLASS_DECL$$",         derived_class_type_declaration],
        ["$$LEXER_DERIVED_CLASS_NAME$$",         analyzer_derived_class_name],
        ["$$MEMENTO_EXTENSIONS$$",               Lng.SOURCE_REFERENCED(blackboard.memento_class_extension)],
        ["$$MODE_CLASS_FRIENDS$$",               friend_txt],
        ["$$MODE_OBJECTS$$",                     mode_object_members_txt],
        ["$$MODE_SPECIFIC_ANALYSER_FUNCTIONS$$", mode_specific_functions_txt],
        ["$$PRETTY_INDENTATION$$",               "     " + " " * (len(LexerClassName)*2 + 2)],
        ["$$QUEX_TEMPLATE_DIR$$",                QUEX_PATH + Lng.CODE_BASE],
        ["$$QUEX_VERSION$$",                     QUEX_VERSION],
        ["$$TOKEN_CLASS_DEFINITION_FILE$$",      token_class_file_name],
        ["$$TOKEN_CLASS$$",                      token_class_name],
        ["$$TOKEN_CLASS_NAME_SAFE$$",            token_class_name_safe],
        ["$$TOKEN_ID_DEFINITION_FILE$$",         Setup.output_token_id_file_ref],
        ["$$USER_DEFINED_HEADER$$",              Lng.SOURCE_REFERENCED(blackboard.header) + "\n"],
        ["$$USER_DEFINED_FOOTER$$",              Lng.SOURCE_REFERENCED(blackboard.footer) + "\n"],
        ["$$EPILOG$$",                           Epilog],
    ])

    return txt, member_function_signature_list

def do_implementation(ModeDB, MemberFunctionSignatureList):

    func_txt = Lng.open_template(Lng.analyzer_template_i_file())

    if ModeDB: 
        map_token_ids_to_names_str = token_id_maker.do_map_id_to_name_cases()
    else:                 
        map_token_ids_to_names_str = ""

    func_txt = blue_print(func_txt, [
        ["$$MEMBER_FUNCTION_ASSIGNMENT$$", Lng.MEMBER_FUNCTION_ASSIGNMENT(MemberFunctionSignatureList)],
        ["$$CONSTRUCTOR_EXTENSTION$$",     Lng.SOURCE_REFERENCED(blackboard.class_constructor_extension)],
        ["$$DESTRUCTOR_EXTENSTION$$",      Lng.SOURCE_REFERENCED(blackboard.class_destructor_extension)],
        ["$$USER_DEFINED_PRINT$$",         Lng.SOURCE_REFERENCED(blackboard.class_print_extension)],
        ["$$RESET_EXTENSIONS$$",           Lng.SOURCE_REFERENCED(blackboard.reset_extension)],
        ["$$MEMENTO_EXTENSIONS_PACK$$",    Lng.SOURCE_REFERENCED(blackboard.memento_pack_extension)],
        ["$$MEMENTO_EXTENSIONS_UNPACK$$",  Lng.SOURCE_REFERENCED(blackboard.memento_unpack_extension)],
        ["$$INCLUDE_TOKEN_ID_HEADER$$",    Lng.INCLUDE(Setup.output_token_id_file_ref)],
        ["$$MAP_ID_TO_NAME_CASES$$",       map_token_ids_to_names_str],
    ])

    return "\n%s\n" % func_txt


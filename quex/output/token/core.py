# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
from   quex.input.files.token_type       import TokenTypeDescriptor
from   quex.engine.misc.string_handling  import blue_print
import quex.token_db                     as     token_db
from   quex.blackboard                   import setup as Setup, Lng
import quex.condition                    as     condition

from   collections import OrderedDict

def do():
    """RETURNS: [0] Header text of the token class definition.
                [1] Implementation of the token class.
    """
    assert not Setup.converter_only_f
    assert token_db.token_type_definition is not None

    if token_db.token_type_definition.manually_written():
        # User has specified a manually written token class
        # (LexemeNull must be declared in global header)
        return "", ""
    else:
        # (LexemeNull is declared in token class header)
        return _do(token_db.token_type_definition)

def _do(Descr):
    txt, txt_i = _do_core(token_db.token_type_definition)

    if Setup.language.upper() == "C++":
        # C++: declaration and (inline) implementation in header.
        header_txt         = "\n".join([txt, txt_i])
        implementation_txt = ""
    else:
        # C: declaration in header, implementation in source file.
        header_txt         = txt
        implementation_txt = txt_i 

    if Setup.token_class_only_f:
        implementation_txt += implementation_extra_lib
        if not Setup.extern_token_class_file:
            implementation_txt += implementation_lexeme_null

    return header_txt, implementation_txt

def _do_core(Descr):
    # The following things must be ensured before the function is called
    assert Descr is not None
    assert isinstance(Descr, TokenTypeDescriptor)

    virtual_destructor_str,      \
    copy_str,                    \
    take_text_str                = _some_standard_stuff(Descr)

    # In case of plain 'C' the class name must incorporate the namespace (list)
    if Setup.language == "C": token_class_name = Descr.class_name_safe
    else:                     token_class_name = Descr.class_name
    assert token_class_name

    # ------------
    # TODO: Following should be always placed in front of footer/header:
    # ------------
    if Setup.token_class_only_f: 
        helper_definitions = helper_definitions_common
    elif Setup.output_configuration_file:                        
        helper_definitions = Lng.INCLUDE(Setup.output_configuration_file)
    else:
        helper_definitions = ""

    if not Setup.implement_lib_quex_f:
        quex_lib_dir = "lib/quex"
    else:
        quex_lib_dir = "%s/lib/quex" % Setup.output_directory

    template_str = Lng.open_template(Lng.token_template_file())
    txt = blue_print(template_str, [
        ["$$BODY$$",                    Lng.SOURCE_REFERENCED(Descr.body)],
        ["$$CONSTRUCTOR$$",             Lng.SOURCE_REFERENCED(Descr.constructor)],
        ["$$COPY$$",                    copy_str],
        ["$$DESTRUCTOR$$",              Lng.SOURCE_REFERENCED(Descr.destructor)],
        ["$$STANDARD_MEMBERS$$",        get_standard_members(Descr)],
        ["$$DISTINCT_MEMBERS$$",        get_distinct_members(Descr)],
        ["$$FOOTER$$",                  Lng.SOURCE_REFERENCED(Descr.footer)],
        ["$$FUNC_TAKE_TEXT$$",          take_text_str],
        ["$$HEADER$$",                  Lng.SOURCE_REFERENCED(Descr.header)],
        ["$$QUICK_SETTERS$$",           get_quick_setters(Descr)],
        ["$$SETTERS_GETTERS$$",         get_setter_getter(Descr)],
        ["$$UNION_MEMBERS$$",           get_union_members(Descr)],
        ["$$VIRTUAL_DESTRUCTOR$$",      virtual_destructor_str],
    ])

    template_i_str = Lng.open_template(Lng.token_template_i_file())
    txt_i = blue_print(template_i_str, [
        ["$$INCLUDE_TOKEN_CLASS_HEADER$$", Lng.INCLUDE(Setup.output_token_class_file)],
        ["$$CONSTRUCTOR$$",                Lng.SOURCE_REFERENCED(Descr.constructor)],
        ["$$COPY$$",                       copy_str],
        ["$$DESTRUCTOR$$",                 Lng.SOURCE_REFERENCED(Descr.destructor)],
        ["$$FOOTER$$",                     Lng.SOURCE_REFERENCED(Descr.footer)],
        ["$$FUNC_TAKE_TEXT$$",             take_text_str],
        ["$$TOKEN_CLASS_HEADER$$",         token_db.token_type_definition.get_file_name()],
    ])

    # Helper macros can only be expanded AFTER insertion of all regions.
    helper_macros = [
        ["$$HELPER_DEFINITIONS$$", helper_definitions],
        ["$$OUTPUT_DIR$$",         Setup.output_directory],
        ["$$QUEX_LIB_DIR$$",       quex_lib_dir],
        ["$$NAMESPACE_OPEN$$",     Lng.NAMESPACE_OPEN(Descr.class_name_space)],
        ["$$NAMESPACE_CLOSE$$",    Lng.NAMESPACE_CLOSE(Descr.class_name_space)],
        ["$$TOKEN_CLASS$$",        token_class_name],
    ]

    txt   = blue_print(txt, helper_macros)
    txt_i = blue_print(txt_i, helper_macros)

    if Setup.token_class_only_f:
        # All type definitions need to be replaced!
        replacements = Lng.type_replacements(DirectF=True)
        txt   = blue_print(txt, replacements)
        txt_i = blue_print(txt_i, replacements)

    return txt, txt_i

implementation_extra_lib = """
$$INC: <lib-lexeme>                 lexeme/basics.i$$
$$INC: <lib-lexeme>                 lexeme/converter-from-lexeme.i$$
$$INC: <lib-quex>                   quex/MemoryManager.i$$
$$INC: <lib-quex>                   quex/byte_loader/ByteLoader.i$$
$$INC: <lib-quex && std-lib>        quex/byte_loader/ByteLoader_FILE.i$$
$$INC: <lib-quex && std-lib && Cpp> quex/byte_loader/ByteLoader_stream.i$$
$$INC: <lib-quex>                   quex/bom.i$$
"""

implementation_lexeme_null = """
$$<lexeme-null>--------------------------------------------
QUEX_TYPE_LEXATOM QUEX_GNAME(LexemeNull) = (QUEX_TYPE_LEXATOM)0;
$$---------------------------------------------------------
"""

#______________________________________________________________________________
# [MEMBER PACKAGING]
#
# The 'distinct_db' and 'union_db' dictionaries are not to be sorted for
# iteration! The members need to be written in the sequence which is provided 
# by '.items()'.
# => The ordered dictionary lists them in the sequence as when they were 
#    defined. 
# => User is able to define 'packaging'.
#______________________________________________________________________________
def get_standard_members(Descr):
    TL = Descr.type_name_length_max()

    txt = []
    if Descr.token_contains_token_id_f:
        txt.append(Lng.CLASS_MEMBER_DEFINITION(Descr.token_id_type.get_text(), TL, "id"))
    if condition.do("count-column"):
        txt.append(Lng.CLASS_MEMBER_DEFINITION(Descr.column_number_type.get_text(), TL, "column_n"))
    if condition.do("count-line"):
        txt.append(Lng.CLASS_MEMBER_DEFINITION(Descr.line_number_type.get_text(), TL, "line_n"))
    return "".join(txt)

def get_distinct_members(Descr):
    TL = Descr.type_name_length_max()
    NL = Descr.variable_name_length_max()

    return "".join(
        __member(type_code, TL, name, NL)
        for name, type_code in list(Descr.distinct_db.items())      # No sort! [MEMBER PACKAGING]
    )

def get_union_members(Descr):
    TL = Descr.type_name_length_max()
    NL = Descr.variable_name_length_max()
    if not Descr.union_db: return ""
    
    txt = ["    union {\n"]
    for name, type_descr in list(Descr.union_db.items()):           # No sort! [MEMBER PACKAGING]
        if isinstance(type_descr, OrderedDict):
            txt.append("        struct {\n")
            txt.extend(
                __member(sub_type, TL, sub_name, NL, IndentationOffset=" " * 8)
                for sub_name, sub_type in list(type_descr.items())  # No sort! [MEMBER PACKAGING]
            )
            txt.append("\n        } %s;\n" % name)
        else:
            txt.append("%s\n" % __member(type_descr, TL, name, NL, IndentationOffset=" " * 4))
    txt.append("    } content;\n")
    #txt += Lng._SOURCE_REFERENCE_END()
    return "".join(txt)

def __member(TypeCode, MaxTypeNameL, VariableName, MaxVariableNameL, IndentationOffset=""):
    my_def  = Lng._SOURCE_REFERENCE_BEGIN(TypeCode.sr)
    my_def += IndentationOffset
    my_def += Lng.CLASS_MEMBER_DEFINITION(TypeCode.get_text(), MaxTypeNameL, 
                                          VariableName)
    my_def += Lng._SOURCE_REFERENCE_END(TypeCode.sr)
    return my_def

def get_setter_getter(Descr):
    """NOTE: All names are unique even in combined unions."""
    TL = Descr.type_name_length_max()
    NL = Descr.variable_name_length_max()
    variable_db = Descr.get_member_db()
    txt = ""
    for variable_name, info in sorted(variable_db.items()):
        type_code = info[0]
        access    = info[1]
        type_str  = type_code.get_text()
        txt += Lng._SOURCE_REFERENCE_BEGIN(type_code.sr)
        my_def = "    %s%s get_%s() const %s{ return %s; }" \
                 % (type_str,      " " * (TL - len(type_str)), 
                    variable_name, " " * ((NL + TL)- len(variable_name)), 
                    access)
        txt += my_def

        type_str = type_str.strip()
        type_str = type_str.replace("\t", " ")
        while type_str.find("  ") != -1:
            type_str = type_str.replace("  ", " ")
        if type_str not in ["char", "unsigned char", "singed char",
                            "short", "unsigned short", "singed short",
                            "int", "unsigned int", "singed int",
                            "long", "unsigned long", "singed long",
                            "float", "unsigned float", "singed float",
                            "double", "unsigned double", "singed double",
                            "uint8_t", "uint16_t", "uint32_t",
                            "int8_t", "int16_t", "int32_t",
                            "size_t", "uintptr_t", "ptrdiff_t"]:
            type_str += "&"

        txt += Lng._SOURCE_REFERENCE_BEGIN(type_code.sr)
        my_def = "    void%s set_%s(%s Value) %s{ %s = Value; }" \
               % (" " * (TL - len("void")), 
                  variable_name, type_str, " " * (NL + TL - (len(type_str) + len(variable_name))), 
                  access)
        txt += my_def

    txt += Lng._SOURCE_REFERENCE_END()
    return txt

def get_quick_setters(Descr):
    """NOTE: All names are unique even in combined unions."""
    variable_db         = Descr.get_member_db()
    used_signature_list = []

    def __quick_setter(ArgList, used_signature_list):
        """ArgList = [ [Name, Type], [Name, Type], ...]
         
           NOTE: There cannot be two signatures of the same type specification.
                 This is so, since functions are overloaded, have the same name
                 and only identify with their types.
        """
        signature = [x[1].get_text() for x in ArgList]
        if signature in used_signature_list:
            return []
        else:
            used_signature_list.append(signature)

        def _get_arg(info, i):
            name, type_info = info
            type_str = type_info.get_text()
            if type_str.find("const") != -1: type_str = type_str[5:]
            return "const %s& Value%i" % (type_str, i)

        def _get_assignment(info, i):
            name, type_info = info
            return "%s = Value%i; " % (variable_db[name][1], i)

        txt  = [
            "    void set(const QUEX_TYPE_TOKEN_ID ID, ",
            ", ".join(
                _get_arg(info, i) for i, info in enumerate(ArgList)
            ),
            ")\n    { ",
            "id = ID; "
        ]
        txt.extend(
            _get_assignment(info, i)
            for i, info in enumerate(ArgList)
        )
        txt.append("}\n")

        return txt

    def __combined_quick_setters(member_db, used_signature_list):
        member_list = list(member_db.items())
        if len(member_list) == 0: return []

        # sort the members with respect to their occurence in the token_type section
        member_list.sort(key=lambda x: x[1].sr.line_n)
        L        = len(member_list)
        # build the argument list consisting of a permutation of distinct members
        arg_list = [ member_list[i] for i in range(L) ]

        return __quick_setter(arg_list, used_signature_list)

    # (*) Quick setters for distinct members
    txt = __combined_quick_setters(Descr.distinct_db, used_signature_list)

    # (*) Quick setters for union members
    complete_f = True
    for name, type_info in sorted(Descr.union_db.items()):
        if isinstance(type_info, OrderedDict): 
            setter_txt = __combined_quick_setters(type_info, used_signature_list)
        else:                                  
            setter_txt = __quick_setter([[name, type_info]], used_signature_list)

        if not setter_txt: complete_f = False
        txt.extend(setter_txt)

    if not complete_f:
        txt.insert(0, "   /* Not all members are accessed via quick-setters (avoid overload errors). */")

    return "".join(txt)

helper_definitions_common = """
/* In cases, such as DLL compilation for some dedicated compilers, 
 * the classes need some epilog. If the user does not specify such
 * a thing, it must be empty.                                                */
#ifndef    QUEX_<PURE>SETTING_USER_CLASS_DECLARATION_EPILOG_EXT
#   define QUEX_<PURE>SETTING_USER_CLASS_DECLARATION_EPILOG_EXT
#endif

#ifdef QUEX_OPTION_ASSERTS
$$<Cpp> #   include <cassert>$$
$$<C>   #   include <assert.h>$$
#   define  __quex_assert(X)              assert(X)
#else
#   define  __quex_assert(X)              /* no assert */
#endif
"""

def _some_standard_stuff(Descr):
    """RETURNS: [0] virtual_destructor_str
                [1] body of the 'copy' function
                [2] body of the 'take_text' function
    """
    virtual_destructor_str = ""
    if Descr.open_for_derivation_f: 
        virtual_destructor_str = Lng.VIRTUAL_DESTRUCTOR_PREFIX

    if Descr.copy is None:
        # Default copy operation: Plain Copy of token memory
        copy_str = Lng.DEFAULT_TOKEN_COPY("__this", "__That")
    else:
        copy_str = Lng.SOURCE_REFERENCED(Descr.copy)

    if Descr.take_text is None:
        take_text_str = "%s\n" % Lng.RETURN_THIS(Lng.TRUE)
    else:
        take_text_str = Lng.SOURCE_REFERENCED(Descr.take_text)

    return virtual_destructor_str, \
           copy_str, \
           take_text_str



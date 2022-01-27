# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.output.languages.cpp.dictionary import Language as LanguageCpp
import quex.token_db                        as     token_db
from   quex.constants                       import E_Files
import quex.condition                       as     condition  
import quex.blackboard                      as     blackboard
from   quex.blackboard                      import setup as Setup

class Language(LanguageCpp):
    all_extension_db = {
        "": {
              E_Files.SOURCE:              ".c",
              E_Files.HEADER:              ".h",
              E_Files.HEADER_IMPLEMTATION: ".c",
        },
    }

    INLINE = "" # "static"
    DEFAULT_STD_LIB_NAMING =  ("", [""]) # (prefix, namespace)

    def __init__(self):      
        LanguageCpp.__init__(self)

    def NAMESPACE_REFERENCE(self, NameList, TrailingDelimiterF=True):
        return "" # C knows no namespaces
    def token_template_file(self):    return "%s/token/TXT-C"       % self.CODE_BASE
    def token_template_i_file(self):  return "%s/token/TXT-C.i"     % self.CODE_BASE
    def token_default_file(self):     return "%s/token/CDefault.qx" % self.CODE_BASE
    def analyzer_template_file(self): return "%s/analyzer/TXT-C"    % self.CODE_BASE

    def NAMESPACE_OPEN(self, NameList):  return ""
    def NAMESPACE_CLOSE(self, NameList): return ""

    def TOKEN_SET_MEMBER(self, Member, Value):
        return "self.token_p(&self)->%s = %s;" % (Member, Value)

    def TOKEN_SEND(self, TokenName):
        return "self.send(&self, %s);" % TokenName

    def TOKEN_SEND_TEXT(self, TokenName, Begin, End):
        return "self.send_text(&self, %s, %s, %s);" % (TokenName, Begin, End)

    def TOKEN_SEND_N(self, N, TokenName):
        return "self.send_n(&self, %s, (size_t)%s);\n" % (TokenName, N)

    def MEMBER_FUNCTION_DECLARATION(self, signature):
        if not condition.do(signature.condition):
            return ""
        argument_list_str = ", ".join("%s %s" % (arg_type, arg_name) 
                                      for arg_type, arg_name, default in signature.argument_list)

        if signature.constant_f: constant_str = "const "
        else:                    constant_str = ""
        if signature.argument_list: me_str = "%sQUEX_TYPE_ANALYZER* me, " % constant_str
        else:                       me_str = "%sQUEX_TYPE_ANALYZER* me" % constant_str

        return "%s (*%s)(%s%s);" % (signature.return_type, signature.function_name, 
                                    me_str, argument_list_str) 

    def MEMBER_FUNCTION_ASSIGNMENT(self, MemberFunctionSignatureList):
        txt = [
            "    me->%s = QUEX_NAME(MF_%s);" % (signature.function_name, signature.function_name)
            for signature in MemberFunctionSignatureList
            if condition.do(signature.condition)
        ]
        return "\n".join(txt)
        
    def RAISE_ERROR_FLAG(self, Name):
        return "self.error_code_set_if_first(&self, %s);\n" % Name

    def MODE_GOTO(self, Mode):
        return "self.enter_mode(&self, %s);" % Mode

    def MODE_GOSUB(self, Mode):
        return "self.push_mode(&self, %s);" % Mode

    def MODE_RETURN(self):
        return "self.pop_mode(&self);"

    def replace_base_reference(self, txt):
        return self.Match_QUEX_BASE.sub("(me->base)", txt) 

    def replace_class_definitions(self, txt):
        txt = self.Match_QUEX_CLASS_BEGIN.sub(
                r"typedef struct QUEX_<PURE>SETTING_USER_CLASS_DECLARATION_EPILOG_EXT {\n    QUEX_NAME_LIB(\2) base;\n", txt)
        txt = self.Match_QUEX_CLASS_END.sub(r"} QUEX_NAME_LIB(\1);", txt)
        return txt

    def type_replacements(self, DirectF=False):
        if DirectF:
            return LanguageCpp.type_replacements(self, True)

        acn = Setup.analyzer_class_name
        result = [
             ("QUEX_TYPE_ANALYZER",      "struct %s_tag" % self.NAME_IN_NAMESPACE(Setup.analyzer_class_name, Setup.analyzer_name_space)),
             ("QUEX_TYPE0_ANALYZER",     "struct %s_tag" % Setup.analyzer_class_name),
             ("QUEX_TYPE_MEMENTO",       "struct %s_tag" % self.NAME_IN_NAMESPACE("%s_Memento" % Setup.analyzer_class_name, Setup.analyzer_name_space)),
             ("QUEX_TYPE0_MEMENTO",      "struct %s_Memento_tag" % Setup.analyzer_class_name),
             ("QUEX_TYPE_LEXATOM",       "%s_lexatom_t" % acn),
             ("QUEX_TYPE_ACCEPTANCE_ID", "%s_acceptance_id_t" % acn),
             ("QUEX_TYPE_INDENTATION",   "%s_indentation_t" % acn),
             ("QUEX_TYPE_GOTO_LABEL",    "%s_goto_label_t" % acn)
        ]
        token_descr = token_db.token_type_definition
        if token_descr: 
            result.extend([
               ("QUEX_TYPE_TOKEN_ID",       "%s_token_id_t" % acn),
               ("QUEX_TYPE_TOKEN_LINE_N",   "%s_token_line_n_t" % acn),
               ("QUEX_TYPE_TOKEN_COLUMN_N", "%s_token_column_n_t" % acn),
               ("QUEX_TYPE_TOKEN",          "struct %s_tag" % self.NAME_IN_NAMESPACE(token_descr.class_name, token_descr.class_name_space)),
               ("QUEX_TYPE0_TOKEN",         "struct %s_tag" % token_descr.class_name),
            ])
        return result

    def FOOTER_IN_IMPLEMENTATION(self):
        return blackboard.Lng.SOURCE_REFERENCED(blackboard.footer)

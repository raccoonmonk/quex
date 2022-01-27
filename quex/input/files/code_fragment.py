# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.misc.error                     as     error
from   quex.engine.misc.file_in                   import EndOfStreamException, \
                                                         check, \
                                                         check_or_die, \
                                                         read_integer, \
                                                         read_namespaced_name, \
                                                         read_until_closing_bracket, \
                                                         skip_whitespace
from   quex.input.files.token_id_file             import cut_token_id_prefix
from   quex.blackboard                            import setup as Setup, \
                                                         Lng
from   quex.input.code.base                       import SourceRef
from   quex.input.setup                           import NotificationDB
import quex.input.regular_expression.snap_backslashed_character as snap_backslashed_character
from   quex.input.code.core                       import CodeUser 
from   quex.engine.codec_db.unicode.parser        import ucs_property_db
import quex.token_db                              as     token_db
from   quex.token_db                              import token_id_db_enter

import re
lexeme_re = re.compile(r"^Lexeme\b")

def parse(fh, CodeFragmentName, 
          ErrorOnFailureF=True, AllowBriefTokenSenderF=True):
    """RETURNS: An object of class CodeUser containing
                line number, filename, and the code fragment.

                None in case of failure.
    """
    assert type(ErrorOnFailureF)        == bool
    assert type(AllowBriefTokenSenderF) == bool

    skip_whitespace(fh)

    pos0 = fh.tell()
    first = fh.read(1)
    if first == "{":
        return __parse_normal(fh, CodeFragmentName)

    second = fh.read(1)
    if AllowBriefTokenSenderF and first + second == "=>":
        return __parse_brief_token_sender(fh)

    elif not ErrorOnFailureF:
        fh.seek(pos0)
        return None
    else:
        error.log("Missing code fragment after %s definition." % CodeFragmentName, fh)

def get_CodeUser_for_token_sending(fh, Identifier, Position, LexemeNullF, LexemeF):
    token_name = "%s%s" % (Setup.token_id_prefix_plain, Identifier)
    code_raw   = __create_token_sender_by_token_name(fh, token_name, 
                                                     LexemeNullOnlyF = LexemeNullF,
                                                     LexemeOnlyF     = LexemeF)
    return CodeUser(code_raw, SourceRef.from_FileHandle(fh, BeginPos=Position))

def __parse_normal(fh, code_fragment_name):
    position = fh.tell()
    code     = read_until_closing_bracket(fh, "{", "}")
    return CodeUser(code, SourceRef.from_FileHandle(fh, BeginPos=position))

def __read_token_identifier(fh):
    """Parses a token identifier that may contain a namespace specification.

       Returns "", if no valid specification could be found.
    """
    identifier,      \
    name_space_list, \
    dummy            = read_namespaced_name(fh, "token identifier",
                                            NamespaceAllowedF=Setup.language not in ("C",))
    if   not identifier:      return ""
    elif not name_space_list: return identifier
    return Lng.NAME_IN_NAMESPACE(identifier, name_space_list) 

def __parse_brief_token_sender(fh):
    # shorthand for { self.send(TKN_SOMETHING); FLUSH; }
    
    position = fh.tell()
    try: 
        skip_whitespace(fh)
        position = fh.tell()

        code = __parse_token_id_specification_by_character_code(fh)
        if code != -1: 
            code = __create_token_sender_by_character_code(fh, code)
        else:
            skip_whitespace(fh)
            identifier = __read_token_identifier(fh)
            skip_whitespace(fh)
            if identifier in ["GOTO", "GOSUB", "RETURN"]:
                code = __create_mode_transition_and_token_sender(fh, identifier)
            else:
                code = __create_token_sender_by_token_name(fh, identifier)
                check_or_die(fh, ";")

        if code: 
            # IMPORTANT: For handlers 'on_end_of_stream' and 'on_failure', 
            #            => CONTINUE would be desastrous!
            # -- When a termination token is sent, no other token shall follow. 
            #    Return MUST be enforced               => Do not allow CONTINUE!
            # -- When an 'on_failure' is detected allow immediate action of the
            #    receiver.                             => Do not allow CONTINUE!
            code += "\n%s\n" % Lng.PURE_RETURN # Immediate RETURN after token sending
            return CodeUser(code, SourceRef.from_FileHandle(fh, BeginPos=position))
        else:
            return None

    except EndOfStreamException:
        fh.seek(position)
        error.error_eof("token", fh)

def read_character_code(fh):
    # NOTE: This function is tested with the regression test for feature request 2251359.
    #       See directory $QUEX_PATH/TEST/2251359.
    pos = fh.tell()
    
    start = fh.read(1)
    if start == "":  
        fh.seek(pos); return -1

    elif start == "'": 
        # read an utf-8 char an get the token-id
        # Example: '+'
        if check(fh, "\\"):
            # snap_backslashed_character throws an exception if 'backslashed char' is nonsense.
            character_code = snap_backslashed_character.do(fh, ReducedSetOfBackslashedCharactersF=True)
        else:
            character_code = ord(fh.read(1))

        if character_code is None:
            error.log("Missing utf8-character for definition of character code by character.", 
                      fh)

        elif fh.read(1) != '\'':
            error.log("Missing closing ' for definition of character code by character.", 
                      fh)

        return character_code

    if start == "U":
        if fh.read(1) != "C": fh.seek(pos); return -1
        # read Unicode Name 
        # Example: UC MATHEMATICAL_MONOSPACE_DIGIT_FIVE
        skip_whitespace(fh)
        ucs_name = __read_token_identifier(fh)
        if ucs_name == "": fh.seek(pos); return -1
        # Get the character set related to the given name. Note, the size of the set
        # is supposed to be one.
        character_code = ucs_property_db.get_character_set("Name", ucs_name, Fh=fh)
        if type(character_code) in [str, str]:
            error.verify_word_in_list(ucs_name, ucs_property_db["Name"].code_point_db,
                                      "The string %s\ndoes not identify a known unicode character." % ucs_name, 
                                      fh)
        elif type(character_code) not in [int, int]:
            error.log("%s relates to more than one character in unicode database." % ucs_name, 
                      fh) 
        return character_code

    fh.seek(pos)
    character_code = read_integer(fh)
    if character_code is not None: return character_code

    # Try to interpret it as something else ...
    fh.seek(pos)
    return -1               

def __parse_function_argument_list(fh, ReferenceName):
    argument_list = []
    position = fh.tell()
    try:
        # Read argument list
        if check(fh, "(") == False:
            return []

        text = ""
        while 1 + 1 == 2:
            tmp = fh.read(1)
            if   tmp == ")": 
                break
            elif tmp in ["(", "[", "{"]:
                closing_bracket = {"(": ")", "[": "]", "{": "}"}[tmp]
                text += tmp + read_until_closing_bracket(fh, tmp, closing_bracket) + closing_bracket
            elif tmp == "\"":
                text += tmp + read_until_closing_bracket(fh, "", "\"", IgnoreRegions = []) + "\"" 
            elif tmp == "'":
                text += tmp + read_until_closing_bracket(fh, "", "'", IgnoreRegions = []) + "'" 
            elif tmp == ",":
                argument_list.append(text)
                text = ""
            elif tmp == "":
                fh.seek(position)
                error.error_eof("argument list for %s" % ReferenceName, fh)
            else:
                text += tmp

        if text != "": argument_list.append(text)

        argument_list = [arg.strip() for arg in argument_list]
        argument_list = [arg for arg in argument_list if arg != ""]
        return argument_list

    except EndOfStreamException:
        fh.seek(position)
        error.error_eof("token", fh)

def __parse_token_id_specification_by_character_code(fh):
    character_code = read_character_code(fh)
    if character_code == -1: return -1
    check_or_die(fh, ";")
    return character_code

def __create_token_sender_by_character_code(fh, CharacterCode):
    # The '--' will prevent the token name from being printed
    prefix_less_token_name = "UCS_0x%06X" % CharacterCode
    token_id_str           = "0x%06X" % CharacterCode 
    token_id_name          = "--%s" % prefix_less_token_name
    token_id_db_enter(fh, token_id_name, CharacterCode)
    return "%s\n" % Lng.TOKEN_SEND(token_id_str)

def token_id_db_verify_or_enter_token_id(fh, TokenName):
    global Setup

    prefix_less_TokenName = cut_token_id_prefix(TokenName, fh)

    # Occasionally add token id automatically to database
    if prefix_less_TokenName not in token_db.token_id_db:
        # DO NOT ENFORCE THE TOKEN ID TO BE DEFINED, BECAUSE WHEN THE TOKEN ID
        # IS DEFINED IN C-CODE, THE IDENTIFICATION IS NOT 100% SAFE.
        if TokenName in list(token_db.token_id_db.keys()):
            msg  = "Token id '%s' defined implicitly.\n" % TokenName
            msg += "'%s' has been defined in a token { ... } section!\n" % \
                   (Setup.token_id_prefix + TokenName)
            msg += "Token ids in the token { ... } section are automatically prefixed."
            error.warning(msg, fh, 
                          SuppressCode=NotificationDB.warning_usage_of_undefined_token_id_name)
        else:
            # Warning is posted later when all implicit tokens have been
            # collected. See "token_id_maker.__propose_implicit_token_definitions()"
            token_db.token_id_implicit_list.append((prefix_less_TokenName, 
                                                   SourceRef.from_FileHandle(fh)))

        # Enter the implicit token id definition in the database
        token_id_db_enter(fh, prefix_less_TokenName)

def __create_token_sender_by_token_name(fh, TokenName, LexemeNullOnlyF=False, LexemeOnlyF=False):
    assert type(TokenName) == str
    assert not(LexemeNullOnlyF and LexemeOnlyF)

    # Enter token_id into database, if it is not yet defined.
    token_id_db_verify_or_enter_token_id(fh, TokenName)

    # Parse the token argument list
    if LexemeNullOnlyF:
        argument_list = ["LexemeNull"]
    elif LexemeOnlyF:
        argument_list = ["Lexeme"]
    else:
        argument_list = __parse_function_argument_list(fh, TokenName)
    #if cut_token_id_prefix(TokenName, fh) == "TERMINATION" and not argument_list:
    #    argument_list.append("LexemeNull")

    # Create the token sender

    assert token_db.token_type_definition is not None, \
           "A valid token_type_definition must have been parsed at this point."

    explicit_member_names_f = any(arg.find("=") != -1 for arg in argument_list)
    if not explicit_member_names_f:
        return __token_sender_with_implicit_member_names(TokenName, argument_list, fh)
    elif Setup.extern_token_class_file:
        error.log("Member assignments in brief token senders are inadmissible\n" + \
                  "with manually written token classes. User provided file '%s'.\n" % Setup.extern_token_class_file,
                  fh)

    member_value_pairs = [ arg.split("=") for arg in argument_list ]
    member_value_pairs = [ (m.strip(), v.strip()) for m, v in member_value_pairs ]

    if any(not value for member, value in member_value_pairs):
        error.log("One explicit argument name mentioned requires all arguments to\n"  + \
                  "be mentioned explicitly.\n", fh)

    global lexeme_re
    if any(lexeme_re.search(value) is not None for member, value in member_value_pairs):
        error.log("Assignment of token member with 'Lexeme' directly being involved. The\n" + 
                  "'Lexeme' points into the text buffer and it is not owned by the token object.\n"
                  "\n"
                  "Proposals:\n\n"
                  "   (1) Use '(Lexeme)', i.e. surround 'Lexeme' by brackets to indicate\n"
                  "       that you are aware of the danger. Do this, if at the end of the\n"
                  "       process, the member can be assumed to relate to an object that\n"
                  "       is not directly dependent anymore on 'Lexeme'. This is particularly\n"
                  "       true if the member is of type 'std::string'. Its constructor\n"
                  "       creates a copy of the zero terminated string.\n\n"
                  "   (2) Use token senders without named arguments, for example\n"
                  "          \"%s(Lexeme+1, LexemeEnd-2)\"\n" % TokenName + 
                  "          \"%s(Lexeme)\"\n" % TokenName + 
                  "       These token senders create a copy of the lexeme and let the token\n"
                  "       own it.", fh)

    for member, value in member_value_pairs:
        error.verify_word_in_list(member, token_db.token_type_definition.get_member_db(), 
                                  "No member:   '%s' in token type description." % member, fh)

    txt = [
        Lng.TOKEN_SET_MEMBER(token_db.token_type_definition.get_member_access(member), 
                             value)
        for member, value in member_value_pairs
    ]

    # Box the token, stamp it with an id and 'send' it
    txt.append("%s\n" % Lng.TOKEN_SEND(TokenName))

    return "\n".join(txt)

def __token_sender_with_implicit_member_names(TokenName, argument_list, fh):
    # There are only three allowed cases for implicit token member names:
    #  QUEX_TKN_XYZ()           --> call take_text(Lexeme, LexemeEnd)
    #  QUEX_TKN_XYZ(Lexeme)     --> call take_text(Lexeme, LexemeEnd)
    #  QUEX_TKN_XYZ(Begin, End) --> call to take_text(Begin, End)
    L = len(argument_list)
    if L == 3:
        error.log("Since 0.49.1, there are only the following brief token senders that can take\n"
                  "unnamed token arguments:\n"
                  "     one argument:   'Lexeme'   =>  token.take_text(..., LexemeBegin, LexemeEnd);\n"
                  "     two arguments:  Begin, End =>  token.take_text(..., Begin, End);\n"
                  + "Found: " + repr(argument_list)[1:-1] + ".", fh)

    elif L == 2:
        send_str = Lng.TOKEN_SEND_TEXT(TokenName, argument_list[0], argument_list[1])

    elif L == 1:
        if argument_list[0] == "Lexeme":
            send_str = Lng.TOKEN_SEND_TEXT(TokenName, Lng.LEXEME_START_P(), Lng.INPUT_P())
        elif argument_list[0] == "LexemeNull":
            send_str = Lng.TOKEN_SEND_TEXT(TokenName, Lng.LEXEME_NULL(), Lng.LEXEME_NULL())
        else:
            error.log("If one unnamed argument is specified it must be 'Lexeme'\n"          + \
                      "or 'LexemeNull'. Found '%s'.\n" % argument_list[0]                     + \
                      "To cut parts of the lexeme, please, use the 2 argument sender, e.g.\n" + \
                      "QUEX_TKN_MY_ID(Lexeme + 1, LexemeEnd - 2);\n"                             + \
                      "Alternatively, use named parameters such as 'number=...'.", 
                      fh)

    else:
        send_str = Lng.TOKEN_SEND(TokenName)

    return send_str


def __create_mode_transition_and_token_sender(fh, Op):
    assert Op in ["GOTO", "GOSUB", "RETURN"]

    position     = fh.tell()
    target_mode  = ""
    token_sender = "" # Lng.RETURN
    if check(fh, "("):
        skip_whitespace(fh)
        if Op != "RETURN":
            target_mode = __read_token_identifier(fh)
            skip_whitespace(fh)

        if check(fh, ")"):
            token_sender = ""

        elif Op == "RETURN" or check(fh, ","):
            skip_whitespace(fh)
            token_name = __read_token_identifier(fh)
            skip_whitespace(fh)

            if check(fh, ","):
                error.log("Missing opening '(' after token name specification.\n" 
                          "Note, that since version 0.50.1 the syntax for token senders\n"
                          "inside brief mode transitions is like:\n\n"
                          "     => GOTO(MYMODE, QUEX_TKN_MINE(Argument0, Argument1, ...));\n", 
                          fh)

            token_sender = __create_token_sender_by_token_name(fh, token_name) 

            if check(fh, ")") == False:
                error.log("Missing closing ')' or ',' after '%s'." % Op, 
                          fh)

        else:
            fh.seek(position)
            error.log("Missing closing ')' or ',' after '%s'." % Op, fh)

    if check(fh, ";") == False:
        error.log("Missing ')' or ';' after '%s'." % Op, fh)

    if Op in ["GOTO", "GOSUB"] and target_mode == "": 
        error.log("Op %s requires at least one argument: The target mode." % Op, 
                  fh)

    # Code for mode change
    if   Op == "GOTO":  txt = Lng.MODE_GOTO(target_mode)
    elif Op == "GOSUB": txt = Lng.MODE_GOSUB(target_mode)
    else:               txt = Lng.MODE_RETURN()

    # Code for token sending
    txt += token_sender

    return txt


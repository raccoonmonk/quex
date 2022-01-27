# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
from   quex.input.setup                  import NotificationDB
from   quex.input.code.base              import SourceRef_VOID
from   quex.input.files.token_id_file    import space
import quex.engine.misc.error            as     error
import quex.engine.misc.similarity       as     similarity
from   quex.engine.misc.string_handling  import blue_print
from   quex.blackboard                   import setup as Setup, \
                                                Lng
import quex.blackboard                   as     blackboard
import quex.token_db                     as     token_db
from   quex.token_db                     import token_id_db_enter, \
                                                get_used_token_id_set

from   collections import defaultdict
import time

standard_token_id_list = ["TERMINATION", "UNINITIALIZED", "INDENT", "NODENT", "DEDENT"]

def do(setup):
    """________________________________________________________________________
       (1) Error Check 
       
       (2) Generates a file containing:
    
       -- token id definitions (if they are not done in '--foreign-token-id-file').

       -- const string& TokenClass::map_token_id_to_name(), i.e. a function which can 
          convert token ids into strings.
       ________________________________________________________________________
    """
    global file_str
    # At this point, assume that the token type has been generated.
    assert token_db.token_type_definition is not None

    # (1) Error Check
    #
    __warn_implicit_token_definitions()
    if not Setup.token_class_only_f:
        __error_on_no_specific_token_ids()

    if Setup.extern_token_id_file:
        __error_on_mandatory_token_id_missing()
        return None

    __autogenerate_token_id_numbers()
    __warn_on_double_definition()
    # If a mandatory token id is missing, this means that Quex did not
    # properly do implicit token definitions. Program error-abort.
    __error_on_mandatory_token_id_missing(AssertF=True)

    # (2) Generate token id file (if not specified outside)
    #
    token_id_txt = __get_token_id_definition_txt()

    return blue_print(file_str, [
        ["$$TOKEN_ID_DEFINITIONS$$", "".join(token_id_txt)],
        ["$$DATE$$",                 time.asctime()],
        ["$$TOKEN_PREFIX$$",         Setup.token_id_prefix], 
    ])

def do_map_id_to_name_cases():
    """Generate function which maps from token-id to string with the 
    name of the token id.
    """
    if not token_db.token_id_db: return ""
    L = max(len(name) for name in list(token_db.token_id_db.keys()))

    def get_case(token_name, token):
        if token_name.startswith("--"):
            # UCS codepoints are coded directly as pure numbers
            return "   case 0x%06X: return \"%s\";\n" % \
                   (token.number, token.name)
        else:
            return "   case %s%s:%s return \"%s\";\n" % \
                   (Setup.token_id_prefix, token_name, space(L, token_name), token_name)

    # -- define the function for token names
    switch_cases = [
        get_case(token_name, token)
        for token_name, token in sorted(token_db.token_id_db.items())
        if token_name not in standard_token_id_list
    ]

    txt = blue_print(map_id_to_name_cases,
                      [["$$TOKEN_ID_CASES$$", "".join(switch_cases)],
                       ["$$TOKEN_PREFIX$$",   Setup.token_id_prefix]]) 

    return txt

def prepare_default_standard_token_ids():
    """Prepare the standard token ids automatically. This shall only happen if
    the token ids are not taken from outside, i.e. from a token id file.

    The token ids given here are possibly overwritten later through a 'token'
    section.
    """
    global standard_token_id_list
    assert not Setup.extern_token_id_file

    # 'TERMINATION' is often expected to be zero. The user may still overwrite
    # it, if required differently.
    token_id_db_enter(None, "TERMINATION", NumericValue=0)

    for name in sorted(standard_token_id_list):
        if name == "TERMINATION": continue 
        token_id_db_enter(None, name, NumericValue=__get_free_token_id())

def __get_token_id_definition_txt():
    assert not Setup.extern_token_id_file

    def define_this(txt, token, L):
        tid_t = token_db.token_type_definition.token_id_type.get_text()
        assert token.number is not None
        if Setup.language == "C":
            txt.append("#define %s%s %s((%s)%i)\n" \
                       % (Setup.token_id_prefix_plain, token.name, space(L, token.name), 
                          tid_t, token.number))
        else:
            txt.append("const %s %s%s%s = ((%s)%i);\n" \
                       % (tid_t, Setup.token_id_prefix_plain, token.name, 
                          space(L, token.name), tid_t, token.number))

    if Setup.language == "C": 
        prolog = ""
        epilog = ""
    else:
        prolog = Lng.NAMESPACE_OPEN(Setup.token_id_prefix_name_space)
        epilog = Lng.NAMESPACE_CLOSE(Setup.token_id_prefix_name_space)

    # Considering 'items' allows to sort by name. The name is the 'key' in 
    # the dictionary 'token_id_db'.
    L      = max(list(map(len, iter(token_db.token_id_db.keys()))))
    result = [prolog]
    for dummy, token in sorted(token_db.token_id_db.items()):
        define_this(result, token, L)
    result.append(epilog)

    return result

file_str = \
"""/* -*- C++ -*- vim: set syntax=cpp:
 * PURPOSE: File containing definition of token-identifier and
 *          a function that maps token identifiers to a string
 *          name.
 *
 * NOTE: This file has been created automatically by Quex.
 *       Visit quex.org for further info.
 *
 * DATE: $$DATE$$
 *
 * (C) 2005-2010 Frank-Rene Schaefer
 * ABSOLUTELY NO WARRANTY                                                     */
#ifndef QUEX_INCLUDE_GUARD__GENERATED_TOKEN_IDS
#define QUEX_INCLUDE_GUARD__GENERATED_TOKEN_IDS

/* Note: When multiple lexical analyzers are included, then their
 *       token prefix must differ! Use '--token-id-prefix'.                   */
$$TOKEN_ID_DEFINITIONS$$

#endif /* QUEX_INCLUDE_GUARD__GENERATED_TOKEN_IDS */
"""

map_id_to_name_cases = \
"""
   case $$TOKEN_PREFIX$$TERMINATION:    return "<TERMINATION>";
   case $$TOKEN_PREFIX$$UNINITIALIZED:  return "<UNINITIALIZED>";
$$<indentation>----------------------------------------------------------------
   case $$TOKEN_PREFIX$$INDENT:         return "<INDENT>";
   case $$TOKEN_PREFIX$$DEDENT:         return "<DEDENT>";
   case $$TOKEN_PREFIX$$NODENT:         return "<NODENT>";
$$-----------------------------------------------------------------------------
$$TOKEN_ID_CASES$$
"""

def __autogenerate_token_id_numbers():
    # Automatically assign numeric token id to token id name
    for dummy, token in sorted(token_db.token_id_db.items()):
        if token.number is not None: continue
        token.number = __get_free_token_id()

def __get_free_token_id():
    used_token_id_set = get_used_token_id_set()
    candidate = Setup.token_id_counter_offset
    while candidate in used_token_id_set:
        candidate += 1
    return candidate

def has_specific_token_ids():
    """RETURNS: True, if there are token ids other than the standard
                      ones like 'TERMINATION', 'UNINITIALIZED', etc.
                False, else.
    """
    all_token_id_set = set(token_db.token_id_db.keys())
    all_token_id_set.difference_update(standard_token_id_list)
    if all_token_id_set: return True
    else:                return False

def __warn_on_double_definition():
    """Double check that no token id appears twice. Again, this can only happen,
    if quex itself produced the numeric values for the token.

    If the token ids come from outside, Quex does not know the numeric value. It 
    cannot warn about double definitions.
    """
    assert not Setup.extern_token_id_file

    if NotificationDB.message_on_extra_options in blackboard.setup.suppressed_notification_list:
        return

    clash_db = defaultdict(list)

    token_list = list(token_db.token_id_db.values())
    for i, x in enumerate(token_list):
        for y in token_list[i+1:]:
            if x.number != y.number: continue
            clash_db[x.number].append(x)
            clash_db[x.number].append(y)

    if not clash_db: return

    sr        = None
    item_list = list(clash_db.items())
    item_list.sort()
    for x, token_id_list in item_list:
        done = set()
        new_token_id_list = []
        for token_id in token_id_list:
            if token_id.name in done: continue
            done.add(token_id.name)
            new_token_id_list.append(token_id)

        subitem_list = sorted([ 
            (token_id.name, token_id.sr) 
            for token_id in new_token_id_list 
        ])
        if not subitem_list: continue

        dummy, sr = subitem_list[0]
        if sr is None: sr = SourceRef_VOID
        error.warning("Token ids with same numeric value %i found:" % x, sr) 
        for name, sr in subitem_list:
            if sr is None: sr = SourceRef_VOID
            error.warning("  %s" % name, sr)

    if sr is not None:
        error.warning("", sr, SuppressCode=NotificationDB.warning_on_duplicate_token_id)
                      
def __warn_implicit_token_definitions():
    """Output a message on token_ids which have been generated automatically.
    That means, that the user may have made a typo.
    """
    if not token_db.token_id_implicit_list: 
        return

    def warn(TokenName, ExistingList, PrefixAddF=False):
        similar_i = similarity.get(TokenName, ExistingList)
        if similar_i == -1: 
            similar_str = ""
        else:
            similar_str = " /* did you mean '%s%s'? */" \
                          % (Setup.token_id_prefix, ExistingList[similar_i])
        if PrefixAddF: prefix = Setup.token_id_prefix
        else:          prefix = ""
        error.warning("     %s%s;%s" % (prefix, TokenName, similar_str), sr)

    sr            = token_db.token_id_implicit_list[0][1]
    msg           = "Detected implicit token identifier definitions."
    implicit_list = [
        tid[0] for tid in token_db.token_id_implicit_list
    ]
    defined_list = [
        tid.name for tid in list(token_db.token_id_db.values())
        if tid.name not in implicit_list
    ]

    if not Setup.extern_token_id_file:
        msg += " Proposal:\n"
        msg += "   token {"
        error.warning(msg, sr)
        for token_name, sr in token_db.token_id_implicit_list:
            warn(token_name, defined_list)
        error.warning("   }", sr)
    else:
        error.warning(msg, sr)
        for token_name, sr in token_db.token_id_implicit_list:
            warn(token_name, defined_list, PrefixAddF=True)
        error.warning("Above token ids must be defined in '%s'" \
                      % Setup.extern_token_id_file, sr)

def __error_on_no_specific_token_ids():
    if has_specific_token_ids(): return

    token_id_str = [
        "    %s%s\n" % (Setup.token_id_prefix, name)
        for name in sorted(token_db.token_id_db.keys())
    ]

    error.log("No token id beyond the standard token ids are defined. Found:\n" \
              + "".join(token_id_str) \
              + "Refused to proceed.") 

def __error_on_mandatory_token_id_missing(AssertF=False):
    def check(AssertF, TokenID_Name):
        if AssertF:
            assert TokenID_Name in token_db.token_id_db
        elif TokenID_Name not in token_db.token_id_db:
            error.log("Definition of token id '%s' is mandatory!" % (Setup.token_id_prefix + TokenID_Name))

    check(AssertF, "TERMINATION")
    check(AssertF, "UNINITIALIZED")
    if blackboard.required_support_indentation_count():
        check(AssertF, "INDENT")
        check(AssertF, "DEDENT")
        check(AssertF, "NODENT")


import quex.engine.misc.error                   as     error
from   quex.engine.misc.file_in                 import \
                                                       check, \
                                                       \
                                                       \
                                                       read_identifier, \
                                                       read_integer, \
                                                       skip_whitespace
import quex.input.files.token_type              as     token_type
from   quex.input.setup                         import NotificationDB
from   quex.output.token.id_generator           import token_id_db_enter
from   quex.input.code.base                     import SourceRef
from   quex.blackboard                          import setup as Setup, Lng
import quex.token_db                            as     token_db

def do(fh, NamesOnlyF=False):
    """NamesOnlyF == True: Allow only definition of names, no numeric values 
                           may be assigned to it.

       'NamesOnlyF' indicates that data is not written to the global 
       'token_id_db'. Then only a list of names is returned.
    """
    # NOTE: Catching of EOF happens in caller: parse_section(...)
    #
    prefix       = Setup.token_id_prefix
    prefix_plain = Setup.token_id_prefix_plain # i.e. without name space included
    def _check_suspicious_prefix(candidate, fh):
        suspicious_prefix = None
        if prefix and candidate.startswith(prefix):       
            suspicious_prefix = prefix
        elif prefix_plain and candidate.startswith(prefix_plain): 
            suspicious_prefix = prefix_plain
        if suspicious_prefix is None: return
        error.warning("Token identifier '%s' starts with token prefix '%s'.\n" \
                  % (candidate, suspicious_prefix) \
                  + "Token prefix is mounted automatically. This token id appears in the source\n" \
                  + "code as '%s%s'." \
                  % (prefix, candidate), \
                  fh, 
                  SuppressCode=NotificationDB.warning_token_id_prefix_appears_in_token_id_name)

    if NamesOnlyF: 
        result = set()

    skip_whitespace(fh)
    if not check(fh, "{"):
        error.log("Missing opening '{' for after 'token' section identifier.", 
                  fh)

    while check(fh, "}") == False:
        skip_whitespace(fh)

        candidate = read_identifier(fh, TolerantF=True, OnMissingStr="Missing valid token identifier.")

        _check_suspicious_prefix(candidate, fh)

        skip_whitespace(fh)

        if NamesOnlyF:
            result.add(prefix + candidate)
            if check(fh, ";") == False:
                error.log("Missing ';' after token identifier '%s'.\n" \
                          % candidate, fh)
            continue

        # Parse a possible numeric value after '='
        numeric_value = None
        if check(fh, "="):
            skip_whitespace(fh)
            numeric_value = read_integer(fh)
            if numeric_value is None:
                error.log("Missing number after '=' for token identifier '%s'." % candidate, 
                          fh)

        repeatable_f = False
        if check(fh, "\\"):
            option_name = read_identifier(fh, TolerantF=True, OnMissingStr="Missing 'option name' after '\\'.")
            if option_name != "repeatable":
                error.log("The option allowed in token definitions is '\\repeatable'; found '%s'.\n" % option_name, fh)
            repeatable_f = True

        if check(fh, ";") == False:
            error.log("Missing ';' after token identifier '%s'." % candidate, 
                      fh)

        if Setup.extern_token_id_file and (not repeatable_f or numeric_value):
            error.log("Section 'token' while token id file '%s' has also been specified.\n" \
                      % Setup.extern_token_id_file \
                      + "In that case, the only thing to be specified for a token-id in 'token'\n"
                      + "is '\\repeatable', i.e. that it is admissible to repeat it.", fh)

        if not NamesOnlyF:
            token_id_db_enter(fh, candidate, numeric_value) 

        if repeatable_f:
            token_db.token_repetition_token_id_list.append(candidate)
            if token_db.token_repetition_source_reference_example is None:
                token_db.token_repetition_source_reference_example = SourceRef.from_FileHandle(fh)

    if NamesOnlyF:
        return sorted(list(result))
    else:
        return # Changes are applied to 'token_db.token_id_db'


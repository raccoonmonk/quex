# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
from   quex.DEFINITIONS                   import QUEX_CODEC_DB_PATH
import quex.engine.codec_db.parser        as     parser
import quex.engine.misc.error             as     error
from   quex.engine.misc.tools             import flatten
from   quex.engine.misc.file_operations   import get_file_content_or_die, \
                                                 open_file_or_die

from   copy import copy
import os


_supported_codec_list              = []
_supported_codec_list_plus_aliases = []

def get_supported_codec_list(IncludeAliasesF=False):
    global _supported_codec_list
    global _supported_codec_list_plus_aliases
    assert type(IncludeAliasesF) == bool

    if not _supported_codec_list: 
        # Determine: _supported_codec_list
        content = get_file_content_or_die("%s/00-SUPPORTED.txt" % QUEX_CODEC_DB_PATH)
        _supported_codec_list = sorted(content.split())

        # Determine: _supported_codec_list_plus_aliases
        codec_db_list = parser.get_codec_list_db()
        aliases = flatten(
            aliases_list for codec_name, aliases_list, dummy in codec_db_list
            if codec_name in _supported_codec_list
        )
        aliases = [alias for alias in aliases if alias]
        _supported_codec_list_plus_aliases = sorted(_supported_codec_list + aliases)

    if IncludeAliasesF: return _supported_codec_list_plus_aliases
    else:               return _supported_codec_list

def get_complete_supported_codec_list():
    return get_supported_codec_list(IncludeAliasesF=True) + ["utf8", "utf16", "utf32"]

def get_supported_language_list(CodecName=None):
    if CodecName is None:
        result = []
        for record in parser.get_codec_list_db():
            for language in record[2]:
                if language not in result: 
                    result.append(language)
        result.sort()
        return result
    else:
        for record in parser.get_codec_list_db():
            if record[0] == CodecName: return record[2]
        return []

def get_codecs_for_language(Language):
    result = []
    for record in parser.get_codec_list_db():
        codec = record[0]
        if codec not in get_supported_codec_list(): continue
        if Language in record[2]: 
            result.append(record[0])
    if len(result) == 0:
        error.verify_word_in_list(Language, get_supported_language_list(),
                                  "No codec found for language '%s'." % Language)
    return result

def get_supported_unicode_character_set(CodecAlias=None, FileName=None):
    """RETURNS:

       NumberSet of unicode characters which are represented in codec.
       None, if an error occurred.

       NOTE: '.source_set' is None in case an error occurred while constructing
             the EncodingTrafoByTable.
    """
    if FileName: file_name = FileName
    else:        codec_name, file_name = get_file_name_for_codec_alias(CodecAlias)

    source_set, drain_set = load([], file_name, ExitOnErrorF=False)
    return source_set

def load(result_list, FileName, ExitOnErrorF):
    fh = open_file_or_die(FileName, "r")
    source_set, drain_set, error_str = parser.do(result_list, fh)

    if error_str is not None:
        error.log(error_str, fh, DontExitF=not ExitOnErrorF)
        return None, None

    return source_set, drain_set

def get_file_name_for_codec_alias(CodecAlias):
    """Arguments FH and LineN correspond to the arguments of error.log."""
    assert CodecAlias

    for record in parser.get_codec_list_db():
        if CodecAlias in record[1] or CodecAlias == record[0]: 
            codec_name = record[0]
            return codec_name, os.path.join(QUEX_CODEC_DB_PATH, "%s.dat" % codec_name)

    error.verify_word_in_list(CodecAlias, get_supported_codec_list(), 
                        "Character encoding '%s' unknown to current version of quex." % CodecAlias)



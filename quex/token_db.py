# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.code.base import SourceRef, \
                                   SourceRef_VOID
from   quex.blackboard import setup as Setup

class TokenInfo:
    def __init__(self, Name, ID, TypeName=None, SourceReference=SourceRef_VOID):
        self.name         = Name
        self.number       = ID
        self.related_type = TypeName
        self.id           = None
        self.sr           = SourceReference

#-----------------------------------------------------------------------------------------
# token_id_db: list of all defined token-ids together with the file position
#              where they are defined. See token_ide_maker, class TokenInfo.
#-----------------------------------------------------------------------------------------
token_id_db = {}

def get_used_token_id_set():
    return [ token.number for token in token_id_db.values() if token.number is not None ]

def token_id_db_enter(fh, TokenIdName, NumericValue=None):
    global token_id_db
    if isinstance(fh, SourceRef): sr = fh
    elif fh is not None:          sr = SourceRef.from_FileHandle(fh)
    else:                         sr = None
    if TokenIdName.startswith("--"): pretty_token_id_name = TokenIdName[2:]
    else:                            pretty_token_id_name = TokenIdName
    
    ti = TokenInfo(pretty_token_id_name, NumericValue, SourceReference=sr)
    token_id_db[TokenIdName] = ti

#-----------------------------------------------------------------------------------------
# token_id_foreign_set: Set of token ids which came from an external token id file.
#                       All tokens which are not defined in an external token id file
#                       are defined by quex.
#-----------------------------------------------------------------------------------------
token_id_foreign_set = set()

#-----------------------------------------------------------------------------------------
# token_id_implicit_list: Keep track of all token identifiers that ware defined 
#                         implicitly, i.e. not in a token section or in a token id file. 
#                         Each list element has three cells:
#                         [ Prefix-less Token ID, Line number in File, File Name]
#-----------------------------------------------------------------------------------------
token_id_implicit_list = []

#-----------------------------------------------------------------------------------------
# token_repetition_support: Quex can be told to return multiple times the same
#                           token before further analyzsis happens. For this,
#                           the engine needs to know how to read and write the
#                           repetition number in the token itself.
# If the 'token_repetition_token_id_list' is None, then the token repetition feature
# is disabled. Otherwise, token repetition in 'token-receiving.i' is enabled
# and the token id that can be repeated is 'token_repetition_token_id'.
#-----------------------------------------------------------------------------------------
token_repetition_token_id_list = []
token_repetition_source_reference_example = None

#-----------------------------------------------------------------------------------------
# token_type_definition: Object that defines a (user defined) token class.
#
# The first token_type section defines the variable as a real 'TokenTypeDescriptor'.
#
# The setup_parser.py checks for the specification of a manually written token class file. 
# If so then an object of type 'ManualTokenClassSetup' is assigned.
#
# Default = None is detected by the 'input/file/core.py' and triggers the parsing of the 
# default token type description. 
#          
#-----------------------------------------------------------------------------------------
token_type_definition = None

def support_take_text():
    global token_type_definition
    if Setup.token_class_support_take_text_f:
        return True
    else:
        return token_type_definition.take_text is not None 

def support_repetition():
    global token_type_definition
    if not token_type_definition: return False
    else:                         return not token_type_definition.token_repetition_n_member_name.sr.is_void()

def support_token_stamp_line_n():
    # Consistency with token type definition is checked in 'token_type.py'
    return Setup.token_class_support_token_stamp_line_n_f

def support_token_stamp_column_n():
    # Consistency with token type definition is checked in 'token_type.py'
    return Setup.token_class_support_token_stamp_column_n_f

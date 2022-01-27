$$INCLUDE_TOKEN_ID_HEADER$$

QUEX_NAMESPACE_MAIN_OPEN

$$<C>--------------------------------------------------------------------------
void
QUEX_NAME(member_functions_assign)(QUEX_TYPE_ANALYZER* me)
{
$$MEMBER_FUNCTION_ASSIGNMENT$$
}
$$-----------------------------------------------------------------------------

bool
QUEX_NAME(user_constructor)(QUEX_TYPE_ANALYZER* me)
{
    (void)me;

#define self  (*(QUEX_TYPE_ANALYZER*)me)
/* START: User's constructor extensions _______________________________________*/
$$CONSTRUCTOR_EXTENSTION$$
/* END: _______________________________________________________________________*/
#undef self
    return true;
}

void
QUEX_NAME(user_destructor)(QUEX_TYPE_ANALYZER* me)
{
    (void)me;

#define self  (*(QUEX_TYPE_ANALYZER*)me)
/* START: User's constructor extensions _______________________________________*/
$$DESTRUCTOR_EXTENSTION$$
/* END: _______________________________________________________________________*/
#undef self
}

bool
QUEX_NAME(user_reset)(QUEX_TYPE_ANALYZER* me)
{
    (void)me;

#define self  (*(QUEX_TYPE_ANALYZER*)me)
/* START: User's 'reset' ______________________________________________________*/
$$RESET_EXTENSIONS$$
/* END: _______________________________________________________________________*/
#undef self
    return true;
}

void
QUEX_NAME(user_print)(QUEX_TYPE_ANALYZER* me)
{
    (void)me;

#define self  (*(QUEX_TYPE_ANALYZER*)me)
/* START: User's constructor extensions _______________________________________*/
$$USER_DEFINED_PRINT$$
/* END: _______________________________________________________________________*/
#undef self
}

bool
QUEX_NAME(user_memento_pack)(QUEX_TYPE_ANALYZER* me, 
                             const char*         InputName, 
                             QUEX_NAME(Memento)* memento) 
{
    (void)me; (void)memento; (void)InputName;

#define self  (*(QUEX_TYPE_ANALYZER*)me)
/* START: User's memento 'pack' _______________________________________________*/
$$MEMENTO_EXTENSIONS_PACK$$
/* END: _______________________________________________________________________*/
#undef self
    return true;
}

void
QUEX_NAME(user_memento_unpack)(QUEX_TYPE_ANALYZER*  me, 
                               QUEX_NAME(Memento)*  memento)
{
    (void)me; (void)memento;

#define self  (*(QUEX_TYPE_ANALYZER*)me)
/* START: User's memento 'unpack' _____________________________________________*/
$$MEMENTO_EXTENSIONS_UNPACK$$
/* END: _______________________________________________________________________*/
#undef self
}

const char*
QUEX_NAME(map_token_id_to_name)(const QUEX_TYPE_TOKEN_ID TokenID)
/* NOTE: This function is not element of the token namespace, since the token
 *       identifiers are lied to the generated lexical analyzer. The token class
 *       may be used over multiple lexical analyzers.                         */
{
   switch( TokenID ) {
   default: {
       return "<NUMERIC VALUE OF TOKEN-ID UNDEFINED>";
   }
$$MAP_ID_TO_NAME_CASES$$
   }
}

QUEX_NAMESPACE_MAIN_CLOSE


/* -*- C++ -*-   vim: set syntax=cpp: 
 * (C) 2004-2009 Frank-Rene Schaefer
 * ABSOLUTELY NO WARRANTY
 */
#ifndef QUEX_TOKEN_INCLUDE_GUARD__TOKEN__GENERATED__I
#define QUEX_TOKEN_INCLUDE_GUARD__TOKEN__GENERATED__I

$$INCLUDE_TOKEN_CLASS_HEADER$$

QUEX_INLINE void 
QUEX_NAME_TOKEN(construct)($$TOKEN_CLASS$$* __this)
{
#   define self (*__this)
#   define LexemeNull  (&QUEX_GNAME(LexemeNull))
    (void)__this;
$$CONSTRUCTOR$$
#   undef  LexemeNull
#   undef  self
}

QUEX_INLINE void 
QUEX_NAME_TOKEN(destruct)($$TOKEN_CLASS$$* __this)
{
#   define self (*__this)
#   define LexemeNull  (&QUEX_GNAME(LexemeNull))
    if( ! __this ) return;

$$DESTRUCTOR$$
#   undef  LexemeNull
#   undef  self
}

QUEX_INLINE void
QUEX_NAME_TOKEN(copy)($$TOKEN_CLASS$$*       __this, 
                      const $$TOKEN_CLASS$$* __That)
{
#   define self  (*__this)
#   define Other (*__That)
#   define LexemeNull  (&QUEX_GNAME(LexemeNull))
    if( __this == __That ) { return; }
$$COPY$$
#   undef  LexemeNull
#   undef  Other
#   undef  self
    /* If the user even misses to copy the token id, then there's
     * something seriously wrong.                                 */
    __quex_assert(__this->id == __That->id);
    $$<token-stamp-line>   __quex_assert(__this->line_n   == __That->line_n);$$
    $$<token-stamp-column> __quex_assert(__this->column_n == __That->column_n);$$
}


$$<token-take-text>------------------------------------------------------------
QUEX_INLINE void 
QUEX_NAME_TOKEN(take_text)($$TOKEN_CLASS$$*         __this, 
                           const QUEX_TYPE_LEXATOM* Begin, 
                           const QUEX_TYPE_LEXATOM* End)
{
#   define self       (*__this)
#   ifdef  LexemeNull
#   error  "Error LexemeNull shall not be defined here."
#   endif
#   define LexemeNull  (&QUEX_GNAME(LexemeNull))
    (void)__this;
    (void)Begin;
    (void)End;
$$FUNC_TAKE_TEXT$$
#   undef  LexemeNull
#   undef  self
}
$$-----------------------------------------------------------------------------

$$FOOTER$$

#endif /* QUEX_TOKEN_INCLUDE_GUARD__TOKEN__GENERATED__I */

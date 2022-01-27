/* -*- C++ -*- vim: set syntax=cpp:
 * (C) 2005-2010 Frank-Rene Schaefer
 * ABSOLUTELY NO WARRANTY              */
#ifndef QUEX_INCLUDE_GUARD__ANALYZER__MEMBER__NAVIGATION_I
#define QUEX_INCLUDE_GUARD__ANALYZER__MEMBER__NAVIGATION_I

$$INC: definitions$$

QUEX_NAMESPACE_MAIN_OPEN

QUEX_INLINE QUEX_TYPE_STREAM_POSITION  
QUEX_NAME(MF_tell)(QUEX_TYPE_ANALYZER* me)
{
    /* No 'undo terminating zero' -- we do not change the lexeme pointer here. */
    return (QUEX_TYPE_STREAM_POSITION)QUEX_NAME(Buffer_tell)(&me->buffer);
}

QUEX_INLINE void    
QUEX_NAME(MF_seek)(QUEX_TYPE_ANALYZER* me, const QUEX_TYPE_STREAM_POSITION CharacterIndex)
{
    QUEX_LEXEME_TERMINATING_ZERO_UNDO(&me->buffer);
    QUEX_NAME(Buffer_seek)(&me->buffer, (ptrdiff_t)CharacterIndex);
}

QUEX_INLINE void    
QUEX_NAME(MF_seek_forward)(QUEX_TYPE_ANALYZER* me, ptrdiff_t LexatomN)
{
    QUEX_LEXEME_TERMINATING_ZERO_UNDO(&me->buffer);
    QUEX_NAME(Buffer_seek_forward)(&me->buffer, (ptrdiff_t)LexatomN);
}

QUEX_INLINE void    
QUEX_NAME(MF_seek_backward)(QUEX_TYPE_ANALYZER* me, ptrdiff_t LexatomN)
{
    QUEX_LEXEME_TERMINATING_ZERO_UNDO(&me->buffer);
    QUEX_NAME(Buffer_seek_backward)(&me->buffer, (ptrdiff_t)LexatomN);
}

QUEX_INLINE void  
QUEX_NAME(MF_undo)(QUEX_TYPE_ANALYZER* me)
{
    $$<count-line>   me->counter._line_number_at_end   = me->counter._line_number_at_begin;$$
    $$<count-column> me->counter._column_number_at_end = me->counter._column_number_at_begin;$$

    QUEX_LEXEME_TERMINATING_ZERO_UNDO(&me->buffer);

    me->buffer._read_p = me->buffer._lexeme_start_p;

    QUEX_LEXEME_TERMINATING_ZERO_SET(&me->buffer);
}

QUEX_INLINE void  
QUEX_NAME(MF_undo_n)(QUEX_TYPE_ANALYZER* me, ptrdiff_t DeltaN_Backward)
{
    $$<count-line>   me->counter._line_number_at_end   = me->counter._line_number_at_begin;$$
    $$<count-column> me->counter._column_number_at_end = me->counter._column_number_at_begin;$$

    QUEX_LEXEME_TERMINATING_ZERO_UNDO(&me->buffer);

    me->buffer._read_p -= (ptrdiff_t)DeltaN_Backward;

    QUEX_LEXEME_TERMINATING_ZERO_SET(&me->buffer);

    __quex_assert(me->buffer._read_p >= me->buffer._lexeme_start_p);
}

QUEX_NAMESPACE_MAIN_CLOSE

#endif /* QUEX_INCLUDE_GUARD__ANALYZER__MEMBER__NAVIGATION_I */

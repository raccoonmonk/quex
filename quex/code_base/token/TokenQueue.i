/* -*- C++ -*- vim: set syntax=cpp: 
 * PURPOSE: Token Queue 
 *
 * A token queue is a queue where read and write cycles are separate.
 * That is, when the queue is filled, it is not read until the 
 * filling terminated. Then, the read does not terminate before there
 * is no more token left.
 *
 * Wrap-arround is neither necessary nor meaningful!
 *
 * (C) 2004-2017 Frank-Rene Schaefer                                          */
#ifndef QUEX_INCLUDE_GUARD__TOKEN__TOKEN_QUEUE_I
#define QUEX_INCLUDE_GUARD__TOKEN__TOKEN_QUEUE_I

$$INC: definitions$$
$$INC: quex/asserts$$
$$INC: quex/MemoryManager$$

/* NOTE: QUEX_TYPE_TOKEN must be defined at this place!                       */

$$INC: token/TokenQueue$$

QUEX_NAMESPACE_MAIN_OPEN

$$<token-repetition>-----------------------------------------------------------
#define QUEX_TOKEN_ID_IS_REPEATABLE(ID) QUEX_TOKEN_ID_IS_REPETITION
$$-----------------------------------------------------------------------------


QUEX_INLINE void             
QUEX_NAME(TokenQueue_push_core)(QUEX_NAME(TokenQueue)* me, QUEX_TYPE_TOKEN_ID Id);

QUEX_INLINE bool
QUEX_NAME(TokenQueue_construct)(QUEX_NAME(TokenQueue)* me, 
                                QUEX_TYPE_ANALYZER*    lexer,
                                const size_t           N)
/* me:     The token queue.
 * Memory: Pointer to memory of token queue, 0x0 --> no initial memory.
 * N:      Number of token objects that the array can carry.                  */
{
    QUEX_TYPE_TOKEN*   iterator   = 0x0;
    QUEX_TYPE_TOKEN*   memory     = (QUEX_TYPE_TOKEN*)QUEX_GNAME_LIB(MemoryManager_allocate)(
                                             N * sizeof(QUEX_TYPE_TOKEN),
                                             E_MemoryObjectType_TOKEN_ARRAY);
    QUEX_TYPE_TOKEN*   memory_end = &memory[N];

    if( ! memory ) {
        QUEX_NAME(TokenQueue_resources_absent_mark)(me);
        return false;
    }

    __quex_assert(memory != 0x0);

    /* Call placement new (plain constructor) for all tokens in chunk.        */
    for(iterator = memory; iterator != memory_end; ++iterator) {
        QUEX_GNAME_TOKEN(construct)(iterator);
    }
    QUEX_NAME(TokenQueue_init)(me, memory, memory_end); 
    me->the_lexer = lexer;
    return true;
}

QUEX_INLINE void
QUEX_NAME(TokenQueue_reset)(QUEX_NAME(TokenQueue)* me) 
{                                                    
    me->read_iterator  = (QUEX_TYPE_TOKEN*)me->begin; 
    me->write_iterator = (QUEX_TYPE_TOKEN*)me->begin; 
}

QUEX_INLINE void
QUEX_NAME(TokenQueue_init)(QUEX_NAME(TokenQueue)* me, 
                           QUEX_TYPE_TOKEN*       Memory, 
                           QUEX_TYPE_TOKEN*       MemoryEnd) 
{
    me->begin = Memory;                           
    me->end   = MemoryEnd;                        
    QUEX_NAME(TokenQueue_reset)(me);                                
}

QUEX_INLINE void
QUEX_NAME(TokenQueue_resources_absent_mark)(QUEX_NAME(TokenQueue)* me) 
{
    me->begin          = (QUEX_TYPE_TOKEN*)0;                           
    me->end            = (QUEX_TYPE_TOKEN*)0;
    me->read_iterator  = (QUEX_TYPE_TOKEN*)0; 
    me->write_iterator = (QUEX_TYPE_TOKEN*)0; 
    me->the_lexer      = (QUEX_TYPE_ANALYZER*)0; 
}

QUEX_INLINE bool
QUEX_NAME(TokenQueue_resources_absent)(QUEX_NAME(TokenQueue)* me) 
{
    return    me->begin          == (QUEX_TYPE_TOKEN*)0                           
           && me->end            == (QUEX_TYPE_TOKEN*)0
           && me->read_iterator  == (QUEX_TYPE_TOKEN*)0 
           && me->write_iterator == (QUEX_TYPE_TOKEN*)0
           && me->the_lexer      == (QUEX_TYPE_ANALYZER*)0;
}

QUEX_INLINE void
QUEX_NAME(TokenQueue_destruct)(QUEX_NAME(TokenQueue)* me)
{
    QUEX_TYPE_TOKEN* iterator = 0x0;
    /* Call explicit destructors for all tokens in array                      */
    for(iterator = me->begin; iterator != me->end; ++iterator) {
        QUEX_GNAME_TOKEN(destruct)(iterator);
    }

    QUEX_GNAME_LIB(MemoryManager_free)((void*)&me->begin[0],
                               E_MemoryObjectType_TOKEN_ARRAY);

    /* The memory chunk for the token queue itself is located inside the
     * analyzer object. Thus, no explicit free is necessary. In case of user
     * managed token queue memory the user takes care of the deletion.        */
    QUEX_NAME(TokenQueue_resources_absent_mark)(me);
}

QUEX_INLINE void   
QUEX_NAME(TokenQueue_remainder_get)(QUEX_NAME(TokenQueue)* me,
                                    QUEX_TYPE_TOKEN**      begin,
                                    QUEX_TYPE_TOKEN**      end)
{
    *begin = me->read_iterator;
    *end   = me->write_iterator;
    QUEX_NAME(TokenQueue_reset)(me);
}

QUEX_INLINE void 
QUEX_NAME(TokenQueue_memory_get)(QUEX_NAME(TokenQueue)* me,
                                 QUEX_TYPE_TOKEN**      memory,
                                 size_t*                n)
{
    *memory = me->begin;
    *n      = (size_t)(me->end - me->begin);
}

QUEX_INLINE bool 
QUEX_NAME(TokenQueue_is_full)(QUEX_NAME(TokenQueue)* me) 
{ return me->write_iterator >= me->end; }

QUEX_INLINE bool 
QUEX_NAME(TokenQueue_is_empty)(QUEX_NAME(TokenQueue)* me)
{ return me->read_iterator == me->write_iterator; }

QUEX_INLINE void             
QUEX_NAME(TokenQueue_push)(QUEX_NAME(TokenQueue)* me,
                           QUEX_TYPE_TOKEN_ID     Id)
/* Push a token and set only its token identifier.                           */
{
$$<token-repetition>-----------------------------------------------------------
    if( QUEX_TOKEN_ID_IS_REPEATABLE(Id) ) {
        me->write_iterator->QUEX_TOKEN_MEMBER_REPETITION_N = 1;
    }
$$-----------------------------------------------------------------------------
    QUEX_NAME(TokenQueue_push_core)(me, Id);
}

QUEX_INLINE void             
QUEX_NAME(TokenQueue_push_core)(QUEX_NAME(TokenQueue)* me,
                                QUEX_TYPE_TOKEN_ID     Id)
{
    if( QUEX_NAME(TokenQueue_is_full)(me) ) {
        me->the_lexer->error_code = E_Error_Token_QueueOverflow;
        return;
    }
    QUEX_NAME(TokenQueue_assert_before_sending)(me);  

    $$<token-stamp-line>   me->write_iterator->line_n   = me->the_lexer->counter._line_number_at_begin;$$
    $$<token-stamp-column> me->write_iterator->column_n = me->the_lexer->counter._column_number_at_begin;$$

    me->write_iterator->id = Id;              
    ++(me->write_iterator);       
}

$$<token-take-text>------------------------------------------------------------
QUEX_INLINE void             
QUEX_NAME(TokenQueue_push_text)(QUEX_NAME(TokenQueue)* me,
                                QUEX_TYPE_TOKEN_ID     Id,
                                QUEX_TYPE_LEXATOM*     BeginP,
                                QUEX_TYPE_LEXATOM*     EndP)
/* Push a token and set its 'text' member.                                    */
{
    QUEX_NAME(TokenQueue_assert_before_sending)(me);
    QUEX_GNAME_TOKEN(take_text)(me->write_iterator, BeginP, EndP);
    QUEX_NAME(TokenQueue_push)(me, Id);
}
$$-----------------------------------------------------------------------------

$$<not-token-take-text>--------------------------------------------------------
QUEX_INLINE void             
QUEX_NAME(TokenQueue_push_text)(QUEX_NAME(TokenQueue)* me,
                                QUEX_TYPE_TOKEN_ID     Id,
                                QUEX_TYPE_LEXATOM*     BeginP,
                                QUEX_TYPE_LEXATOM*     EndP)
{
    (void)me; (void)Id; (void)BeginP; (void)EndP;
    QUEX_NAME(TokenQueue_assert_before_sending)(me);
    __quex_assert((const char*)0 == "Token type does not support 'take text'.");

    QUEX_NAME(TokenQueue_set_token_TERMINATION)(me);
}
$$-----------------------------------------------------------------------------

$$<token-repetition>-----------------------------------------------------------
QUEX_INLINE void             
QUEX_NAME(TokenQueue_push_repeated)(QUEX_NAME(TokenQueue)* me,
                                    QUEX_TYPE_TOKEN_ID     Id,
                                    size_t                 RepetitionN)
/* Push a repeated token by 'RepetitionN' times. This is only addmissible for
 * TokenId-s specified in the 'repeated_token' section of the '.qx' file.     */
{
    QUEX_NAME(TokenQueue_assert_before_sending)(me);  
    __quex_assert(RepetitionN != 0);        
    __quex_assert(QUEX_TOKEN_ID_IS_REPEATABLE(Id));

    me->write_iterator->QUEX_TOKEN_MEMBER_REPETITION_N = RepetitionN;
    QUEX_NAME(TokenQueue_push_core)(me, Id);
}


QUEX_INLINE QUEX_TYPE_TOKEN* 
QUEX_NAME(TokenQueue_pop)(QUEX_NAME(TokenQueue)* me)
{
    __quex_assert(QUEX_NAME(TokenQueue_begin)(me) != 0x0);

    if( QUEX_NAME(TokenQueue_is_empty)(me) ) {        
        return (QUEX_TYPE_TOKEN*)0;
    }
    else if( QUEX_TOKEN_ID_IS_REPEATABLE(me->read_iterator->id) ) {
        if( me->read_iterator->QUEX_TOKEN_MEMBER_REPETITION_N > 1 ) { 
            me->read_iterator->QUEX_TOKEN_MEMBER_REPETITION_N -= 1;
            if( me->read_iterator->QUEX_TOKEN_MEMBER_REPETITION_N != 0 ) {
                return me->read_iterator;  
            }
        }
    }
    /* Tokens are in queue --> take next token from queue                    */ 
    return me->read_iterator++;
}
#undef QUEX_TOKEN_ID_IS_REPEATABLE

$$------------------------------------------------------------------------------
$$<not-token-repetition>--------------------------------------------------------

QUEX_INLINE void             
QUEX_NAME(TokenQueue_push_repeated)(QUEX_NAME(TokenQueue)* me,
                                    QUEX_TYPE_TOKEN_ID     Id,
                                    size_t                 RepetitionN)
/* Push a repeated token by 'RepetitionN' times. This is only addmissible for
 * TokenId-s specified in the 'repeated_token' section of the '.qx' file.     */
{
    QUEX_NAME(TokenQueue_assert_before_sending)(me);  
    (void)me; (void)Id; (void)RepetitionN;
    __quex_assert(RepetitionN != 0);        

    __quex_assert((const char*)0 == "Token type does not support token repetition.");
    QUEX_NAME(TokenQueue_set_token_TERMINATION)(me);
}

QUEX_INLINE QUEX_TYPE_TOKEN* 
QUEX_NAME(TokenQueue_pop)(QUEX_NAME(TokenQueue)* me)
{
    __quex_assert(QUEX_NAME(TokenQueue_begin)(me) != 0x0);

    if( QUEX_NAME(TokenQueue_is_empty)(me) ) {        
        return (QUEX_TYPE_TOKEN*)0;
    }
    /* Tokens are in queue --> take next token from queue                    */ 
    return me->read_iterator++;
}
$$------------------------------------------------------------------------------

QUEX_INLINE QUEX_TYPE_TOKEN* QUEX_NAME(TokenQueue_begin)(QUEX_NAME(TokenQueue)* me)
{ return me->begin; }

QUEX_INLINE QUEX_TYPE_TOKEN* QUEX_NAME(TokenQueue_back)(QUEX_NAME(TokenQueue)* me)
{ return me->end - 1; }

QUEX_INLINE QUEX_TYPE_TOKEN* QUEX_NAME(TokenQueue_last_token)(QUEX_NAME(TokenQueue)* me)
{ return me->write_iterator == me->begin ? (QUEX_TYPE_TOKEN*)0 : &me->write_iterator[-1]; }

QUEX_INLINE size_t QUEX_NAME(TokenQueue_available_n)(QUEX_NAME(TokenQueue)* me) 
{ return (size_t)(me->end - me->write_iterator); }

QUEX_INLINE void
QUEX_NAME(TokenQueue_set_token_TERMINATION)(QUEX_NAME(TokenQueue)* me) 
/* Reset entire token queue and set the token 'TERMINATION'. This should
 * only be called in case of a detected error.                                */
{
    QUEX_NAME(TokenQueue_reset)(me);
$$<token-take-text>------------------------------------------------------------
    QUEX_NAME(TokenQueue_push_text)(me, QUEX_SETTING_TOKEN_ID_TERMINATION, 
                                    (QUEX_TYPE_LEXATOM*)0, (QUEX_TYPE_LEXATOM*)0);
$$-----------------------------------------------------------------------------
$$<not-token-take-text>--------------------------------------------------------
    QUEX_NAME(TokenQueue_push)(me, QUEX_SETTING_TOKEN_ID_TERMINATION); 
$$-----------------------------------------------------------------------------
}

QUEX_INLINE bool             
QUEX_NAME(TokenQueue_assert_before_sending)(QUEX_NAME(TokenQueue)* me)
{                                                                              
    if( ! QUEX_NAME(TokenQueue_assert_after_sending)(me) ) {
        return false;
    } 
    /* End of token queue has not been reached.                       */          
    __quex_assert((me)->write_iterator != (me)->end);                             
    /* No token sending after 'TERMINATION'.                          */          
    __quex_assert(   (me)->write_iterator         == (me)->begin                  
                  || (me)->write_iterator[-1].id !=  QUEX_SETTING_TOKEN_ID_TERMINATION ); 
    return true;
} 

QUEX_INLINE bool             
QUEX_NAME(TokenQueue_assert_after_sending)(QUEX_NAME(TokenQueue)* me)
{                                                                     
    __quex_assert((me)->begin != 0x0);                                   
    __quex_assert((me)->read_iterator  >= (me)->begin);                  
    __quex_assert((me)->write_iterator >= (me)->read_iterator);          
    /* If the following breaks, then the given queue size was to small*/ 
    if( (me)->write_iterator > (me)->end ) {                            
        QUEX_ERROR_EXIT("Error: Token queue overflow.");                 
        return false;
    }                                                                    
    return true;
}

QUEX_NAMESPACE_MAIN_CLOSE

#endif /* QUEX_INCLUDE_GUARD__TOKEN__TOKEN_QUEUE_I */

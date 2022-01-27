/* -*- C++ -*- vim: set syntax=cpp: 
 * 
 * PURPOSE: Feeder -- coordinates the lexical analysis based on input that
 *                    is fed manually by the caller of the lexical analyser.
 *
 * This file implements an adaptor to a lexical analyzer's class in order to
 * specify a specific 'data feeding scenario'. Where 'normal' lexical analysis
 * relies on filling in the background from some stream or socket, feeding
 * and gavaging implies manual interaction of the consumer of the caller.
 *
 * Feeding can be applied if data chunks arrive in arbitrary sizes. During
 * feeding those chunks are presented to the 'Feeder'. The feeder feeds sub-
 * chunks of those-as big as possible-into the lexical analyzers buffer. The
 * process involves a 'copying' operation. Once a Feeder deliver's a Null
 * token, it can be assumed that all content has been copied or consumed. The
 * memory pointed to can then be freed and new content can be presented to
 * the feeder.
 *
 * PROCEDURE:
 *
 * Data that comes from a framework must be fed using the 'feed()' function.
 * Then, the 'deliver()' function needs to be called. It delivers tokens found
 * until it returns Null. This indicates that all data has been consumed and
 * new data is required to continue analysis. The user must then call 'feed()'
 * again.
 *
 * The constructor of a feeder receives a 'StreamTerminatingTokenId' that 
 * tells when the stream is absolutely terminated. The caller must check
 * the received token against this id and terminate in case that it arrived.
 *
 * EXAMPLES: See the demo's '010' directory.
 *
 * (C) 2016 Frank-Rene Schaefer.                                              */

#ifndef QUEX_INCLUDE_GUARD__ANALYZER__ADAPTORS__FEEDER_I
#define QUEX_INCLUDE_GUARD__ANALYZER__ADAPTORS__FEEDER_I

$$INC: analyzer/adaptors/Feeder$$

QUEX_NAMESPACE_MAIN_OPEN

$$<Cpp>------------------------------------------------------------------------

QUEX_INLINE
QUEX_NAME(Feeder)::QUEX_NAME(Feeder)(QUEX_TYPE_ANALYZER* lexer,
                                     QUEX_TYPE_TOKEN_ID  StreamTerminatingTokenId)
{ QUEX_NAME(Feeder_construct)(this, lexer, StreamTerminatingTokenId); }

QUEX_INLINE void
QUEX_NAME(Feeder)::feed(const void* BeginP, const void* EndP)
{ QUEX_NAME(Feeder_feed)(this, BeginP, EndP); }

QUEX_INLINE QUEX_TYPE_TOKEN* 
QUEX_NAME(Feeder)::deliver()
{ return QUEX_NAME(Feeder_deliver)(this); }

$$-----------------------------------------------------------------------------

QUEX_INLINE void
QUEX_NAME(Feeder_construct)(QUEX_NAME(Feeder)*   me, 
                            QUEX_TYPE_ANALYZER* lexer,
                            QUEX_TYPE_TOKEN_ID  StreamTerminatingTokenId)
{
    /* Initialization                                                         */
    me->base.lexer                       = lexer;
    me->base.last_incomplete_lexeme_p    = (QUEX_TYPE_LEXATOM*)0;
    me->base.stream_terminating_token_id = StreamTerminatingTokenId;

    me->external_chunk.begin_p   = (void*)0;
    me->external_chunk.end_p     = (void*)0;

$$<C>--------------------------------------------------------------------------
    me->feed    = QUEX_NAME(Feeder_feed);
    me->deliver = QUEX_NAME(Feeder_deliver);
$$-----------------------------------------------------------------------------

    if( ! QUEX_SETTING_FALLBACK_MANDATORY ) {
        /* For manual buffer filling, the fallback must be finite and computed 
         * during engine generation. (call Quex with '--fallback-mandatory')  */
        QUEX_GNAME(MF_error_code_set_if_first)(me->base.lexer, 
                                               E_Error_EngineNotGeneratedWithFallbackMandatory);
    }
}

QUEX_INLINE void
QUEX_NAME(Feeder_feed)(QUEX_NAME(Feeder)* me, const void* BeginP, const void* EndP)
{
    __quex_assert(BeginP);
    __quex_assert(EndP);
    /* Copy buffer content into the analyzer's buffer-as much as possible.
     * 'fill()' returns a pointer to the first not-eaten byte.                */
    me->external_chunk.end_p   = EndP;
    me->external_chunk.begin_p = me->base.lexer->buffer.fill(&me->base.lexer->buffer, BeginP, EndP);
}

QUEX_INLINE QUEX_TYPE_TOKEN*
QUEX_NAME(Feeder_deliver)(QUEX_NAME(Feeder)* me)
{
    const bool        EndOfChunkF = me->external_chunk.begin_p == me->external_chunk.end_p ? true : false;
    QUEX_TYPE_TOKEN*  token = QUEX_NAME(receive_from_chunk)(me->base.lexer, 
                                                            EndOfChunkF,
                                                            me->base.stream_terminating_token_id);
    const void*       previous_begin_p;

    while( ! token && me->external_chunk.begin_p != me->external_chunk.end_p ) {
        /* Refill required.
         * => Try to get more out of the remainder of the external chunk.     */
        previous_begin_p           = me->external_chunk.begin_p;
        me->external_chunk.begin_p = me->base.lexer->buffer.fill(&me->base.lexer->buffer, 
                                                                 me->external_chunk.begin_p, 
                                                                 me->external_chunk.end_p);
        if( me->external_chunk.begin_p == previous_begin_p ) {
            /* If '_read_p' stands at beginning of buffer, no more content 
             * can be filled. Buffer size must be large enough to hold a 
             * complete token queue for one step (including skipped data).    */
            QUEX_NAME(MF_error_code_set_if_first)(me->base.lexer, 
                                                  E_Error_Buffer_Feeder_CannotAbsorbMoreContent);
            return (QUEX_TYPE_TOKEN*)0;
        }

        token = QUEX_NAME(receive_from_chunk)(me->base.lexer, EndOfChunkF,
                                              me->base.stream_terminating_token_id);
    }
    return token;
}

QUEX_NAMESPACE_MAIN_CLOSE

#endif /* QUEX_INCLUDE_GUARD__ANALYZER__ADAPTORS__FEEDER_I */


/* vim: set ft=c:
 * (C) Frank-Rene Schaefer */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_I
#define  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_I

$$INC: quex/byte_loader/ByteLoader$$
$$INC: quex/operations$$
$$INC: quex/asserts$$

QUEX_NAMESPACE_QUEX_OPEN

extern QUEX_TYPE_STREAM_POSITION
QUEX_NAME_LIB(ByteLoader_tell)(QUEX_GNAME_LIB(ByteLoader)* me);

extern void                      
QUEX_NAME_LIB(ByteLoader_seek)(QUEX_GNAME_LIB(ByteLoader)* me, QUEX_TYPE_STREAM_POSITION ReadByteIdx);

extern size_t                    
QUEX_NAME_LIB(ByteLoader_load)(QUEX_GNAME_LIB(ByteLoader)* me, void* begin_p, const size_t N, bool* end_of_stream_f);

extern void                    
QUEX_NAME_LIB(ByteLoader_print_this)(QUEX_GNAME_LIB(ByteLoader)* me);

void
QUEX_NAME_LIB(ByteLoader_construct)(QUEX_GNAME_LIB(ByteLoader)* me, 
                     bool                       BinaryModeF,
                     size_t                     ChunkSizeInBytes,
                     QUEX_TYPE_STREAM_POSITION  ChunkPositionOfReadByteIdxZero,
                     void                       (*chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* me, QUEX_TYPE_STREAM_POSITION Pos),
                     size_t                     (*chunk_load)(QUEX_GNAME_LIB(ByteLoader)*, void*, const size_t, bool*),
                     void                       (*destruct)(QUEX_GNAME_LIB(ByteLoader)*),
                     void                       (*print_this)(QUEX_GNAME_LIB(ByteLoader)*),
                     bool                       (*compare_handle)(const QUEX_GNAME_LIB(ByteLoader)*, 
                                                                  const QUEX_GNAME_LIB(ByteLoader)*))
{
    me->tell               = QUEX_GNAME_LIB(ByteLoader_tell);
    me->seek               = QUEX_GNAME_LIB(ByteLoader_seek);
    me->load               = QUEX_GNAME_LIB(ByteLoader_load);
    me->print_this         = QUEX_GNAME_LIB(ByteLoader_print_this);
    me->derived.chunk_seek = chunk_seek;
    me->derived.chunk_load = chunk_load;
    me->derived.print_this = print_this;
    me->destruct           = destruct;
    me->compare_handle     = compare_handle;
    me->on_nothing         = (bool  (*)(struct QUEX_GNAME_LIB(ByteLoader_tag)*, size_t, size_t))0;

    /* Set element size before 'tell()'!                                       */
    me->chunk_size_in_bytes                = ChunkSizeInBytes;  
    me->chunk_position_of_read_byte_i_zero = ChunkPositionOfReadByteIdxZero;
    me->read_byte_i        = 0;
    me->binary_mode_f      = BinaryModeF;          /* Default: 'false' is SAFE */

    me->ownership          = E_Ownership_EXTERNAL; /* Default                  */
}

QUEX_TYPE_STREAM_POSITION
QUEX_NAME_LIB(ByteLoader_tell)(QUEX_GNAME_LIB(ByteLoader)* me)
{
    return me->read_byte_i; 
}

void
QUEX_NAME_LIB(ByteLoader_seek_disable)(QUEX_GNAME_LIB(ByteLoader)* me)
{
    me->derived.chunk_seek = (void (*)(QUEX_GNAME_LIB(ByteLoader)*, QUEX_TYPE_STREAM_POSITION))0;
}

bool
QUEX_NAME_LIB(ByteLoader_seek_is_enabled)(QUEX_GNAME_LIB(ByteLoader)* me)
{
    return me->derived.chunk_seek ? true : false;
}

void                      
QUEX_NAME_LIB(ByteLoader_seek)(QUEX_GNAME_LIB(ByteLoader)* me, QUEX_TYPE_STREAM_POSITION ReadByteIdx)
{
    uint8_t*      tmp_buffer;
    size_t        loaded_n;                                    /* [byte] */
    size_t        block_size = 1024 * me->chunk_size_in_bytes; /* [byte] */
    bool          end_of_stream_f = false;
    QUEX_TYPE_STREAM_POSITION TargetChunkIdx = ReadByteIdx / (QUEX_TYPE_STREAM_POSITION)me->chunk_size_in_bytes; 

    /* Current implementation: only load a multiple of 'chunk_size_in_bytes'.
     * => only seek to positions which are multiples of 'chunk_size_in_bytes'.*/
    __quex_assert(ReadByteIdx % (QUEX_TYPE_STREAM_POSITION)me->chunk_size_in_bytes == 0);

    /* "x < 0": 
     * expressed in a safe manner for any integer type, signed or unsigned:  */
    if( ReadByteIdx < (QUEX_TYPE_STREAM_POSITION)1 && ReadByteIdx != (QUEX_TYPE_STREAM_POSITION)0 ) {
        me->read_byte_i = 0;
        return;
    }
    else if( ! me->derived.chunk_seek ) {
        return;
    }
    else if( me->binary_mode_f ) {
        me->derived.chunk_seek(me, TargetChunkIdx);
        me->read_byte_i = TargetChunkIdx * (QUEX_TYPE_STREAM_POSITION)me->chunk_size_in_bytes;
        return;
    }
    else {
        /* No reliable seek: 
         * Reset the stream, then read until the requested position.          */
        me->derived.chunk_seek(me, me->chunk_position_of_read_byte_i_zero);
        tmp_buffer = (uint8_t*)QUEX_NAME_LIB(MemoryManager_allocate)((size_t)block_size, 
                                                                     E_MemoryObjectType_TEXT);

        me->read_byte_i = 0;
        while( me->read_byte_i != ReadByteIdx ) {
            block_size = QUEX_RANGE(block_size, me->chunk_size_in_bytes, (size_t)(ReadByteIdx - me->read_byte_i));
            loaded_n   = me->load(me, tmp_buffer, block_size, &end_of_stream_f);
            /* 'load()' increments '.read_byte_i'                             */
            if( loaded_n != block_size || end_of_stream_f ) {
                break;
            }
        }
        QUEX_NAME_LIB(MemoryManager_free)((void*)tmp_buffer, E_MemoryObjectType_TEXT);
        return;
    }
}

size_t                    
QUEX_NAME_LIB(ByteLoader_load)(QUEX_GNAME_LIB(ByteLoader)* me, void* begin_p, const size_t N, bool* end_of_stream_f)
/* RETURNS: != 0, if something could be loaded
 *          == 0, if nothing could be loaded further. End of stream (EOS).   
 *
 * Additionally, 'end_of_stream_f' may hint the end of the stream while still
 * some bytes have been loaded. 
 *
 *    *end_of_stream_f == true  => End of stream has been reached.
 *    *end_of_stream_f == false => No assumption if end of stream ore not.
 *
 * The first case is solely a hint to help the caller to act upon end of stream
 * before actually reading zero bytes. It may spare a unnecessary load-cycle
 * which ends up with no load at all.                                        */
{
    size_t    loaded_chunk_n;
    ptrdiff_t try_n = 0;
   
    /* Current implementation: only load a multiple of 'chunk_size_in_bytes'.
     * => only seek to positions which are multiples of 'chunk_size_in_bytes'.*/
    __quex_assert(N % me->chunk_size_in_bytes == 0);

    *end_of_stream_f = false;

    if( ! N ) {
        return 0;
    }

#   if 0
    /* Provide content on byte-granulatity, even if the chunk size > 1. ______*/
    if( me->chunk_cache.has_content_f ) {
        sub_byte_i = me->read_byte_i % me->chunk_size_in_bytes;
        remaining_byte_n = me->chunk_size_in_bytes - sub_byte_i;
        if( remaining_byte_n =< N ) {
            QUEX_GSTD(memcpy)(begin_p, &me->chunk_cache.data[sub_byte_i], N);
            me->read_byte_i += N;
            return N;
        }
        else {
            QUEX_GSTD(memcpy)(begin_p, &me->chunk_cache.data[sub_byte_i], remaining_byte_n);
            me->read_byte_i += remaining_byte_n;
            N               -= remaining_byte_n;
        }
    }
    /*________________________________________________________________________*/
#   endif

    do {
        ++try_n;

        /* Try to load 'N' bytes.                                             */
        loaded_chunk_n = me->derived.chunk_load(me, begin_p, N / me->chunk_size_in_bytes, end_of_stream_f);
        if( loaded_chunk_n ) {
            /* If at least some bytes could be loaded, return 'success'.      */
            me->read_byte_i += (QUEX_TYPE_STREAM_POSITION)(loaded_chunk_n * me->chunk_size_in_bytes);
            return loaded_chunk_n * me->chunk_size_in_bytes;
        }

    } while( me->on_nothing && me->on_nothing(me, (size_t)try_n, N) );

    /* If user's on nothing returns 'false' no further attemps to read.       */
    *end_of_stream_f = true;

    return 0;
}

bool
QUEX_NAME_LIB(ByteLoader_is_equivalent)(const QUEX_GNAME_LIB(ByteLoader)* A, 
                                        const QUEX_GNAME_LIB(ByteLoader)* B)
/* RETURNS: true -- if A and B are equivalent.
 *          false -- else.                                                    */
{
    /* If two QUEX_GNAME_LIB(ByteLoader )classes use the same 'load()' function, then they 
     * should not be different. For example, it does not make sense to have
     * two loaders implementing stdandard libraries 'fread()' interface.     
     *
     * Further, it is always safe to return 'false'.                          */
    if( A == NULL ) {
        if( B != NULL ) return false; 
        else            return true;
    }
    else if( B == NULL ) {
        return false;
    }
    else if( A->load != B->load ) {
        return false;
    }

    /* The 'compare_handle()' function can now safely cast the two pointers
     * to its pointer type.                                                   */
    return A->compare_handle(A, B);
}

void  
QUEX_NAME_LIB(ByteLoader_delete)(QUEX_GNAME_LIB(ByteLoader)** me)
{
    if( ! *me ) {
        return;
    }
    else if( (*me)->destruct ) {
        (*me)->destruct(*me);
    }
    /* NO 'else if'! */
    if( (*me)->ownership == E_Ownership_LEXER ) {
        QUEX_NAME_LIB(MemoryManager_free)((void*)*me, E_MemoryObjectType_BYTE_LOADER);
    }
    (*me) = (QUEX_GNAME_LIB(ByteLoader)*)0;
}

void                    
QUEX_NAME_LIB(ByteLoader_print_this)(QUEX_GNAME_LIB(ByteLoader)* me)
{
    QUEX_DEBUG_PRINT("      byte_loader: {\n");
    QUEX_DEBUG_PRINT1("        binary_mode_f:    %s;\n", E_Boolean_NAME(me->binary_mode_f));
    QUEX_DEBUG_PRINT1("        chunk_size_in_bytes:     %i;\n", (int)me->chunk_size_in_bytes); 
    QUEX_DEBUG_PRINT1("        initial_position: %i;\n", (int)me->chunk_position_of_read_byte_i_zero); 
    QUEX_DEBUG_PRINT1("        current_position: %i;\n", (int)me->tell(me)); 
    if( me->derived.print_this ) {
        me->derived.print_this(me);
    }
    QUEX_DEBUG_PRINT("      }\n");
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_I */

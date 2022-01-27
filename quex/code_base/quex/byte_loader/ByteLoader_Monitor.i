/* vim: set ft=c:
 * (C) Frank-Rene Schaefer */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_MONITOR_I
#define  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_MONITOR_I

$$INC: quex/MemoryManager$$
$$INC: quex/byte_loader/ByteLoader_Monitor$$
#include "quex/byte_loader/ByteLoader_Monitor"
#include <malloc.h> // DEBUG

QUEX_NAMESPACE_QUEX_OPEN

extern void                       QUEX_NAME_LIB(ByteLoader_Monitor_construct)(QUEX_GNAME_LIB(ByteLoader_Monitor)* me,
                                                                            QUEX_GNAME_LIB(ByteLoader)*       source,
                                                                            void*                        reference_object);
extern void                       QUEX_NAME_LIB(ByteLoader_Monitor_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)*     me, 
                                                                       QUEX_TYPE_STREAM_POSITION  Pos);
extern size_t                     QUEX_NAME_LIB(ByteLoader_Monitor_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                                       void*                  buffer, 
                                                                       const size_t           ByteN, 
                                                                       bool*                  end_of_stream_f);
extern void                       QUEX_NAME_LIB(ByteLoader_Monitor_destruct)(QUEX_GNAME_LIB(ByteLoader)* me);
extern void                       QUEX_NAME_LIB(ByteLoader_Monitor_print_this)(QUEX_GNAME_LIB(ByteLoader)* me);
extern bool                       QUEX_NAME_LIB(ByteLoader_Monitor_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                                                                  const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(ByteLoader_Monitor)::QUEX_NAME_LIB(ByteLoader_Monitor)(QUEX_GNAME_LIB(ByteLoader)* source,
                                                                 void*                       reference_object)
{
    QUEX_NAME_LIB(ByteLoader_Monitor_construct)(this, source, reference_object);
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_Monitor_new)(QUEX_GNAME_LIB(ByteLoader)* source,
                                    void*                       reference_object)
    /* ByteLoader takes over ownership over 'source' */
{
    QUEX_GNAME_LIB(ByteLoader_Monitor)* me;
   
    me = (QUEX_GNAME_LIB(ByteLoader_Monitor)*)QUEX_GNAME_LIB(MemoryManager_allocate)(
                   sizeof(QUEX_GNAME_LIB(ByteLoader_Monitor)),
                   E_MemoryObjectType_BYTE_LOADER);

    if( ! me ) return (QUEX_GNAME_LIB(ByteLoader)*)0;

    QUEX_GNAME_LIB(ByteLoader_Monitor_construct)(me, source, reference_object);

    return &QUEX_BASE;
}

void
QUEX_NAME_LIB(ByteLoader_Monitor_construct)(QUEX_GNAME_LIB(ByteLoader_Monitor)* me, 
                                          QUEX_GNAME_LIB(ByteLoader)*       source,
                                          void*                        reference_object)
{
    me->source           = source;
    me->reference_object = reference_object;
    QUEX_TYPE_STREAM_POSITION chunk_size_in_bytes = source ? source->chunk_size_in_bytes : 0;
    QUEX_TYPE_STREAM_POSITION chunk_position_zero = source ? source->chunk_position_of_read_byte_i_zero : 0;
 
    QUEX_GNAME_LIB(ByteLoader_construct)(&QUEX_BASE, source->binary_mode_f,
                                         chunk_size_in_bytes,
                                         chunk_position_of_read_byte_i_zero,
                                         QUEX_GNAME_LIB(ByteLoader_Monitor_chunk_seek),
                                         QUEX_GNAME_LIB(ByteLoader_Monitor_chunk_load),
                                         QUEX_GNAME_LIB(ByteLoader_Monitor_destruct),
                                         QUEX_GNAME_LIB(ByteLoader_Monitor_print_this),
                                         QUEX_GNAME_LIB(ByteLoader_Monitor_compare_handle));
}

void    
QUEX_NAME_LIB(ByteLoader_Monitor_destruct)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_Monitor)* me = (QUEX_GNAME_LIB(ByteLoader_Monitor)*)(alter_ego);

    if( me->on_destruct ) {
        me->on_destruct(me);
    }
    me->source->destruct(me->source);
    QUEX_GNAME_LIB(ByteLoader_delete)(me->source);
}

void                      
QUEX_NAME_LIB(ByteLoader_Monitor_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, QUEX_TYPE_STREAM_POSITION Pos) 
{ 
    QUEX_GNAME_LIB(ByteLoader_Monitor)* me = (QUEX_GNAME_LIB(ByteLoader_Monitor)*)(alter_ego);
    QUEX_TYPE_STREAM_POSITION    position;
    QUEX_TYPE_STREAM_POSITION    result_position;

    if( me->on_seek ) {
        position = me->on_seek(me, Pos);
    }
    else {
        position = Pos;
    }

    me->source->seek(me->source, position);

    ++(me->seek_n);
    me->position_last_seek = position;
}

size_t  
QUEX_NAME_LIB(ByteLoader_Monitor_chunk_load)(QUEX_GNAME_LIB(ByteLoader)*   alter_ego, 
                                 void*                    buffer, 
                                 const size_t             ByteN, 
                                 bool*                    end_of_stream_f) 
{ 
    QUEX_GNAME_LIB(ByteLoader_Monitor)* me = (QUEX_GNAME_LIB(ByteLoader_Monitor)*)(alter_ego);
    size_t                       loaded_byte_n;
    size_t                       byte_n;

    if( me->on_before_load ) {
        byte_n = me->on_before_load(me, ByteN);
    }
    else {
        byte_n = ByteN;
    }

    loaded_byte_n = me->source->load(me->source, buffer, byte_n, end_of_stream_f);

    if( me->on_after_load ) {
        loaded_byte_n = me->on_after_load(me, buffer, loaded_byte_n, end_of_stream_f);
    }

    ++(me->load_n);
    me->loaded_byte_n += loaded_byte_n;

    return loaded_byte_n;
}

bool  
QUEX_NAME_LIB(ByteLoader_Monitor_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                                      const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B) 
/* RETURNS: true  -- if A and B point to the same Memory object.
 *          false -- else.                                                   */
{ 
    const QUEX_GNAME_LIB(ByteLoader_Monitor)* me = (QUEX_GNAME_LIB(ByteLoader_Monitor)*)(alter_ego_A);
    bool                                          result;

    result = me->source->compare_handle(me->source, alter_ego_B);

    return result;
}

void                       
QUEX_NAME_LIB(ByteLoader_Monitor_print_this)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_Monitor)* me = (QUEX_GNAME_LIB(ByteLoader_Monitor)*)(alter_ego);

    QUEX_DEBUG_PRINT("        remote_controlled: {\n");
    me->source->print_this(me->source);
    QUEX_DEBUG_PRINT("        }\n");
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /* QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_MONITOR_I */

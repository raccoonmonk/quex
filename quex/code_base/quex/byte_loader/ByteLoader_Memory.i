/* vim: set ft=c:
 * (C) Frank-Rene Schaefer */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_MEMORY_I
#define  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_MEMORY_I

$$INC: quex/MemoryManager$$
$$INC: quex/byte_loader/ByteLoader_Memory$$
$$INC: quex/asserts$$
#include <malloc.h> // DEBUG

QUEX_NAMESPACE_QUEX_OPEN

extern void                       QUEX_NAME_LIB(ByteLoader_Memory_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                                        QUEX_TYPE_STREAM_POSITION   Pos);
extern size_t                     QUEX_NAME_LIB(ByteLoader_Memory_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                                        void*                       buffer, 
                                                                        const size_t                ByteN, 
                                                                        bool*                       end_of_stream_f);
extern void                       QUEX_NAME_LIB(ByteLoader_Memory_destruct)(QUEX_GNAME_LIB(ByteLoader)* me);
extern void                       QUEX_NAME_LIB(ByteLoader_Memory_print_this)(QUEX_GNAME_LIB(ByteLoader)* me);
extern bool                       QUEX_NAME_LIB(ByteLoader_Memory_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                                                                   const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(ByteLoader_Memory)::ByteLoader_Memory(const uint8_t* BeginP, const uint8_t* EndP)
{
    (void)QUEX_NAME_LIB(ByteLoader_Memory_construct)(this, BeginP, EndP);
}
QUEX_NAME_LIB(ByteLoader_Memory)::QUEX_NAME_LIB(ByteLoader_Memory)(const char* FileName)
{
    (void)QUEX_NAME_LIB(ByteLoader_Memory_construct_from_file_name)(this, FileName);
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_Memory_new)(const uint8_t*  BeginP,
                                     const uint8_t*  EndP)
{
    QUEX_GNAME_LIB(ByteLoader_Memory)* me;
   
    me = (QUEX_GNAME_LIB(ByteLoader_Memory)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_Memory)),
                                                                                    E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_Memory_construct)(me, BeginP, EndP) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_Memory_new_from_file_name)(const char* FileName)
{
    QUEX_GNAME_LIB(ByteLoader_Memory)* me;
   
    me = (QUEX_GNAME_LIB(ByteLoader_Memory)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_Memory)),
                                                                                    E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_Memory_construct_from_file_name)(me, FileName) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

bool
QUEX_NAME_LIB(ByteLoader_Memory_construct_from_file_name)(QUEX_GNAME_LIB(ByteLoader_Memory)* me, 
                                                          const char*                        FileName)
{
    size_t                  size;
    uint8_t*                begin_p;

    /* Determine size of file                                                */;
    FILE* fh = fopen(FileName, "rb"); 
    if( ! fh ) {
        return false;
    }
    if( fseek(fh, 0, SEEK_END) ) {
        fclose(fh);
        return false;
    }
    size = (size_t)ftell(fh);
    if( fseek(fh, 0, SEEK_SET) ) {
        fclose(fh);
        return false;
    }

    /* Load the file's content into some memory.                             */
    begin_p = (uint8_t*)QUEX_GNAME_LIB(MemoryManager_allocate)(size, E_MemoryObjectType_BUFFER_MEMORY);
    if( size != fread(begin_p, 1, size, fh) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(begin_p, E_MemoryObjectType_BUFFER_MEMORY);
        fclose(fh);
        return false;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_Memory_construct)(me, begin_p, &begin_p[size])) {
        QUEX_GNAME_LIB(MemoryManager_free)(begin_p, E_MemoryObjectType_BUFFER_MEMORY);
        fclose(fh);
        return false;
    }
    else {
        /* Mark memory ownership => destructor deletes it.                   */
        ((QUEX_GNAME_LIB(ByteLoader_Memory)*)me)->memory_ownership = E_Ownership_LEXER;
        fclose(fh);
        return true;
    }
}

bool
QUEX_NAME_LIB(ByteLoader_Memory_construct)(QUEX_GNAME_LIB(ByteLoader_Memory)* me, 
                                           const uint8_t*                BeginP,
                                           const uint8_t*                EndP)
{
    __quex_assert(EndP >= BeginP);

    me->byte_array.begin_p  = BeginP;
    me->byte_array.position = BeginP;
    me->byte_array.end_p    = EndP;
    QUEX_GNAME_LIB(ByteLoader_construct)(&QUEX_BASE, true,
                                         /* ChunkSizeInBytes */1,
                                         /* ChunkPositionOfReadByteIdxZero */0,
                                         QUEX_GNAME_LIB(ByteLoader_Memory_chunk_seek),
                                         QUEX_GNAME_LIB(ByteLoader_Memory_chunk_load),
                                         QUEX_GNAME_LIB(ByteLoader_Memory_destruct),
                                         QUEX_GNAME_LIB(ByteLoader_Memory_print_this),
                                         QUEX_GNAME_LIB(ByteLoader_Memory_compare_handle));

    return (! BeginP || ! EndP || BeginP > EndP) ? false : true;
}

void    
QUEX_NAME_LIB(ByteLoader_Memory_destruct)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    /* NOTE: The momory's ownership remains in the hand of the one who
     *       constructed this object.                                        */
    QUEX_GNAME_LIB(ByteLoader_Memory)* me = (QUEX_GNAME_LIB(ByteLoader_Memory)*)(alter_ego);

    if( me->memory_ownership == E_Ownership_LEXER ) {
        QUEX_GNAME_LIB(MemoryManager_free)((void*)&me->byte_array.begin_p[0], 
                                           E_MemoryObjectType_BUFFER_MEMORY);
    }
}

void                      
QUEX_NAME_LIB(ByteLoader_Memory_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, QUEX_TYPE_STREAM_POSITION Pos) 
{ 
    QUEX_GNAME_LIB(ByteLoader_Memory)* me = (QUEX_GNAME_LIB(ByteLoader_Memory)*)(alter_ego);

    if( Pos > me->byte_array.end_p -  me->byte_array.begin_p ) {
        /* Make sure, that the 'load()' will not provide data!                */
        me->byte_array.position = &me->byte_array.end_p[0];
    }
    else {
        me->byte_array.position = &me->byte_array.begin_p[(ptrdiff_t)Pos];
    }
}

size_t  
QUEX_NAME_LIB(ByteLoader_Memory_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, 
                                void*                    buffer, 
                                const size_t             ByteN, 
                                bool*                    end_of_stream_f) 
{ 
    QUEX_GNAME_LIB(ByteLoader_Memory)* me = (QUEX_GNAME_LIB(ByteLoader_Memory)*)(alter_ego);
    const ptrdiff_t               Remaining = me->byte_array.end_p - me->byte_array.position;
    ptrdiff_t                     copy_n;

    if( (size_t)Remaining < ByteN ) { copy_n = Remaining; *end_of_stream_f = true; }
    else                            { copy_n = ByteN; } 

    QUEX_GSTD(memcpy)((void*)buffer, (void*)me->byte_array.position, copy_n);
    me->byte_array.position += copy_n;
    return copy_n;
}

bool  
QUEX_NAME_LIB(ByteLoader_Memory_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                            const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B) 
/* RETURNS: true  -- if A and B point to the same Memory object.
 *          false -- else.                                                   */
{ 
    const QUEX_GNAME_LIB(ByteLoader_Memory)* A = (QUEX_GNAME_LIB(ByteLoader_Memory)*)(alter_ego_A);
    const QUEX_GNAME_LIB(ByteLoader_Memory)* B = (QUEX_GNAME_LIB(ByteLoader_Memory)*)(alter_ego_B);

    return    A->byte_array.begin_p  == B->byte_array.begin_p
           && A->byte_array.end_p    == B->byte_array.end_p
           && A->byte_array.position == B->byte_array.position;
}

void                       
QUEX_NAME_LIB(ByteLoader_Memory_print_this)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_Memory)* me = (QUEX_GNAME_LIB(ByteLoader_Memory)*)(alter_ego);

    QUEX_DEBUG_PRINT("        type:             memory;\n");
    QUEX_DEBUG_PRINT1("        memory_ownership: %s;\n", E_Ownership_NAME(me->memory_ownership));
    QUEX_DEBUG_PRINT3("        byte_array:       { begin: ((%p)) end: ((%p)) size: %i; }\n",
                      (const void*)me->byte_array.begin_p, 
                      (const void*)me->byte_array.end_p, 
                      (int)(me->byte_array.end_p - me->byte_array.begin_p));
    QUEX_DEBUG_PRINT("        input_position:   ");
    QUEX_GNAME_LIB(print_relative_positions)(me->byte_array.begin_p, me->byte_array.end_p, 1, 
                                     (void*)me->byte_array.position);
    QUEX_DEBUG_PRINT("\n");
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /* QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_MEMORY_I */

/* vim: ft=c:
 * (C) Frank-Rene Schaefer */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_POSIX_I
#define  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_POSIX_I

$$INC: quex/MemoryManager$$
$$INC: quex/byte_loader/ByteLoader_POSIX$$

QUEX_NAMESPACE_QUEX_OPEN

extern void                       QUEX_NAME_LIB(ByteLoader_POSIX_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                                       QUEX_TYPE_STREAM_POSITION Pos);
extern size_t                     QUEX_NAME_LIB(ByteLoader_POSIX_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                                       void* buffer, const size_t ByteN, 
                                                                       bool*);
extern void                       QUEX_NAME_LIB(ByteLoader_POSIX_destruct)(QUEX_GNAME_LIB(ByteLoader)* me);
extern void                       QUEX_NAME_LIB(ByteLoader_POSIX_print_this)(QUEX_GNAME_LIB(ByteLoader)* me);
extern bool                       QUEX_NAME_LIB(ByteLoader_POSIX_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                                                       const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(ByteLoader_POSIX)::QUEX_NAME_LIB(ByteLoader_POSIX)(int fd)
{
    (void)QUEX_NAME_LIB(ByteLoader_POSIX_construct)(this, fd);
}
QUEX_NAME_LIB(ByteLoader_POSIX)::QUEX_NAME_LIB(ByteLoader_POSIX)(const char* FileName)
{
    (void)QUEX_NAME_LIB(ByteLoader_POSIX_construct_from_file_name)(this, FileName); 
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_POSIX_new)(int fd)
{
    QUEX_GNAME_LIB(ByteLoader_POSIX)* me;

    if( fd == -1 ) return (QUEX_GNAME_LIB(ByteLoader)*)0;
    me = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_POSIX)),
                                                           E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_POSIX_construct)(me, fd) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_POSIX_new_from_file_name)(const char* FileName)
{
    QUEX_GNAME_LIB(ByteLoader_POSIX)* me;

    me = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_POSIX)),
                                                           E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_POSIX_construct_from_file_name)(me, FileName) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

bool
QUEX_NAME_LIB(ByteLoader_POSIX_construct_from_file_name)(QUEX_GNAME_LIB(ByteLoader_POSIX)* me, 
                                                         const char*                       FileName)
{
    int fd = open(FileName, O_RDONLY);
    return QUEX_GNAME_LIB(ByteLoader_POSIX_construct)(me, fd);
}

bool
QUEX_NAME_LIB(ByteLoader_POSIX_construct)(QUEX_GNAME_LIB(ByteLoader_POSIX)* me, int fd)
{
    QUEX_TYPE_STREAM_POSITION chunk_position_zero = (fd != -1) ? (QUEX_TYPE_STREAM_POSITION)lseek(fd, 0, SEEK_CUR) 
                                                               : (QUEX_TYPE_STREAM_POSITION)0;
    me->fd = fd;

    /* A POSIX file handle is always in binary mode.                         */
    QUEX_GNAME_LIB(ByteLoader_construct)(&QUEX_BASE, true,
                                    /* ChunkSizeInBytes */ 1,
                                    /* ChunkPositionOfReadByteIdxZero */ chunk_position_zero,
                                    QUEX_GNAME_LIB(ByteLoader_POSIX_chunk_seek),
                                    QUEX_GNAME_LIB(ByteLoader_POSIX_chunk_load),
                                    QUEX_GNAME_LIB(ByteLoader_POSIX_destruct),
                                    QUEX_GNAME_LIB(ByteLoader_POSIX_print_this),
                                    QUEX_GNAME_LIB(ByteLoader_POSIX_compare_handle));

    return fd == -1 ?  false : true;
}

void    
QUEX_NAME_LIB(ByteLoader_POSIX_destruct)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_POSIX)* me = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)(alter_ego);

    if( me->fd != -1 ) {
        close(me->fd);
        me->fd = -1;
    }
}

void                      
QUEX_NAME_LIB(ByteLoader_POSIX_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)*    alter_ego, 
                                 QUEX_TYPE_STREAM_POSITION Pos) 
{ 
    QUEX_GNAME_LIB(ByteLoader_POSIX)* me = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)(alter_ego);
    if( me->fd == -1 ) { return; }
    (void)lseek(me->fd, (long)Pos, SEEK_SET); 
}

size_t  
QUEX_NAME_LIB(ByteLoader_POSIX_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, 
                                     void*                       buffer, 
                                     const size_t                ByteN, 
                                     bool*                       end_of_stream_f) 
/* The POSIX interface does not allow to detect end of file upon reading.
 * The caller will realize end of stream by a return of zero bytes.          */
{ 
    QUEX_GNAME_LIB(ByteLoader_POSIX)* me = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)(alter_ego);
    ssize_t                      n;

    if( me->fd == -1 ) { *end_of_stream_f = true; return 0; }

    n = read(me->fd, buffer, ByteN); 

    /* Theoretically, a last 'terminating zero' might be send over socket 
     * connections. Make sure, that this does not appear in the stream.      */
    if( n && ((uint8_t*)buffer)[n-1] == 0x0 ) {
        --n;
    }
    *end_of_stream_f = false;
    return (size_t)n;
}

bool  
QUEX_NAME_LIB(ByteLoader_POSIX_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                           const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B) 
/* RETURNS: true  -- if A and B point to the same POSIX object.
 *          false -- else.                                                   */
{ 
    const QUEX_GNAME_LIB(ByteLoader_POSIX)* A = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)(alter_ego_A);
    const QUEX_GNAME_LIB(ByteLoader_POSIX)* B = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)(alter_ego_B);

    return A->fd == B->fd;
}

void                       
QUEX_NAME_LIB(ByteLoader_POSIX_print_this)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_POSIX)* me = (QUEX_GNAME_LIB(ByteLoader_POSIX)*)(alter_ego);

    QUEX_DEBUG_PRINT("        type:             POSIX;\n");
    QUEX_DEBUG_PRINT1("        file_descriptor:  ((%i));\n", (int)me->fd);
    QUEX_DEBUG_PRINT("        end_of_stream_f:  <no means to detect>;\n");
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_POSIX_I */


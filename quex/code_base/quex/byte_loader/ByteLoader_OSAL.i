/* vim: ft=c:
 * (C) Frank-Rene Schaefer */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_OSAL_I
#define  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_OSAL_I

$$INC: quex/MemoryManager$$
$$INC: quex/byte_loader/ByteLoader_OSAL$$

#include <osapi.h>     /* Usually located in directory '$OSAL_SRC/src/os/inc' */

QUEX_NAMESPACE_QUEX_OPEN

extern void    QUEX_NAME_LIB(ByteLoader_OSAL_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                   QUEX_TYPE_STREAM_POSITION Pos);
extern size_t  QUEX_NAME_LIB(ByteLoader_OSAL_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* me, 
                                                   void* buffer, const size_t ByteN, 
                                                   bool*);
extern void    QUEX_NAME_LIB(ByteLoader_OSAL_destruct)(QUEX_GNAME_LIB(ByteLoader)* me);
extern void    QUEX_NAME_LIB(ByteLoader_OSAL_print_this)(QUEX_GNAME_LIB(ByteLoader)* me);
extern bool    QUEX_NAME_LIB(ByteLoader_OSAL_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                                             const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B);
extern bool    QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(int32 fd);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(ByteLoader_OSAL)::QUEX_NAME_LIB(ByteLoader_OSAL)(int32 fd)
{
    (void)QUEX_NAME_LIB(ByteLoader_OSAL_construct)(this, fd);
}
QUEX_NAME_LIB(ByteLoader_OSAL)::QUEX_NAME_LIB(ByteLoader_OSAL)(const char* FileName)
{
    (void)QUEX_NAME_LIB(ByteLoader_OSAL_construct_from_file_name)(this, FileName); 
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_OSAL_new)(int32 fd)
{
    QUEX_GNAME_LIB(ByteLoader_OSAL)* me;

    if( ! QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(fd) ) return (QUEX_GNAME_LIB(ByteLoader)*)0;
    me = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_OSAL)),
                                                           E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_OSAL_construct)(me, fd) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_OSAL_new_from_file_name)(const char* FileName)
{
    QUEX_GNAME_LIB(ByteLoader_OSAL)* me;

    me = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_OSAL)),
                                                           E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_OSAL_construct_from_file_name)(me, FileName) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

bool
QUEX_NAME_LIB(ByteLoader_OSAL_construct_from_file_name)(QUEX_GNAME_LIB(ByteLoader_OSAL)* me, 
                                                        const char*                       FileName)
{
    int32 fd = OS_open(FileName, OS_READ_ONLY, 0x644);
    return QUEX_GNAME_LIB(ByteLoader_OSAL_construct)(me, fd);
}

bool
QUEX_NAME_LIB(ByteLoader_OSAL_construct)(QUEX_GNAME_LIB(ByteLoader_OSAL)* me, int32 fd)
{
    QUEX_TYPE_STREAM_POSITION chunk_position_zero = QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(fd) ? 
                                                      (QUEX_TYPE_STREAM_POSITION)OS_lseek(fd, 0, SEEK_CUR) 
                                                    : (QUEX_TYPE_STREAM_POSITION)0;
    me->fd = fd;

    /* A OSAL file handle is always in binary mode.                         */
    QUEX_GNAME_LIB(ByteLoader_construct)(&QUEX_BASE, true,
                                    /* ChunkSizeInBytes */ 1,
                                    /* ChunkPositionOfReadByteIdxZero */ chunk_position_zero,
                                    QUEX_GNAME_LIB(ByteLoader_OSAL_chunk_seek),
                                    QUEX_GNAME_LIB(ByteLoader_OSAL_chunk_load),
                                    QUEX_GNAME_LIB(ByteLoader_OSAL_destruct),
                                    QUEX_GNAME_LIB(ByteLoader_OSAL_print_this),
                                    QUEX_GNAME_LIB(ByteLoader_OSAL_compare_handle));

    return QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(fd);
}

void    
QUEX_NAME_LIB(ByteLoader_OSAL_destruct)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_OSAL)* me = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)(alter_ego);

    if( QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(me->fd) ) {
        OS_close(me->fd);
        me->fd = OS_FS_ERROR;
    }
}

void                      
QUEX_NAME_LIB(ByteLoader_OSAL_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)*  alter_ego, 
                                    QUEX_TYPE_STREAM_POSITION    Pos) 
{ 
    QUEX_GNAME_LIB(ByteLoader_OSAL)* me = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)(alter_ego);
    if( ! QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(me->fd) ) { return; }
    (void)OS_lseek(me->fd, (long)Pos, SEEK_SET); 
}

size_t  
QUEX_NAME_LIB(ByteLoader_OSAL_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, 
                                    void*                       buffer, 
                                    const size_t                ByteN, 
                                    bool*                       end_of_stream_f) 
/* The OSAL interface does not allow to detect end of file upon reading.
 * The caller will realize end of stream by a return of zero bytes.          */
{ 
    QUEX_GNAME_LIB(ByteLoader_OSAL)* me = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)(alter_ego);
    int32                            n;

    if( ! QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(me->fd) ) { *end_of_stream_f = true; return 0; }

    n = OS_read(me->fd, buffer, ByteN); 
    switch( n ) {
    case OS_FS_ERR_INVALID_POINTER: n = 0; break;
    case OS_FS_ERROR:               n = 0; break;
    default:                        n = (n>=OS_SUCCESS) ? n : 0; break;
    }

    /* Theoretically, a last 'terminating zero' might be send over socket 
     * connections. Make sure, that this does not appear in the stream.      */
    if( n && ((uint8_t*)buffer)[n-1] == 0x0 ) {
        --n;
    }
    *end_of_stream_f = false;
    return (size_t)n;
}

bool  
QUEX_NAME_LIB(ByteLoader_OSAL_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                              const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B) 
/* RETURNS: true  -- if A and B point to the same OSAL object.
 *          false -- else.                                                   */
{ 
    const QUEX_GNAME_LIB(ByteLoader_OSAL)* A = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)(alter_ego_A);
    const QUEX_GNAME_LIB(ByteLoader_OSAL)* B = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)(alter_ego_B);

    return A->fd == B->fd;
}

bool    
QUEX_NAME_LIB(ByteLoader_OSAL_descriptor_good)(int32 fd)
{
    switch( fd ) {
    case OS_FS_ERROR:                 return false;
    case OS_FS_ERR_DEVICE_NOT_FREE:   return false;
    case OS_FS_ERR_DRIVE_NOT_CREATED: return false;
    case OS_FS_ERR_INVALID_POINTER:   return false;
    case OS_FS_ERR_NAME_TOO_LONG:     return false;
    case OS_FS_ERR_NO_FREE_FDS:       return false;
    case OS_FS_ERR_PATH_INVALID:      return false;
    case OS_FS_ERR_PATH_TOO_LONG:     return false;
    default:                          return fd >= OS_SUCCESS ? true : false;
    }
}


void                       
QUEX_NAME_LIB(ByteLoader_OSAL_print_this)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_OSAL)* me = (QUEX_GNAME_LIB(ByteLoader_OSAL)*)(alter_ego);
    (void)me; (void)alter_ego;

    QUEX_DEBUG_PRINT("        type:             OSAL;\n");
    QUEX_DEBUG_PRINT1("        file_descriptor:  ((%i));\n", (int32)me->fd);
    QUEX_DEBUG_PRINT("        end_of_stream_f:  <no means to detect>;\n");
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_OSAL_I */


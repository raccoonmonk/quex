/* vim: set ft=c:
 * (C) Frank-Rene Schaefer */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_FILE_I
#define  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_FILE_I

$$INC: quex/MemoryManager$$
$$INC: quex/byte_loader/ByteLoader_FILE$$

QUEX_NAMESPACE_QUEX_OPEN

extern void                       QUEX_NAME_LIB(ByteLoader_FILE_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* me, QUEX_TYPE_STREAM_POSITION Pos);
extern size_t                     QUEX_NAME_LIB(ByteLoader_FILE_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* me, void* buffer, const size_t ByteN, bool*);
extern void                       QUEX_NAME_LIB(ByteLoader_FILE_destruct)(QUEX_GNAME_LIB(ByteLoader)* me);
extern void                       QUEX_NAME_LIB(ByteLoader_FILE_print_this)(QUEX_GNAME_LIB(ByteLoader)* me);
extern bool                       QUEX_NAME_LIB(ByteLoader_FILE_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                                                                 const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(ByteLoader_FILE)::QUEX_NAME_LIB(ByteLoader_FILE)(FILE* fh, bool BinaryModeF)
{
    (void)QUEX_NAME_LIB(ByteLoader_FILE_construct)(this, fh, BinaryModeF);
}
QUEX_NAME_LIB(ByteLoader_FILE)::QUEX_NAME_LIB(ByteLoader_FILE)(const char* FileName)
{
    (void)QUEX_NAME_LIB(ByteLoader_FILE_construct_from_file_name)(this, FileName); 
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_FILE_new)(FILE* fh, bool BinaryModeF)
{
    QUEX_GNAME_LIB(ByteLoader_FILE)* me;
   
    me = (QUEX_GNAME_LIB(ByteLoader_FILE)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_FILE)),
                                                                     E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    } 
    else if( ! QUEX_GNAME_LIB(ByteLoader_FILE_construct)(me, fh, BinaryModeF) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

QUEX_GNAME_LIB(ByteLoader)*    
QUEX_NAME_LIB(ByteLoader_FILE_new_from_file_name)(const char* FileName)
{
    QUEX_GNAME_LIB(ByteLoader_FILE)* me;

    me = (QUEX_GNAME_LIB(ByteLoader_FILE)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_GNAME_LIB(ByteLoader_FILE)),
                                                                     E_MemoryObjectType_BYTE_LOADER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else if( ! QUEX_GNAME_LIB(ByteLoader_FILE_construct_from_file_name)(me, FileName) ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me, E_MemoryObjectType_BYTE_LOADER);
        return (QUEX_GNAME_LIB(ByteLoader)*)0;
    }
    else {
        QUEX_BASE.ownership = E_Ownership_LEXER;
        return &QUEX_BASE;
    }
}

bool
QUEX_NAME_LIB(ByteLoader_FILE_construct_from_file_name)(QUEX_GNAME_LIB(ByteLoader_FILE)* me, 
                                                        const char*                      FileName)
{
    FILE*  fh = fopen(FileName, "rb");

    return QUEX_GNAME_LIB(ByteLoader_FILE_construct)(me, fh, true);
}

bool
QUEX_NAME_LIB(ByteLoader_FILE_construct)(QUEX_GNAME_LIB(ByteLoader_FILE)* me, FILE* fh, bool BinaryModeF)
{
    /* IMPORTANT: input_handle must be set BEFORE call to base constructor!
     *            Constructor does call 'tell()'                             */
    QUEX_TYPE_STREAM_POSITION chunk_position_zero = fh ? (QUEX_TYPE_STREAM_POSITION )ftell(fh) 
                                                       : (QUEX_TYPE_STREAM_POSITION )0;
    me->input_handle = fh;

    QUEX_GNAME_LIB(ByteLoader_construct)(&QUEX_BASE, BinaryModeF,
                                         /* ChunkSizeInBytes */ 1,
                                         /* ChunkPositionOfReadByteIdxZero */ chunk_position_zero,
                                         QUEX_GNAME_LIB(ByteLoader_FILE_chunk_seek),
                                         QUEX_GNAME_LIB(ByteLoader_FILE_chunk_load),
                                         QUEX_GNAME_LIB(ByteLoader_FILE_destruct),
                                         QUEX_GNAME_LIB(ByteLoader_FILE_print_this),
                                         QUEX_GNAME_LIB(ByteLoader_FILE_compare_handle));
    return fh ? true : false;
}

void    
QUEX_NAME_LIB(ByteLoader_FILE_destruct)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_FILE)* me = (QUEX_GNAME_LIB(ByteLoader_FILE)*)(alter_ego);

    if( me->input_handle ) {
        fclose(me->input_handle);
        me->input_handle = (FILE*)0;
    }
}

void                      
QUEX_NAME_LIB(ByteLoader_FILE_chunk_seek)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, QUEX_TYPE_STREAM_POSITION Pos) 
{ 
    QUEX_GNAME_LIB(ByteLoader_FILE)* me = (QUEX_GNAME_LIB(ByteLoader_FILE)*)(alter_ego);
    if( ! me->input_handle ) return;
    (void)fseek(me->input_handle, (long)Pos, SEEK_SET); 
}

size_t  
QUEX_NAME_LIB(ByteLoader_FILE_chunk_load)(QUEX_GNAME_LIB(ByteLoader)* alter_ego, 
                                void*                  buffer, 
                                const size_t           ByteN, 
                                bool*                  end_of_stream_f) 
{ 
    QUEX_GNAME_LIB(ByteLoader_FILE)* me = (QUEX_GNAME_LIB(ByteLoader_FILE)*)(alter_ego);
    size_t                      loaded_byte_n;

    if( ! me->input_handle ) { *end_of_stream_f = true; return 0; }

    loaded_byte_n = fread(buffer, 1, ByteN, me->input_handle); 
    *end_of_stream_f = feof(me->input_handle) ? true : false;
    return loaded_byte_n;
}

bool  
QUEX_NAME_LIB(ByteLoader_FILE_compare_handle)(const QUEX_GNAME_LIB(ByteLoader)* alter_ego_A, 
                                          const QUEX_GNAME_LIB(ByteLoader)* alter_ego_B) 
/* RETURNS: true  -- if A and B point to the same FILE object.
 *          false -- else.                                                   */
{ 
    const QUEX_GNAME_LIB(ByteLoader_FILE)* A = (QUEX_GNAME_LIB(ByteLoader_FILE)*)(alter_ego_A);
    const QUEX_GNAME_LIB(ByteLoader_FILE)* B = (QUEX_GNAME_LIB(ByteLoader_FILE)*)(alter_ego_B);

    return A->input_handle == B->input_handle;
}

void                       
QUEX_NAME_LIB(ByteLoader_FILE_print_this)(QUEX_GNAME_LIB(ByteLoader)* alter_ego)
{
    QUEX_GNAME_LIB(ByteLoader_FILE)* me = (QUEX_GNAME_LIB(ByteLoader_FILE)*)(alter_ego);

    QUEX_DEBUG_PRINT("        type:             FILE;\n");
    QUEX_DEBUG_PRINT1("        file_handle:      ((%p));\n", (const void*)me->input_handle);
    if( me->input_handle ) {
        QUEX_DEBUG_PRINT1("        end_of_stream:    %s;\n", E_Boolean_NAME(feof(me->input_handle)));
    }
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__QUEX__BYTE_LOADER__BYTE_LOADER_FILE_I */

#include <basic_functionality.h>
#ifdef __cplusplus
#   include "test_cpp/lib/quex/MemoryManager.i"
#else
#   include "test_c/lib/quex/MemoryManager.i"
#endif
#include <hwut_unit.h>
#define REFERENCE_DIR    "../../../../buffer/TESTS/navigation/TEST/examples/"
#define ARRAY_ELEMENT_N  65536

QUEX_NAMESPACE_MAIN_OPEN

typedef struct QUEX_SETTING_USER_CLASS_DECLARATION_EPILOG_EXT {
   const char* reference_file; 
   int         character_n;
   int         total_converter_call_n;
   int         checksum;
} self_t;

self_t  self;

static void         prepare(const char* CodecName);

static const char*  file_get_name_stem(const char* Codec);
static const char*  file_get_input(const char* Codec);
static const char*  file_get_reference(const char* file_stem);
static size_t       file_load(const char* FileName, void* buffer, size_t Size);

static void         verify_completion(QUEX_GNAME_LIB(Converter)* converter, 
                                      uint8_t* source_p, QUEX_TYPE_LEXATOM_EXT* drain_p);
static void         verify_source_content(uint8_t*       SourceP, 
                                          const uint8_t* SourceEndP);
static void         verify_drain_content(QUEX_TYPE_LEXATOM_EXT*       Drain, 
                                         const QUEX_TYPE_LEXATOM_EXT* DrainEndP);
static void         verify_call_to_convert(QUEX_GNAME_LIB(Converter)*    converter,
                                           uint8_t**                source_pp, 
                                           const uint8_t*           SourceEndP,
                                           QUEX_TYPE_LEXATOM_EXT**      drain_pp,  
                                           const QUEX_TYPE_LEXATOM_EXT* DrainEndP,
                                           E_LoadResult             DrainFilledF);
static void         poison_drain_buffer();

uint8_t             source[ARRAY_ELEMENT_N];
uint8_t             source_backup[ARRAY_ELEMENT_N];
int                 source_byte_n;
QUEX_TYPE_LEXATOM_EXT drain[ARRAY_ELEMENT_N];
QUEX_TYPE_LEXATOM_EXT drain_nominal[ARRAY_ELEMENT_N];
int                 drain_character_n;

/* Following function is converter specific and must be defined in 
 * a file such as 'basic_functionality-CONVERTER.c'.                         */
extern void 
test_this(const char* Codec, void (*test)(QUEX_GNAME_LIB(Converter)*, const char*));

void 
test_with_available_codecs(void (*test)(QUEX_GNAME_LIB(Converter)*, const char*))
{
    if(    strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "uint8_t")  == 0 
        || strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "uint16_t") == 0 
        || strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "uint32_t") == 0 
        || strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "wchar_t")  == 0  ) {
        test_this("ASCII", test);
    }
    if(    strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "uint16_t") == 0 
        || strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "uint32_t") == 0 
        || strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "wchar_t")  == 0  ) {
        test_this("UTF16BE", test);
    }
    if(   strcmp(STR(QUEX_TYPE_LEXATOM_EXT), "uint32_t") == 0 ) {
        test_this("UTF8", test);
        test_this("UCS-4BE", test);
    }

    printf("<terminated>\n");
}

void
print_result(const char* Codec)
{
    printf("{\n    codec:              %s;\n"
           "    reference_file:     %s;\n"
           "    character_n:        %i;\n"
           "    sub-tests (3 runs): %i;\n"
           "    checksum:           %i;\n}\n",
           Codec,
           self.reference_file, 
           self.character_n, 
           self.total_converter_call_n,
           self.checksum);
}

void
test_conversion_in_one_beat(QUEX_GNAME_LIB(Converter)* converter, const char* CodecName)
{
    uint8_t*              s_p;
    QUEX_TYPE_LEXATOM_EXT*  d_p;
    int                   i;

    printf("function: %s;\n", __func__);
    prepare(CodecName);

    for(i = 0; i < 3; ++i) {
        poison_drain_buffer();

        s_p = &source[0];
        d_p = &drain[0];

        /* Complete source is present => conversion must be complete.
         * converter must return 'true.'                                     */
        verify_call_to_convert(converter, &s_p, &source[source_byte_n],
                               &d_p, &drain[drain_character_n], 
                               /* FilledF */ E_LoadResult_COMPLETE);

        verify_completion(converter, s_p, d_p);
    }
}

void
test_conversion_stepwise_source(QUEX_GNAME_LIB(Converter)* converter, 
                                const char*           CodecName)
{
    uint8_t*              s_p;
    QUEX_TYPE_LEXATOM_EXT*  d_p;
    int                   i;

    printf("function: %s;\n", __func__);
    prepare(CodecName);

    for(i = 0; i < 3; ++i) {
        poison_drain_buffer();

        s_p = &source[0];
        d_p = &drain[0];
        for(i = 0; i < source_byte_n; ++i) {
            /* As long as the last source byte has not been received, the drain
             * can never be full.                                            */
            verify_call_to_convert(converter, &s_p, &source[i+1], 
                                   &d_p, &drain[drain_character_n], 
                                   (i == source_byte_n-1) ? E_LoadResult_COMPLETE : E_LoadResult_INCOMPLETE);
        }
        verify_completion(converter, s_p, d_p);
    }
}

void
test_conversion_stepwise_drain(QUEX_GNAME_LIB(Converter)* converter, 
                               const char*           CodecName)
{
    uint8_t*              s_p;
    QUEX_TYPE_LEXATOM_EXT*  d_p;
    int                   i;

    printf("function: %s;\n", __func__);
    prepare(CodecName);

    for(i = 0; i < 3; ++i) {
        poison_drain_buffer();

        s_p = &source[0];
        d_p = &drain[0];
        for(i = 0; i < drain_character_n; ++i) {
            /* There are always enough source bytes to fill the drain character
             * as long as i < drain_character_n.                             */
            verify_call_to_convert(converter, &s_p, &source[source_byte_n], 
                                   &d_p, &drain[i+1], E_LoadResult_COMPLETE);
        }
        
        verify_completion(converter, s_p, d_p);
    }
}

static void
prepare(const char* CodecName)
{
    const char*  file_name           = file_get_input(CodecName);
    const char*  reference_file_name = file_get_reference(CodecName);

    /* Poison all buffers, so that bad steps cause failure. */
    memset(&source[0], 0xFF, sizeof(source));
    memset(&source_backup[0], 0xFF, sizeof(source_backup));
    memset(&drain[0], 0xFF, sizeof(drain));
    memset(&drain_nominal[0], 0xFF, sizeof(drain_nominal));

    /* Load content into source and nominal drain. */
    source_byte_n     = file_load(file_name, &source[0], ARRAY_ELEMENT_N);
    drain_character_n = file_load(reference_file_name, &drain_nominal[0], 
                                  ARRAY_ELEMENT_N * sizeof(QUEX_TYPE_LEXATOM_EXT))
                        / sizeof(QUEX_TYPE_LEXATOM_EXT);
    self.character_n = drain_character_n;

    hwut_verify(source_byte_n);
    hwut_verify(drain_character_n);

    /* Backup the source, so it s checked that source is not altered. */
    memcpy(&source_backup[0], &source[0], source_byte_n);

    self.total_converter_call_n = 0;
}

static const char* 
file_get_name_stem(const char* Codec)
{
    if     ( strcmp(Codec, "ASCII") == 0 )   return REFERENCE_DIR "festgemauert";
    else if( strcmp(Codec, "UTF8") == 0 )    return REFERENCE_DIR "languages";
    else if( strcmp(Codec, "UTF16BE") == 0 ) return REFERENCE_DIR "small";
    else if( strcmp(Codec, "UCS-4BE") == 0 ) return REFERENCE_DIR "languages";
    else                                     return "";
}

static const char* 
file_get_input(const char* Codec)
{
    static char  file_name[1024];
    const char*  file_stem = file_get_name_stem(Codec);

    if     ( strcmp(Codec, "ASCII") == 0 )   snprintf(&file_name[0], 1023, "%s.dat", file_stem); 
    else if( strcmp(Codec, "UTF8") == 0 )    snprintf(&file_name[0], 1023, "%s.utf8", file_stem);
    else if( strcmp(Codec, "UTF16BE") == 0 ) snprintf(&file_name[0], 1023, "%s.utf16-be", file_stem); 
    else if( strcmp(Codec, "UCS-4BE") == 0 ) snprintf(&file_name[0], 1023, "%s.ucs4-be", file_stem);
    else                                     return "";

    return &file_name[0];
}

static const char*
file_get_reference(const char* Codec)
/* Finds the correspondent unicode file to fill the reference buffer with
 * pre-converted data. A file stem 'name' is converted into a file name 
 *
 *             name-SIZE-ENDIAN.dat
 *
 * where SIZE indicates the size of a buffer element in bits (8=Byte, 16= 
 * 2Byte, etc.); ENDIAN indicates the system's endianess, 'le' for little
 * endian and 'be' for big endian. 
 */
{
#   ifdef __cplusplus
    const char*  endian_str = quex::system_is_little_endian() ? "le" : "be";
#   else
    const char*  endian_str = quex_system_is_little_endian() ? "le" : "be";
#   endif
    static char  file_name[1024];
    const char*  file_stem = file_get_name_stem(Codec);

    if( sizeof(QUEX_TYPE_LEXATOM_EXT) == 1 ) {
        snprintf(&file_name[0], 1023, "%s.dat", file_stem);
    }
    else {
        snprintf(&file_name[0], 1023, "%s-%i-%s.dat", file_stem, 
                 (int)sizeof(QUEX_TYPE_LEXATOM_EXT)*8, endian_str);
    }
    self.reference_file = &file_name[0];
    return &file_name[0];
}

static size_t      
file_load(const char* FileName, void* buffer, size_t Size)
{
    FILE*      fh;
    size_t     loaded_byte_n;

    fh = fopen(FileName, "rb");
   
    if( !fh ) {
        printf("Could not load '%s'.\n", FileName);
        return 0;
    }

    loaded_byte_n = fread(buffer, 1, Size, fh);
    fclose(fh);
    return loaded_byte_n;
}

static void
verify_completion(QUEX_GNAME_LIB(Converter)* converter, 
                  uint8_t* source_p, QUEX_TYPE_LEXATOM_EXT* drain_p)
{
    /* Nothing shall be left in stomach. */
    hwut_verify(source_p - &source[0] == source_byte_n);
    if( converter->stomach_byte_n ) {
        if( converter->stomach_byte_n(converter) != -1 ) {
            hwut_verify(converter->stomach_byte_n(converter) == 0);
        }
    }

    /* All is converted. */
    hwut_verify(drain_p - &drain[0] == drain_character_n);

    /* Converted content must be correct! */
    verify_drain_content(&drain[0], &drain[drain_character_n]);

    /* Input buffer is NOT to be touched. */
    verify_source_content(&source[0], &source[source_byte_n]);

    /* '.stomach_clear()' shall not do any harm. */
    if( converter->stomach_clear ) {
        converter->stomach_clear(converter);
    }
}


static void
poison_drain_buffer()
{
    memset(&drain[0], 0x5A, drain_character_n * sizeof(QUEX_TYPE_LEXATOM_EXT));
}

static void
verify_call_to_convert(QUEX_GNAME_LIB(Converter)* converter,
                       uint8_t**             source_pp, const uint8_t*             SourceEndP,
                       QUEX_TYPE_LEXATOM_EXT**   drain_pp,  const QUEX_TYPE_LEXATOM_EXT* DrainEndP,
                       E_LoadResult          DrainFilledF)
{
    uint8_t*           s_p_before = *source_pp;
    QUEX_TYPE_LEXATOM_EXT* d_p_before = *drain_pp;
    QUEX_TYPE_LEXATOM_EXT* p;
    E_LoadResult       result;

    result = converter->convert(converter, source_pp, SourceEndP, 
                                (void**)drain_pp, (const void*)DrainEndP); 
    self.total_converter_call_n += 1;
    for(p=d_p_before; p != *drain_pp ; ++p) {
        self.checksum = (self.checksum << 5) % 997 + *p;
    }

    hwut_verify(result == DrainFilledF);

    hwut_verify(s_p_before <= *source_pp && *source_pp <= SourceEndP);
    hwut_verify(d_p_before <= *drain_pp  && *drain_pp  <= DrainEndP); 
    if( converter->stomach_byte_n ) {
        if( converter->stomach_byte_n(converter) != -1 ) {
            hwut_verify(*source_pp - converter->stomach_byte_n(converter) <= SourceEndP);
            hwut_verify(*source_pp - converter->stomach_byte_n(converter) >= &source[0]);
        }
    }

    /* Converted content must be correct! */
    verify_drain_content(d_p_before, *drain_pp);

    /* Input buffer is NOT to be touched. */
    verify_source_content(s_p_before, *source_pp);
}

static void
verify_source_content(uint8_t* SourceP, const uint8_t* SourceEndP)
{
    const ptrdiff_t Offset = SourceP - &source[0];
    const size_t    Size   = (size_t)(SourceEndP - SourceP);

    hwut_verify( 
        memcmp((void*)&source_backup[Offset], (void*)SourceP, Size) == 0
    );
}

static void
verify_drain_content(QUEX_TYPE_LEXATOM_EXT* DrainP, 
                     const QUEX_TYPE_LEXATOM_EXT* DrainEndP)
{
    const ptrdiff_t   Offset = DrainP - &drain[0];
    const size_t      Size   = (size_t)(DrainEndP - DrainP);

    hwut_verify( 
        memcmp((void*)&drain_nominal[Offset], (void*)DrainP, Size) == 0
    );
}

QUEX_NAMESPACE_MAIN_CLOSE

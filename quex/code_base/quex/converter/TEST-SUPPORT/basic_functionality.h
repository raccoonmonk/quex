#include "minimum-definitions.h"
#ifdef __cplusplus
#include "test_cpp/lib/quex/converter/Converter"
#else
#include "test_c/lib/quex/converter/Converter"
#endif
#include <stdint.h>

QUEX_NAMESPACE_MAIN_OPEN

extern void test_with_available_codecs(void (*test)(QUEX_GNAME_LIB(Converter)*, const char*));

extern void test_conversion_in_one_beat(QUEX_GNAME_LIB(Converter)* converter, 
                                        const char*           CodecName);

extern void test_conversion_stepwise_source(QUEX_GNAME_LIB(Converter)* converter, 
                                            const char*           CodecName);

extern void test_conversion_stepwise_drain(QUEX_GNAME_LIB(Converter)* converter, 
                                           const char*           CodecName);
extern void print_result(const char*);

#define STR_CORE(X) #X
#define STR(X) STR_CORE(X)

QUEX_NAMESPACE_MAIN_CLOSE

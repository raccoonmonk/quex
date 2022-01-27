/* -*- C++ -*- vim:set syntax=cpp:
 * (C) 2005-2010 Frank-Rene Schaefer
 * ABSOLUTELY NO WARRANTY                      */
#ifndef QUEX_INCLUDE_GUARD__IMPLEMENTATIONS_I
#define QUEX_INCLUDE_GUARD__IMPLEMENTATIONS_I

#if ! defined(__cplusplus)

$$INC: analyzer/asserts.i$$
$$INC: buffer/asserts.i$$

$$INCLUDE_TOKEN_CLASS_IMPLEMENTATION$$
$$INC: token/TokenQueue.i$$
$$INC: token/receiving.i$$

$$INC: analyzer/member/mode-handling.i$$
$$INC: analyzer/member/misc.i$$
$$INC: analyzer/member/navigation.i$$

$$INC: analyzer/struct/constructor.i$$
$$INC: analyzer/struct/include-stack.i$$
$$INC: analyzer/struct/reset.i$$

$$INC: buffer/Buffer.i$$
$$INC: buffer/lexatoms/LexatomLoader.i$$

$$INC: analyzer/Mode.i$$

$$INC: <lib-lexeme> lexeme/basics.i$$
$$INC: <count>      analyzer/Counter.i$$


#endif

$$INC: <lib-quex && not-memory-management-extern> quex/MemoryManager.i$$
$$INC: <lib-quex>                                 quex/byte_loader/ByteLoader.i$$
$$INC: <lib-quex && std-lib>                      quex/byte_loader/ByteLoader_FILE.i$$
$$INC: <lib-quex && std-lib && Cpp>               quex/byte_loader/ByteLoader_stream.i$$
$$INC: <lib-quex>                                 quex/converter/Converter.i$$
$$INC: <lib-lexeme>                               lexeme/converter-from-lexeme.i$$
$$INC: <tiny-std-lib>                             quex/tiny_stdlib.i$$

$$<not-token-class-only && lexeme-null>----------------------------------------
QUEX_NAMESPACE_MAIN_OPEN
QUEX_TYPE_LEXATOM   QUEX_NAME(LexemeNull) = (QUEX_TYPE_LEXATOM)0;
QUEX_NAMESPACE_MAIN_CLOSE
$$-----------------------------------------------------------------------------


#endif /* QUEX_INCLUDE_GUARD__IMPLEMENTATIONS_I */

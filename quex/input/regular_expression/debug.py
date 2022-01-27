# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
__debug_recursion_depth  = -1
__debug_output_enabled_f = False # True / False 

def __debug_print(msg, msg2="", msg3=""):
    global __debug_recursion_depth
    if not __debug_output_enabled_f: return
    if type(msg2) != str: msg2 = repr(msg2)
    if type(msg3) != str: msg3 = repr(msg3)
    txt = "##" + "  " * __debug_recursion_depth + msg + " " + msg2 + " " + msg3
    txt = txt.replace("\n", "\n    " + "  " * __debug_recursion_depth)
    print(txt)
    
def __debug_exit(result, stream):
    global __debug_recursion_depth
    __debug_recursion_depth -= 1

    if __debug_output_enabled_f: 
        pos = stream.tell()
        txt = stream.read(64).replace("\n", "\\n")
        stream.seek(pos)    
        __debug_print("##exit: [%s], remainder = \"%s\"" % (type(result), txt))
        
    return result

def __debug_entry(function_name, stream):
    global __debug_recursion_depth
    __debug_recursion_depth += 1

    if __debug_output_enabled_f: 
        pos = stream.tell()
        txt = stream.read(64).replace("\n", "\\n")
        stream.seek(pos)    
        __debug_print("##entry: %s, remainder = \"%s\"" % (function_name, txt))

def __debug_print_stream(Prefix, stream):
    pos = stream.tell()
    print("#%s: [%s]" % (Prefix, stream.read(64).replace("\n", "\\n")))
    stream.seek(pos)    


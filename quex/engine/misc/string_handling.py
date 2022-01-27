# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
def blue_print(BluePrintStr, replacementsRaw):
    """Takes a string acting as blue print and replaces all
       replacements of the form r in replacements:

           r[0] = original pattern
           r[1] = replacements
    """
    def error(replacements):
        for original, replacement in replacements:
            if not isinstance(replacement, str):
                print("##", original, "  ->  ", repr(replacement.__class__.__name__))
                print("##>>", replacement)
        assert False

    # Only consider replacements where orig != empty
    replacements = [ x for x in replacementsRaw if x[0] ]

    if not replacements: return BluePrintStr
    start        = common_start([x[0] for x in replacements])
    Lstart       = len(start)

    # Only consider the part of the original which is not common start
    replacements = [ (x[0][Lstart:], len(x[0][Lstart:]), x[1]) for x in replacements ]

    # -- sort the replacements so that long strings are replaced first
    replacements.sort(key=lambda x: (-x[1], x[0]))  # x[0] = original; x[1] = len(original)

    txt      = BluePrintStr
    Lt       = len(txt)
    result   = []
    prev_end = 0
    while 1 + 1 == 2:
        i = txt.find(start, prev_end)
        if i == -1: 
            result.append(txt[prev_end:])
            try:    
                return "".join(result)
            except: 
                error(replacements)

        # The 'orig' begins after the common start.
        iStart = i + Lstart
        for orig, Lo, replacement in replacements:
            if iStart + Lo <= Lt and txt[iStart:iStart+Lo] == orig:
                result.append(txt[prev_end:i])
                result.append(replacement)
                prev_end = iStart + Lo
                break
        else:
            # Nothing matched the expression starting with '$' simply
            # continue as if nothing happend.
            result.append(txt[prev_end:i+1])
            prev_end  = i + 1

def common_start(stringList):
    """RETURNS: common string that all strings start with in 'stringList'.
    """
    if not stringList: 
        return ""
    stringList.sort(key=lambda x: len(x))
    result = stringList[0]
    rangeL = range(len(result))
    for string in stringList[1:]:
        if string.startswith(result): 
            continue
        for i in rangeL:
            # Strings are sorted by length => always i <= len(string)
            if result[i] != string[i]:
                result = result[:i]
                rangeL = range(len(result))
                break
    return result

def pretty_code(Code, Base=4):
    """-- Delete empty lines at the beginning
       -- Delete empty lines at the end
       -- Strip whitespace after last non-whitespace
       -- Propper Indendation based on Indentation Counts

       Base = Min. Indentation
    """
    class Info:
        def __init__(self, IndentationN, Content):
            self.indentation = IndentationN
            self.content     = Content
    info_list           = []
    no_real_line_yet_f  = True
    indentation_set     = set()
    for element in Code:
        for line in element.splitlines():
            line = line.rstrip() # Remove trailing whitespace
            if len(line) == 0 and no_real_line_yet_f: continue
            else:                                     no_real_line_yet_f = False

            content     = line.lstrip()
            if content.startswith("#"): indentation = 0
            else:                       indentation = len(line) - len(content) + Base
            info_list.append(Info(indentation, content))
            indentation_set.add(indentation)

    # Discretize indentation levels
    indentation_list = list(indentation_set)
    indentation_list.sort()

    # Collect the result
    result              = []
    # Reverse so that trailing empty lines are deleted
    no_real_line_yet_f  = True
    for info in reversed(info_list):
        if len(info.content) == 0 and no_real_line_yet_f: continue
        else:                                             no_real_line_yet_f = False
        indentation_level = indentation_list.index(info.indentation)
        result.append("%s%s\n" % ("    " * indentation_level, info.content))

    return "".join(reversed(result))


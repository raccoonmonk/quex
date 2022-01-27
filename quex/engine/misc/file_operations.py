# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import os
import sys

def open_file_or_die(FileName, Mode="r", Env=None, CodecCheckF=True, Encoding="utf-8-sig"):
    fh = __open_safely(FileName, Mode, Encoding)
    if fh is None:
        # NOTE: Use 'print()' instead of 'quex.engine.misc.error.log()'
        #       => avoid circular import
        print("Cannot open file '%s'" % FileName)
        if Env is not None:
            print("Is environment variable '%s' set propperly?" % Env) 
        sys.exit(-1)
    return fh

def get_file_content_or_die(FileName, Mode="r"):
    fh  = open_file_or_die(FileName, Mode)
    txt = fh.read()
    fh.close()
    return txt

def write_safely_and_close(FileName, txt):
    fh = open_file_or_die(FileName, Mode="w", CodecCheckF=False, Encoding="utf-8")
    if os.linesep != "\n": txt = txt.replace("\n", os.linesep)
    # NOTE: According to bug 2813381, maybe due to an error in python,
    #       there appeared two "\r" instead of one "\r\r".
    while txt.find("\r\r") != -1:
        txt = txt.replace("\r\r", "\r")
    fh.write(txt)
    fh.close()


count_db = {}

def count_until_position(file_name, Pos, Char):
    hint  = __count_until_position_cache_find(file_name, Pos, Char)
    count = count_until_position_raw(open_file_or_die(file_name), Pos, Char, hint)

    sub_db   = count_db.get(file_name)
    new_hint = (Pos, count)
    if not sub_db:           count_db[file_name] = { Char: set([new_hint]) }
    elif Char not in sub_db: sub_db[Char]        = set([new_hint])
    else:                    sub_db[Char].add(new_hint)
        
    return count


count_db = {}
def __count_until_position_cache_find(file_name, Pos, Char):
    sub_db = count_db.get(file_name)
    if not sub_db:
        return None

    position_count_list = sub_db.get(Char)
    if not position_count_list:
        return None

    # find greatest position < Pos
    best = (0, 0)
    for pos, count in position_count_list:
        if   pos > Pos:     continue
        elif pos > best[0]: best = (pos, count)
    return best if best != (0,0) else None
                

def count_until_position_raw(fh, Pos, Char, Hint=None):
    if not Hint: 
        fh.seek(0)
        count = 1
    else:
        fh.seek(Hint[0])
        count = Hint[1]

    # When reading 'position' number of characters from '0', then we are
    # at position 'position' at the end of the read. That means, we are where
    # we started. With UTF8 streams, the position is no longer linear with
    # the position. So reading until position is more difficult.
    while fh.tell() < Pos:
        try:
            tmp = fh.read(1)
        except:
            break
        if   not tmp:     break
        elif tmp == Char: count += 1

    return count

def read_between_positions(fh, Start, End):
    fh.seek(Start)
    # When reading 'position' number of characters from '0', then we are
    # at position 'position' at the end of the read. That means, we are where
    # we started. With UTF8 streams, the position is no longer linear with
    # the position. So reading until position is more difficult.
    txt = []
    while fh.tell() < End:
        try:
            tmp = fh.read(1)
        except:
            # Need to catch encoding errors and the like
            break
        if not tmp: break
        else:       txt.append(tmp)
    return "".join(txt)

def __ensure_directory_for_file_exists(FileName):
    directory = os.path.dirname(FileName)
    if not directory:
        return True

    elif not os.path.isdir(directory):
        try:    os.makedirs(directory)
        except: return None
        return True
    else:
        return True

def __open_safely(FileName, Mode, Encoding):
    file_name = FileName.replace("//","/")
    file_name = os.path.normpath(file_name)

    if "w" in Mode:
        if not __ensure_directory_for_file_exists(file_name):
            return None

    try:    return open(file_name, Mode, encoding=Encoding)
    except: return None


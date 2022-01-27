# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import io

def UniStream(TextOrStream, Name=None, UnsetStringF=False):
    """This class is to replace 'StringIO' from Python 2 in Python 3.

    GOAL: -- Have a string behave like a file (handle)
          -- provide current relative seek operations
          -- provide output as text (not bytes as in BytesIO)
    """
    if   isinstance(TextOrStream, UniStreamBase): result = TextOrStream
    elif isinstance(TextOrStream, str):           result = UniStreamBytesIO(TextOrStream, Name)
    else:                                         result = UniStreamStream(TextOrStream)

    if UnsetStringF: result.unset_string_f()
    return result

class UniStreamBase:
    def __init__(self):
        self._stream_name = "<command line>"
        self._not_a_string_anyway_f = False

    @property
    def name(self):
        return self._stream_name

    def unset_string_f(self):
        self._not_a_string_anyway_f = True

class UniStreamStream(UniStreamBase):
    def __init__(self, Stream):
        self.stream = Stream
        if hasattr(self.stream, "name"): self._stream_name = self.stream.name
        UniStreamBase.__init__(self)

    @property
    def name(self):
        if hasattr(self.stream, "name"): return self.stream.name
        else:                            return "<nameless stream>"

    def read(self, N=None):
        return self.stream.read(N)

    def readline(self):
        return self.stream.readline()

    def tell(self):
        return self.stream.tell()

    def seek(self, X, Y=io.SEEK_SET):
        return self.stream.seek(X, Y)

    def string_f(self):
        if self._not_a_string_anyway_f: return False
        return isinstance(self.stream, io.StringIO)

class UniStreamBytesIO(UniStreamBase):
    def __init__(self, Text, Name=None):
        self.stringio = io.StringIO(Text)
        if Name is not None: self._stream_name = Name
        UniStreamBase.__init__(self)

    def read(self, N=None):
        return self.stringio.read(N)

    def readline(self):
        return self.stringio.readline()

    def tell(self):
        return self.stringio.tell()

    def seek(self, X, Y=io.SEEK_SET):
        return self.stringio.seek(X, Y)

    def string_f(self):
        if self._not_a_string_anyway_f: return False
        return True


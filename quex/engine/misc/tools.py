# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.quex_enum  import QuexEnum
from   quex.DEFINITIONS            import QUEX_PATH
from   quex.constants              import INTEGER_MAX

from   itertools   import islice, combinations
import functools
from   operator    import iconcat
from   collections import deque
import sys
import os
from   enum import auto

def cmp(A, B):
    return (A>B)-(A<B)

def quex_chr(x, SpaceIsSpaceF=False):
    return     "-oo"              if x == - INTEGER_MAX   \
           else "oo"              if x == INTEGER_MAX - 1 \
           else "' '"             if x == ord(' ')  and not SpaceIsSpaceF \
           else "\\t"             if x == ord('\t') \
           else "\\n"             if x == ord('\n') \
           else "\\b"             if x == ord('\b') \
           else "\\f"             if x == ord('\f') \
           else "\\r"             if x == ord('\r') \
           else "\\a"             if x == ord('\a') \
           else "\\v"             if x == ord('\v') \
           else "<%04x>" % x      if x >= 0xD800 and x < 0xE000 \
           else "%s"     % chr(x) if x >= 32 and x < 0x110000 \
           else "\\%s"   % x      


def r_enumerate(x):
    """Reverse enumeration."""
    return zip(reversed(range(len(x))), reversed(x))

def delete_if(the_list, condition):
    """Delete element from the list if and only if 'condition(element)' 
    returns True.
    """
    for i in range(len(the_list)-1, -1, -1):
        if condition(the_list[i]): del the_list[i]

def do_and_delete_if(the_list, do, result):
    """'do()' operates on each element of the list and the 'result'. If
    it returns 'True' the element is deleted from 'the_list'.
    """
    for i in range(len(the_list)-1, -1, -1):
        if do(the_list[i], result): del the_list[i]

def print_callstack(BaseNameF=False):
    try:
        i = 1
        name_list = []
        while 1 + 1 == 2:
            f = sys._getframe(i)
            x = f.f_code

            # Do not consider the frame coming from the @typed decorator,
            # (See 'def typed(**parameters)' below)
            if x.co_name != "modified": 
                name_list.append([x.co_filename, f.f_lineno, x.co_name])
            i += 1
    except:
        pass

    prev_file_name = ""
    i = - 1
    for x in reversed(name_list):
        if BaseNameF: 
            name = os.path.basename(x[0])
            i += 1
        else:         
            file_name = x[0][len(QUEX_PATH)+1:]
            if file_name != prev_file_name:
                name = file_name
                i += 1
            else:
                # base_name = os.path.basename(x[0])
                base_name = " " * len(os.path.basename(x[0]))
                name = " " * (len(file_name) - len(base_name)) + base_name
            prev_file_name = file_name
            
        print("%s%s:%s:%s(...)" % (" " * (i*4), name, x[1], x[2])) 

def pair_combinations(iterable):
    other = tuple(iterable)
    for i, x in enumerate(other):
        for y in islice(other, i+1, None):
            yield x, y

class E_Values(QuexEnum):
    UNASSIGNED = auto()
    VOID       = auto()
    DISABLED   = auto()
    SIGMA      = auto()
    RESTORE    = auto()
    
# 'SIGMA' is something that is always different. It will cause always the 
# content to become 'VOID', i.e. not uniform in UniformObject.

def concatinate(one_list, other_list):
    """RETURNS: The 'one_list' extended with 'other_list' in case that 
                'other_list' is not None.

       Both lists remain unchanged during the operation.
    """
    if other_list is not None: return one_list + other_list
    else:                      return one_list

def flatten(ListOfListsIterable):
    """The very fastest way to flatten a list of lists of objects into a list
    of objects.

    EXAMPLE: input:   [1, 2], [3, 4], [5, 6]
             output:  [1, 2, 3, 4, 5, 6]

    RETURNS: List of objects.
    """
    # The fastest method ever! 
    # Before changing this, please benchmark propperly!
    return functools.reduce(iconcat, ListOfListsIterable, [])

class UniformObject(object):
    __slots__ = ("_content", "_equal")
    def __init__(self, EqualCmp=lambda x,y: x==y, Initial=E_Values.UNASSIGNED):
        if isinstance(Initial, UniformObject):
            self._content = Initial._content
        else:
            self._content = Initial
        self._equal       = EqualCmp

    @staticmethod
    def from_iterable(Iterable, EqualCmp=lambda x,y: x==y):
        try:    initial = next(Iterable)
        except: return UniformObject(EqualCmp, Initial=E_Values.UNASSIGNED)

        result = UniformObject(EqualCmp, Initial=initial)
        for x in Iterable:
            result <<= x
            if result._content == E_Values.VOID: break
        return result

    @staticmethod
    def from_2(A, B, EqualCmp=lambda x,y: x==y):
        result = UniformObject(EqualCmp, Initial=A)
        result <<= B
        return result

    def clone(self):
        result = UniformObject(self._equal)
        result._content = self._content
        return result

    def __ilshift__(self, NewContent):
        if isinstance(NewContent, UniformObject):    
            NewContent = NewContent._content

        if   E_Values.UNASSIGNED == self._content:       self._content = NewContent
        elif E_Values.VOID       == self._content:       pass
        elif E_Values.VOID       == NewContent:          self._content = E_Values.VOID
        elif E_Values.SIGMA      == NewContent:          self._content = E_Values.VOID
        elif not self._equal(self._content, NewContent): self._content = E_Values.VOID
        return self

    def fit(self, NewContent):
        if isinstance(NewContent, UniformObject):    
            NewContent = NewContent._content

        if   E_Values.UNASSIGNED == self._content: return True
        elif E_Values.VOID       == self._content: return False
        
        return self._equal(self._content, NewContent)

    @property
    def content(self):
        if   E_Values.UNASSIGNED == self._content: return None
        elif E_Values.VOID       == self._content: return None
        else:                                      return self._content

    def is_uniform(self):
        """If the content is UNASSIGNED or remained uniform, then this
           function returns 'True'. It returns 'False' if two different
           values have been shifted into it.
        """
        return E_Values.VOID != self._content

def _report_failed_assertion(i, thing, last_things, iterable_next_things):
    L = len(last_things)
    for k, thing in enumerate(last_things):
        print("[%i](before) \"%s\"" % (i - L + k, thing))

    print(">> [%i] Error: '%s'" % (i, thing.__class__.__name__))
    print(">> [%i] Error: '%s'" % (i, thing))

    for k in range(10):
        try:   thing = next(iterable_next_things)
        except StopIteration: break
        print("[%i](after) \"%s\"" % (i + k + 1, thing))

def _check_all(Iterable, Condition):
    assert not isinstance(Iterable, (int, str))

    last_things = deque()
    if isinstance(Iterable, (tuple, list)): iterable = iter(Iterable)
    else:                                   iterable = Iterable
    i = -1
    while 1 + 1 == 2:
        i     += 1
        try:   thing = next(iterable)
        except StopIteration: break

        if len(last_things) > 10: last_things.popleft()
        last_things.append(thing)
        if Condition(thing): continue
        _report_failed_assertion(i, thing, last_things, iterable)
        return False
    return True

def _get_value_check_function(Type):
    """Tries possible operations on 'Type' and returns the operation which
    works without exception.
    """
    try:     
        if isinstance(4711, Type): pass
        return lambda value: isinstance(value, Type)
    except: 
        if not isinstance(Type, tuple):
            try: 
                if 4711 in Type: pass
                return lambda value: value in Type
            except:
                pass
        else:
            condition_array = tuple( 
                _get_value_check_function(alternative_type) 
                for alternative_type in Type
            )
            def is_ok(element):
                for condition in condition_array:
                    if condition(element): return True
                return False
            return is_ok
    return None

def all_isinstance(List, Type):
    if Type is None: return True
    is_ok = _get_value_check_function(Type) # 'Type' is coded in 'is_ok'
    assert is_ok is not None
    return _check_all(List, is_ok)

def none_isinstance(List, Type):
    if Type is None: return True
    is_ok = _get_value_check_function(Type) # 'Type' is coded in 'is_ok'
    assert is_ok is not None
    return _check_all(List, lambda element: not is_ok(element))

def none_is_None(Iterable):
    return not any(x is None for x in Iterable)

def typed(**_parameters_):
    """parameter=Type                   --> isinstance(parameter, Type)
                                            Type == None --> no requirements.
       parameter=(Type0, Type1, ...)    --> isinstance(parameter, (Type0, Type1, ...))
                                            TypeX == None means that parameter can be None
       parameter=[Type]                 --> (1) isinstance(parameter, list)
                                            (2) all_isinstance(parameter, Type)
       parameter=[(Type0, Type1, ...)]  --> (1) isinstance(parameter, list)
                                            (2) all_isinstance(parameter, (Type0, Type1, ...))
       parameter={Type0: Type1}         --> (1) isinstance(parameter, dict)
                                            (2) all_isinstance(parameter.keys(),   Type0)
                                            (3) all_isinstance(parameter.values(), Type1)
                                        (Here, Type0 or Type1 may be a tuple (TypeA, TypeB, ...)
                                         indicating alternative types.)
    """
    def name_type(TypeD):
        if isinstance(TypeD, tuple):
            return "[%s]" % "".join("%s, " % name_type(x) for x in TypeD)
        elif hasattr(TypeD, __name__):
            return "'%s'" % TypeD.__name__
        else:
            return str(TypeD)

    def error(Name, Value, TypeD):
        return "Parameter '%s' is a '%s'. Expected '%s'." \
               % (Name, Value.__class__.__name__, name_type(TypeD))

    def check_types(_func_, _parameters_ = _parameters_):
        def modified(*arg_values, **kw):
            arg_names = _func_.__code__.co_varnames
            kw.update(list(zip(arg_names, arg_values)))
            for name, type_d in _parameters_.items():
                if name not in kw:  # Default arguments may possibly not appear
                    continue
                value = kw[name]
                if type_d is None:  # No requirements on type_d
                    continue

                elif value is None:
                    assert type_d is None or (type(type_d) == tuple and None in type_d), \
                           error(name, value, type_d)

                elif type(type_d) == tuple:
                    if None in type_d: 
                        # 'None' is accepted as alternative. But, if value was 'None' it
                        # would have triggered the previous case. So, here filter it out.
                        type_d = tuple(set(x for x in type_d if x is not None))
                    assert isinstance(value, type_d), error(name, value, type_d)

                elif type(type_d) == list:
                    assert len(type_d) == 1
                    assert isinstance(value, list), error(name, value, type_d)
                    value_type = type_d[0]
                    assert all_isinstance(value, value_type), error(name, value, type_d)

                elif type(type_d) == dict:
                    assert len(type_d) == 1
                    assert isinstance(value, dict), error(name, value, type_d)
                    key_type, value_type = next(iter(type_d.items()))
                    assert all_isinstance(iter(value.keys()), key_type), \
                           "Dictionary '%s' contains key not of of '%s'" % (name, name_type(key_type))
                    assert all_isinstance(iter(value.values()), value_type), \
                           "Dictionary '%s' contains value not of of '%s'" % (name, name_type(value_type))
                else:
                    assert isinstance(value, type_d), \
                           error(name, value, type_d)
            return _func_(**kw)
        return modified
    return check_types

def iterator_N_on_M_slots(N,M):
    """YIELDS: array of size N,
               where 'array[i]' number of the slot occupied by object 'i'

    If 'cursor' (something that points to positions) is the yielded
    by this function, then the code fragment 

        slots = [ int(slot_index in choice) for slot_index in range(M) ]

    delivers the slot settings for a given combination.
    """
    assert M >= N
    for cursor in combinations(list(range(M)), N):
        yield cursor

def iterator_N_on_M_slots_multiple_occupancy(N,M):
    """YIELDS: array of size N,
               where 'array[i]' number of the slot occupied by object 'i'

    If 'cursor' (something that points to positions) is the yielded
    by this function, then the code fragment 

        slots = [ int(slot_index in choice) for slot_index in range(M) ]

    delivers the slot settings for a given combination.
    """
    assert M >= N
    for cursor in combinations(list(range(M+(N-1))), N):
        yield tuple(cursor[i]-i for i in range(N))

def iterator_N_slots_with_limit_indices(Limits):
    """YIELDS: See example below:

        Limits = [3,4,2] 

        => 1st slot counts: 0, 1, 2
           2nd slot counts: 0, 1, 2, 3
           3rd slot counts: 0, 1

    Delivers:

        [0, 0, 0] [1, 0, 0] [2, 0, 0] [0, 1, 0] [1, 1, 0] [2, 1, 0]
        [0, 2, 0] [1, 2, 0] [2, 2, 0] [0, 3, 0] [1, 3, 0] [2, 3, 0]
        [0, 0, 1] [1, 0, 1] [2, 0, 1] [0, 1, 1] [1, 1, 1] [2, 1, 1]
        [0, 2, 1] [1, 2, 1] [2, 2, 1] [0, 3, 1] [1, 3, 1] [2, 3, 1]
    """
    slot_n = len(Limits)
    cursor = [0] * slot_n
    i      = 0
    while 1 + 1 == 2:
        yield cursor
        i = 0
        cursor[i] += 1
        while cursor[i] >= Limits[i]:
            cursor[i] = 0
            i += 1
            if i >= slot_n: return
            cursor[i] += 1

def iterator_N_slots_with_setting_db(SettingDb):
    """Same as 'iterator_N_slots_with_limit_indices' only that indices
    are directly interpreted by SettingsDb.
    """
    limit_indices = [ len(setting_list) for setting_list in SettingDb ]
    for cursor in iterator_N_slots_with_limit_indices(limit_indices):
        yield tuple(
            setting_list[cursor[i]] for i, setting_list in enumerate(SettingDb)
        )


class TypedSet(set):
    def __init__(self, Cls):
        self.__element_class = Cls

    def add(self, X):
        assert isinstance(X, self.__element_class)
        set.add(self, X)

    def update(self, Iterable):
        for x in Iterable:
            assert isinstance(x, self.__element_class)
        set.update(self, Iterable)

class TypedDict(dict):
    def __init__(self, ClsKey=None, ClsValue=None):
        self.__key_class   = ClsKey
        self.__value_class = ClsValue

    def get(self, Key):
        assert self.__key_class is None or isinstance(Key, self.__key_class), \
               self._error_key(Key)
        return dict.get(self, Key)

    def __getitem__(self, Key):
        assert self.__key_class is None or isinstance(Key, self.__key_class), \
               self._error_key(Key)
        return dict.__getitem__(self, Key)

    def __setitem__(self, Key, Value):
        assert self.__key_class   is None or isinstance(Key, self.__key_class), \
               self._error_key(Key)
        assert self.__value_class is None or isinstance(Value, self.__value_class), \
               self._error_value(Value)
        return dict.__setitem__(self, Key, Value)

    def update(self, Iterable):
        # Need to iterate twice: 'list()' may be faster here then 'tee()'.
        if isinstance(Iterable, dict): iterable2 = iter(Iterable.items())
        else:                          Iterable = list(Iterable); iterable2 = iter(Iterable)

        for x in iterable2:
            assert isinstance(x, tuple)
            assert self.__key_class   is None or isinstance(x[0], self.__key_class), \
                   self._error_key(x[0])
            assert self.__value_class is None or isinstance(x[1], self.__value_class), \
                   self._error_value(x[1])

        dict.update(self, Iterable)

    def _error(self, ExpectedClass):
        return "TypedDict(%s, %s) expects %s" % \
                (self.__key_class.__name__, self.__value_class.__name__, \
                 ExpectedClass.__name__)

    def _error_key(self, Key):
        return "%s as a key. Found type='%s; value='%s';" % \
                (self._error(self.__key_class), Key.__class__.__name__, Key)

    def _error_value(self, Value):
        return "%s as value. Found '%s'" % \
                (self._error(self.__value_class), Value.__class__.__name__)


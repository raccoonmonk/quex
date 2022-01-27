# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from  collections            import namedtuple
from  quex.engine.misc.tools import typed
from  quex.constants         import E_AcceptanceCondition, \
                                    E_IncidenceIDs
from copy     import deepcopy
from operator import attrgetter

class AccepterContentElement(namedtuple("AccepterContentElement_tuple", ("acceptance_condition_set", "acceptance_id"))):
    """Objects of this class shall describe a check sequence such as

            if     ( pre_condition_5_f ) last_acceptance = 34;
            else if( pre_condition_7_f ) last_acceptance = 67;
            else if( pre_condition_9_f ) last_acceptance = 31;
            else                         last_acceptance = 11;

       by a list such as [(5, 34), (7, 67), (9, 31), (None, 11)]. Note, that
       the prioritization is not necessarily by acceptance_id. This is so, since
       the whole trace is considered and length precedes acceptance_id.
    
       The values for .acceptance_condition_set and .acceptance_id are carry the 
       following meaning:

       .acceptance_condition_set   AccConditionIDs of concern. 

                         is None --> no pre-context (normal pattern)
                         is -1   --> pre-context 'begin-of-line'
                         >= 0    --> id of the pre-context state machine/flag

       .acceptance_id    Terminal to be targeted (what was accepted).

                         is None --> acceptance determined by stored value in 
                                     'last_acceptance', thus "goto *last_acceptance;"
                         == -1   --> goto terminal 'failure', nothing matched.
                         >= 0    --> goto terminal given by '.terminal_id'

    """
    @typed(AccConditionSet=tuple)
    def __new__(self, AccConditionSet, AcceptanceID):
        return super(AccepterContentElement, self).__new__(self, AccConditionSet, AcceptanceID)

    def __str__(self):
        txt = []
        for acceptance_condition_id in self.acceptance_condition_set:
            txt.append("%s: accept = %s" % (repr_pre_context_id(acceptance_condition_id),
                                            repr_acceptance_id(self.acceptance_id)))
        return "".join(txt)

class AccepterContent:
    """_________________________________________________________________________

    A list of conditional pattern acceptance actions. It corresponds to a 
    sequence of if-else statements such as 

          [0]  if   pre_condition_4711_f: acceptance = Pattern32
          [1]  elif pre_condition_512_f:  acceptance = Pattern21
          [2]  else:                      acceptance = Pattern56
    
    Requires: AccepterContentElement (see above) which stores the elements
              of the list.

    An element in the sorted list of test/accept commands.  It contains the
    'acceptance_condition_id' of the condition to be checked and the 'acceptance_id' to
    be accepted if the condition is true.
    ___________________________________________________________________________
    """

    def __init__(self):
        self.__list = []

    @staticmethod
    def from_iterable(AccConditionSet_AcceptanceId_Iterable):
        result = AccepterContent()
        result.absorb(AccConditionSet_AcceptanceId_Iterable)
        return result

    def absorb(self, AccConditionSet_AcceptanceId_Iterable):
        assert not self.__list

        def unconditional_acceptance(acceptance_condition_set, acceptance_id):
            return not acceptance_condition_set and acceptance_id != E_IncidenceIDs.MATCH_FAILURE

        for acceptance_condition_set, acceptance_id in AccConditionSet_AcceptanceId_Iterable:
            self.__list.append(AccepterContentElement(acceptance_condition_set, acceptance_id))
            if unconditional_acceptance(acceptance_condition_set, acceptance_id): 
                break

    def clone(self):
        result = AccepterContent()
        result.__list = [ deepcopy(x) for x in self.__list ]
        return result
    
    @typed(AccConditionSet=tuple)
    def add(self, AccConditionSet, AcceptanceID):
        self.__list.append(AccepterContentElement(AccConditionSet, AcceptanceID))

    def clean_up(self):
        """Ensure that nothing follows and unconditional acceptance."""
        self.__list.sort(key=attrgetter("acceptance_id"))
        for i, x in enumerate(self.__list):
            if not x.acceptance_condition_set:
                break
        if i != len(self.__list) - 1:
            del self.__list[i+1:]

    def has_acceptance_without_pre_context(self):
        for x in self.__list:
            if not x.acceptance_condition_set: return True
        return False

    def get_pretty_string(self):
        txt    = []
        if_str = "if     "
        for x in self.__list:
            if x.acceptance_condition_set:
                for acceptance_condition_id in x.acceptance_condition_set:
                    txt.append("%s %s: " % (if_str, repr_pre_context_id(acceptance_condition_id)))
                    if_str = "else if"
            else:
                if if_str == "else if": txt.append("else: ")
            txt.append("last_acceptance = %s\n" % repr_acceptance_id(x.acceptance_id))
            if_str = "else if"
        return txt

    # Require '__hash__' and '__eq__' to be element of a set.
    def __hash__(self): 
        xor_sum = 0
        for x in self.__list:
            if isinstance(x.acceptance_id, int): xor_sum ^= x.acceptance_id
        return xor_sum

    def __eq__(self, Other):
        if   not isinstance(Other, AccepterContent):    return False
        elif len(self.__list) != len(Other.__list):     return False

        for x, y in zip(self.__list, Other.__list):
            if   x.acceptance_condition_set != y.acceptance_condition_set: return False
            elif x.acceptance_id            != y.acceptance_id:            return False

        return True

    def __ne__(self, Other):
        return not (self == Other)

    def __iter__(self):
        for x in self.__list:
            yield x

    def __str__(self):
        def to_string(X, FirstF):
            acc_str = "last_acceptance = %s" % repr_acceptance_id(X.acceptance_id)
            if not X.acceptance_condition_set:
                return acc_str

            cond_str = ""
            for acceptance_condition_id in X.acceptance_condition_set:
                cond_str += "%s" % repr_pre_context_id(acceptance_condition_id)
            if FirstF:
                return "if %s:  %s" % (cond_str, acc_str)
            else:
                return "else if %s:  %s" % (cond_str, acc_str)

        last_i = len(self.__list) - 1
        return "".join("%s%s" % (to_string(element, i==0), "\n" if i != last_i else "") 
                       for i, element in enumerate(self.__list))

    def __len__(self):
        return len(self.__list)
    
def repr_pre_context_id(Value):
    if   Value is None:                                  return "Always"
    elif Value == E_AcceptanceCondition.BEGIN_OF_LINE:   return "BeginOfLine"
    elif Value == E_AcceptanceCondition.BEGIN_OF_STREAM: return "BeginOfStream"
    elif Value >= 0:                               return "PreContext_%i" % Value
    else:                                          assert False

def repr_acceptance_id(Value, PatternStrF=True):
    if   Value == E_IncidenceIDs.VOID:          return "last_acceptance"
    elif Value == E_IncidenceIDs.MATCH_FAILURE: return "Failure"
    elif Value == E_IncidenceIDs.BAD_LEXATOM:   return "Bad Lexatom"
    elif Value >= 0:                                    
        if PatternStrF:                         return "Pattern%i" % Value
        else:                                   return "%i" % Value
    else:                                       assert False

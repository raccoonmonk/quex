# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.engine.misc.tools               import typed
from quex.engine.misc.quex_enum           import QuexEnum
from quex.engine.operations.se_operations import SeOp, \
                                                 SeAccept, \
                                                 SeStoreInputPosition
from quex.constants  import E_AcceptanceCondition, \
                            E_IncidenceIDs
from functools import reduce



class SingleEntry(object):
    __slots__ = ('__list')

    def __init__(self, CloneF=False):
        if not CloneF: self.__list = []

    @staticmethod
    def from_iterable(Iterable):
        result = SingleEntry()
        result.set(Iterable)
        return result

    def clone(self, ReplDbPreContext=None, ReplDbAcceptance=None):
        return SingleEntry.from_iterable(
            x.clone(ReplDbPreContext=ReplDbPreContext,
                    ReplDbAcceptance=ReplDbAcceptance) 
            for x in self.__list)

    def find(self, OpClass):
        for cmd in self.__list:
            if cmd.__class__ == OpClass: return cmd
        return None

    def get_iterable(self, OpClass, Start=0):
        for cmd in self.__list[Start:]:
            if cmd.__class__ == OpClass: yield cmd

    def get_enumerated_iterable(self, OpClass, Start=0):
        for i, cmd in enumerate(self.__list[Start:0]):
            if cmd.__class__ == OpClass: yield i, cmd
        
    def has(self, Op):
        for candidate in self.__list:
            if candidate == Op: return True
        return False

    @typed(Op=SeOp)
    def add(self, Op):
        if self.has(Op): return
        self.__list.append(Op.clone())

    def add_Op(self, OpClass):
        cmd = self.find(OpClass)
        if cmd is not None: return
        self.add(OpClass())

    def merge(self, Other):
        assert isinstance(Other, SingleEntry)
        self.__list.extend(
            cmd.clone() for cmd in Other.__list if not self.has(cmd)
        )

    def merge_list(self, OpIterableIterable):
        for origin_iterable in OpIterableIterable:
            self.merge(origin_iterable)

    def get_highest_precedence_acceptance_id(self):
        """RETURNS: incidence_id of the highest non-E_IncidenceIDs pattern
                                 that matches in this state.
                    None, else.
        """
        dominating_iid = None
        for cmd in self.get_iterable(SeAccept):
            if   cmd.acceptance_id() in E_IncidenceIDs: 
                continue
            elif dominating_iid is None or dominating_iid > cmd.acceptance_id():
                dominating_iid = cmd.acceptance_id()
        return dominating_iid

    def set(self, OpList):
        self.clear()
        self.__list.extend(
            cmd.clone() for cmd in OpList if not self.has(cmd)
        )
        
    def remove_Op(self, OpClass):
        L = len(self.__list)
        for i in range(L-1, -1, -1):
            cmd = self.__list[i]
            if cmd.__class__ == OpClass: del self.__list[i]

    def has_acceptance_id(self, AcceptanceID):
        return any(cmd.acceptance_id() == AcceptanceID
                   for cmd in self.get_iterable(SeAccept))

    def has_specific_acceptance_id(self):
        return any(cmd.acceptance_id_is_specific()
                   for cmd in self.get_iterable(SeAccept))

    def has_pre_context_begin_of_line(self):
        return any(
            E_AcceptanceCondition.BEGIN_OF_LINE in cmd.acceptance_condition_set() 
            for cmd in self.get_iterable(SeAccept)
        )

    def has_pre_context_begin_of_stream(self):
        # 'begin of line' includes 'begin of stream'.
        if self.has_acceptance_condition(E_AcceptanceCondition.BEGIN_OF_LINE): return True

        return any(
            E_AcceptanceCondition.BEGIN_OF_STREAM in cmd.acceptance_condition_set() 
            for cmd in self.get_iterable(SeAccept)
        )

    def clear(self):
        del self.__list[:]

    def delete_dominated(self):
        """Simplification to make Hopcroft Minimization more efficient. The
        first unconditional acceptance makes any lower prioritized acceptances
        meaningless. 
        """
        # Find the first unconditional acceptance
        unconditional_acceptance_i = None
        for i, cmd in self.get_enumerated_iterable(SeAccept):
            if cmd.acceptance_condition_set(): # What is this? <fschaef 17y08m>
                unconditional_acceptance_i = i
                break

        if unconditional_acceptance_i is None:
            return

        # There MUST be at least one unconditional 'SeAccept' 
        # => min() not on empty set
        min_acceptance_id = min(
            cmd.acceptance_id()
            for cmd in self.get_iterable(SeAccept, Start=unconditional_acceptance_i)
        )

        # Delete any SeAccept command where '.acceptance_id() > min_acceptance_id'
        #
        for i, cmd in self.get_enumerated_iterable(SeAccept, Start=unconditional_acceptance_i):
            if cmd.__class__ == SeAccept and cmd.acceptance_id() > min_acceptance_id:
                del self.__list[i]

    def hopcroft_combinability_key(self):
        """Two states have the same hopcroft-combinability key, if and only if
        they are combinable during the initial state split in the hopcroft
        minimization. Criteria:
        
        (1) Acceptance states of a different acceptance schemes. The
            decision making about the winning pattern must be the same for all
            states of a state set that is possibly combined into one single
            state. 
        
            In particular, non-acceptance states can never be combined with
            acceptance states.
        
        (2) Two states of the same pattern where one stores the input position
            and the other not, cannot be combined. Otherwise, the input
            position would be stored in unexpected situations.

        The approach is the following: For each investigated behavior a a tuple
        of numbers can be derived that describes it uniquely. The tuple of all
        tuples is used during the hopcroft minimization to distinguish between
        combinable states and those that are not.
        """
        # Before the track analysis, the acceptance in a state is simple
        # given by its precedence, i.e. its acceptance id. Thus, the sorted
        # sequence of acceptance ids identifies the acceptance behavior.
        acceptance_info = tuple(sorted((x.acceptance_id() for x in self.get_iterable(SeAccept)), 
                                       key=QuexEnum.general_key))

        # The storing of input positions in registers is independent of its
        # position in the command list (as long as it all happens before the increment
        # of the input pointer, of course).
        #
        # The sorted list of position storage registers where positions are stored
        # is a distinct description of the position storing behavior.
        store_info = tuple(sorted(x.acceptance_id() 
                                  for x in self.get_iterable(SeStoreInputPosition)))

        result = (acceptance_info, store_info)
        return result

    def get_string(self, OpalStatesF=True):
        if   not self.__list:       return "\n"
        elif len(self.__list) == 1: return "%s\n" % self.__list[0]

        def key(X):
            if   X.__class__ == SeAccept:              
                acc_condition_str = ", ".join("%s" % ac for ac in X.acceptance_condition_set())
                return (0, X.acceptance_id(), acc_condition_str, X.restore_position_register_f())
            elif X.__class__ == SeStoreInputPosition: 
                return (1, X.acceptance_id())
            else:
                assert False

        return "%s\n" % reduce(lambda x, y: "%s, %s" % (x, y), sorted(self.__list, key=key))

    def __iter__(self):
        for x in self.__list:
            yield x

    def __len__(self):
        return len(self.__list)

    def is_equal(self, Other):
        if len(self.__list) != len(Other.__list): return False
        return all(op_x == op_y 
                   for op_x, op_y in zip(self.__list, Other.__list))


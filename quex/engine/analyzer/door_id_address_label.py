# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.state_machine.index  as     sm_index
from   quex.engine.misc.tools           import print_callstack, \
                                               TypedSet
from   quex.blackboard import Lng
from   quex.constants  import E_IncidenceIDs, \
                              E_StateIndices, \
                              E_DoorIdIndex
from   collections import namedtuple
import itertools 

#______________________________________________________________________________
#
# Address:
#
# Numeric representation of a 'goto target'. Using an address a variable may 
# contain the information of what target to go, and the goto is then executed 
# by a code fragment as
#
#      switch( address_variable ) {
#         ...
#         case 0x4711:  goto _4711;
#         ...
#      }
#______________________________________________________________________________
#
# TransitionID:
#
# Identifies a transition from one source to target state.  There may be
# multiple transitions for the same source-target pair. Each one identified by
# an additional 'trigger_id'.  TransitionIDs are connected with OpList-s
# at entry into a state; But 
#
#                               n          1
#               TransitionID  <--------------> OpList
#
# That is, there may be multiple TransitionID-s with the same OpList.
# TransitionID-s are useful during the construction of entries.
#______________________________________________________________________________


#______________________________________________________________________________
#
# DoorID:
#
# Marks an entrance into a 'Processor', an FSM_State for example.  A
# Processor can have multiple entries, each entry has a different DoorID. A
# DoorID identifies distinctly a OpList to be executed upon entry.
# No two OpList-s
# are the same except that their DoorID is the same.
#            
#______________________________________________________________________________
class DoorID(namedtuple("DoorID_tuple", ("state_index", "door_index", "related_address"))):
    def __new__(self, StateIndex, DoorIndex, dial_db=None):
        assert isinstance(StateIndex, int) or StateIndex in E_StateIndices or StateIndex == E_IncidenceIDs.MATCH_FAILURE
        assert isinstance(dial_db, DialDB)
        # 'DoorIndex is None' --> right after the entry commands (targetted after reload).
        assert isinstance(DoorIndex, int)  or DoorIndex is None or DoorIndex in E_DoorIdIndex, "%s" % DoorIndex

        # If the DoorID object already exists, than do not generate a second one.
        result = dial_db.find_door_id(StateIndex, DoorIndex)

        if result is not None: return result

        # Any created DoorID must be properly registered.
        address = dial_db.new_address()
        result  = super(DoorID, self).__new__(self, StateIndex, DoorIndex, address)
        dial_db.register_door_id(result)

        return result

    @staticmethod
    def drop_out(StateIndex, dial_db):            return DoorID(E_StateIndices.DROP_OUT, StateIndex, dial_db=dial_db)
    @staticmethod                        
    def transition_block(StateIndex, dial_db):    return DoorID(StateIndex, E_DoorIdIndex.TRANSITION_BLOCK, dial_db=dial_db)
    @staticmethod                        
    def incidence(IncidenceId, dial_db):          return DoorID(dial_db.map_incidence_id_to_state_index(IncidenceId), 
                                                                E_DoorIdIndex.ACCEPTANCE, dial_db=dial_db)
    @staticmethod                        
    def bipd_return(IncidenceId, dial_db):        return DoorID(dial_db.map_incidence_id_to_state_index(IncidenceId), E_DoorIdIndex.BIPD_RETURN, dial_db=dial_db)
    @staticmethod                        
    def state_machine_entry(SM_Id, dial_db):      return DoorID(SM_Id,      E_DoorIdIndex.STATE_MACHINE_ENTRY, dial_db=dial_db)
    @staticmethod                        
    def global_state_router(dial_db):             return DoorID(0,         E_DoorIdIndex.GLOBAL_STATE_ROUTER, dial_db=dial_db)
    @staticmethod                         
    def global_end_of_pre_context_check(dial_db): return DoorID(0,         E_DoorIdIndex.GLOBAL_END_OF_PRE_CONTEXT_CHECK, dial_db=dial_db)
    @staticmethod
    def global_reentry(dial_db):                  return DoorID(0,         E_DoorIdIndex.GLOBAL_REENTRY, dial_db=dial_db)
    @staticmethod
    def return_with_on_after_match(dial_db):      return DoorID(0,         E_DoorIdIndex.RETURN_WITH_ON_AFTER_MATCH, dial_db=dial_db)
    @staticmethod
    def continue_with_on_after_match(dial_db):    return DoorID(0,         E_DoorIdIndex.CONTINUE_WITH_ON_AFTER_MATCH, dial_db=dial_db)
    @staticmethod
    def continue_without_on_after_match(dial_db): return DoorID(0,         E_DoorIdIndex.CONTINUE_WITHOUT_ON_AFTER_MATCH, dial_db=dial_db)

    def drop_out_f(self):                  return self.state_index == E_StateIndices.DROP_OUT
    def last_acceptance_f(self):           return     self.door_index  == E_DoorIdIndex.ACCEPTANCE \
                                                  and self.state_index == E_IncidenceIDs.VOID

    def __repr__(self):
        return "DoorID(s=%s, d=%s)" % (self.state_index, self.door_index)

#______________________________________________________________________________
# DialDB: DoorID, Address - Database
#
# A DoorID of a state entry is distincly linked to an 'address', i.e something
# a 'goto' can go to. The language's dictionary later relates an 'address' to
# a 'label' (i.e. something that the language uses as target of 'goto').
#
#                           1     n          1       1
#               StateIndex <-------> DoorID <---------> Address
#
#              '---------------------._.-----------------------'
#                                     '
#                                   DialDB
#
# The DialDB maps from DoorID to Address and vice versa. Additionally, it 
# keeps track of 'goto-ed' addresses. Thus, addresses that are never goto-ed,
# may not have to be instantiated.
#______________________________________________________________________________


# Globally Unique Incidence Id ________________________________________________
#
# (For ease: make it globally unique, not only mode-unique)
#
def new_incidence_id():
    """Incidence ids are used as DFA-ids => they MUST be aligned.
    TODO: They are actually the same. 
          Replace 'state_machine_id' by 'incidence_id'.
    """
    return sm_index.get_state_machine_id()

class DialDB(object):
    __slots__ = ("__door_id_db", "__gotoed_address_set", "__routed_address_set", "__map_incidence_id_to_state_index", "__debug")

    # Address counter to generate globally unique address
    __address_i = itertools.count(start=0)

    def __init__(self):
        # Track all generated DoorID objects with 2d-dictionary that maps:
        #
        #          StateIndex --> ( DoorSubIndex --> DoorID )
        #
        # Where the DoorID has the 'state_index' and 'door_index' equal to
        # 'StateIndex' and 'DoorSubIndex'.
        #
        self.__door_id_db = {} # TypedDict(long, dict)
       
        # Track addresses which are subject to 'goto' and those which need to
        # be routed.
        self.__gotoed_address_set = TypedSet(int)
        self.__routed_address_set = TypedSet(int)

        # Mapping from incidence_id to terminal state index
        self.__map_incidence_id_to_state_index = {}

        # Monitoring the address generation for debug purposes
        # self.__debug = DialDb_DebugOutput(self, [2L, 27L, 28L])
        self.__debug = None

    def address_is_gotoed(self, Adr):
        if self.__debug: self.__debug.query_if_address_is_gotoed(Adr, Adr in self.__gotoed_address_set)
        return Adr in self.__gotoed_address_set

    def new_door_id(self, StateIndex=None):
        """Create a new entry in the database. First, a DoorID is generated.
        Then a new address is linked to it. A list of existing
        DoorID-s is maintained in '.__door_id_db'.

        RETURNS: New DoorID
        """
        state_index    = StateIndex if StateIndex is not None \
                                    else sm_index.get()
        door_sub_index = self.max_door_sub_index(state_index) + 1

        assert self.find_door_id(state_index, door_sub_index) is None
        return DoorID(state_index, door_sub_index, dial_db=self)

    def new_address(self):
        return int(next(self.__address_i))

    def max_door_sub_index(self, StateIndex):
        """RETURN: The greatest door sub index for a given StateIndex. 
                   '-1' if not index has been used yet.
        """
        result = - 1
        sub_db = self.__door_id_db.get(StateIndex)
        if sub_db is None: return result

        for dsi in (x for x in sub_db.keys() if isinstance(x, int)):
            if dsi > result: result = dsi
        return result

    def register_door_id(self, DoorId):
        if self.__debug: self.__debug.address_generation(DoorId, DoorId.related_address)

        sub_db = self.__door_id_db.get(DoorId.state_index)
        if sub_db is None:
            sub_db = {}
            self.__door_id_db[DoorId.state_index] = sub_db

        assert DoorId.door_index not in sub_db # Otherwise, it would not be new
        sub_db[DoorId.door_index] = DoorId

    def find_door_id(self, StateIndex, DoorSubIndex):
        """Try to get a DoorID from the set of existing DoorID-s. If a DoorID
        with 'StateIndex' and 'DoorSubIndex' does not exist yet, then create it.
        """
        sub_db = self.__door_id_db.get(StateIndex)
        if sub_db is None: return None
        door_id = sub_db.get(DoorSubIndex)
        if door_id is None: return None
        return door_id

    def mark_address_as_gotoed(self, Address):
        if self.__debug: self.__debug.address_is_gotoed(Address)
        self.__gotoed_address_set.add(Address)

    def mark_address_as_routed(self, Address):
        self.__routed_address_set.add(Address)
        # Any address which is subject to routing is 'gotoed', at least inside
        # the router (e.g. "switch( ... ) ... case AdrX: goto LabelX; ...").
        self.mark_address_as_gotoed(Address)

    def map_incidence_id_to_state_index(self, IncidenceId):
        assert    isinstance(IncidenceId, int) \
               or IncidenceId in E_IncidenceIDs, \
               "Found <%s>" % IncidenceId

        index = self.__map_incidence_id_to_state_index.get(IncidenceId)
        if index is None:
            index = sm_index.get()
            self.__map_incidence_id_to_state_index[IncidenceId] = index

        return index

    def routed_address_set(self):
        return self.__routed_address_set

class DialDb_DebugOutput:
    def __init__(self, related_dial_db, SuspectAdrList):
        self._address_set = set(SuspectAdrList)
        self._dial_db_id  = id(related_dial_db)
        print("CONTRUCTED(%li):" % self._dial_db_id)
        print_callstack()

    def address_generation(self, DoorId, Address):
        """Prints the callstack if an address of SuspectAdrList is generated.
        """
        if Address not in self._address_set: return
        print("#GENERATED(%li): DoorID %s <-> Address %s" % (self._dial_db_id, DoorId, Address))
        print_callstack()

    def address_is_gotoed(self, Address):
        """Prints the callstack if an address of SuspectAdrList is generated.
        """
        if Address not in self._address_set: return
        print("#GOTOED(%li): Address %s" % (self._dial_db_id, Address))
        print_callstack()

    def query_if_address_is_gotoed(self, Address, VerdictF):
        """Prints the callstack if an address of SuspectAdrList is generated.
        """
        if Address not in self._address_set: return
        print("#QUERY IF GOTOED(%li): Address %s (%s)" % (self._dial_db_id, Address, VerdictF))
        print_callstack()

class DoorID_Scheme(tuple):
    """A TargetByStateKey maps from a index, i.e. a state_key to a particular
       target (e.g. a DoorID). It is implemented as a tuple which can be 
       identified by the class 'TargetByStateKey'.
    """
    def __new__(self, DoorID_List):
        return tuple.__new__(self, DoorID_List)

    @staticmethod
    def concatinate(This, That):
        door_id_list = list(This)
        door_id_list.extend(list(That))
        return DoorID_Scheme(door_id_list)

__routed_address_set = set([]) # TODO: Delete and test

class IfDoorIdReferencedCode:
    def __init__(self, DoorId, Code=None, dial_db=None):
        """LabelType, LabelTypeArg --> used to access __address_db.

           Code  = Code that is to be generated, supposed that the 
                   address is actually referred (by goto).
                   (May be empty, so that that only the address is not printed.)
        """
        assert isinstance(Code, list) or Code is None

        self.address = DoorId.related_address
        self.door_id = DoorId
        if Code is None: self.code = [ Lng.LABEL(self.door_id) ]
        else:            self.code = Code

class IfDoorIdReferencedLabel(IfDoorIdReferencedCode):
    def __init__(self, DoorId, dial_db):
        IfDoorIdReferencedCode.__init__(self, DoorId, dial_db=dial_db)

def get_plain_strings(txt_list, dial_db):
    """-- Replaces unreferenced 'CodeIfLabelReferenced' objects by empty strings.
       -- Replaces integers by indentation, i.e. '1' = 4 spaces.
    """

    size = len(txt_list)
    i    = -1
    while i < size - 1:
        i += 1

        elm = txt_list[i]

        if type(elm) in [int, int]:    
            # Indentation: elm = number of indentations
            txt_list[i] = "    " * elm

        elif not isinstance(elm, IfDoorIdReferencedCode): 
            # Text is left as it is
            pass

        elif dial_db.address_is_gotoed(elm.address): 
            # If an address is referenced, the correspondent code is inserted.
            txt_list[i:i+1] = elm.code
            # txt_list = txt_list[:i] + elm.code + txt_list[i+1:]
            size += len(elm.code) - 1
            i    -= 1
        else:
            # If an address is not referenced, the it is replaced by an empty string
            txt_list[i] = ""

    return txt_list

def __nice(SM_ID): 
    assert isinstance(SM_ID, int)
    return repr(SM_ID).replace("L", "").replace("'", "")
    

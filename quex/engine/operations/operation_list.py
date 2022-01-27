# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# MAIN CLASSES:
#
# (*) Op:
#
#     .id      -- identifies the command (from E_Op)
#     .content -- 'Arguments' and/or additional information
#                 (Normally a tuple, 'AccepterContent' is a real class).
#  
# (*) CommandFactory:
#
#     Contains the database of all available commands. The '.do()' member
#     function can generate a command based on a set of arguments and 
#     the command's identifier.
#
#     CommandInfo:
#
#     Tells about the attributes of each command, i.e. its 'cost', its access
#     type (read/write/none) a constructor for the class of the '.content'
#     member.
#
#     CommandFactory.db:
#
#               Op identifier ----> CommandInfo
#
#     Maps from a command identifier (see E_Op) to a CommandInfo. The
#     CommandInfo is used to create a Op.
#
# (*) OpList:
#
#     A class which represents a sequence of Op-s. 
#
#     'command.shared_tail.get(A, B)' find shared Op-s in 'A' and 'B'.
#
#     This 'shared tail' is used for the 'door tree construction'. That is, 
#     upon entry into a state the OpList-s may different dependent on
#     the source state, but some shared commands may be the same. Those
#     shared commands are then only implemented once and not for each source
#     state separately.
#______________________________________________________________________________
#
# EXPLANATION:
#
# Op-s represent operations such as 'Accept X if Pre-Context Y fulfilled'
# or 'Store Input Position in Position Register X'. They are used to control
# basic operations of the pattern matching state machine.
#
# A command is generated by the CommandFactory's '.do(id, parameters)'
# function. For clarity, dedicated functions may be used, do provide a more
# beautiful call to the factory, for example:
#
#     cmd = Op.StoreInputPosition(AccConditionID, PositionRegister, Offset)
#
# is equivalent to
#
#     cmd = CommandFactory.do(E_Op.StoreInputPosition, 
#                             (AccConditionID, PositionRegister, Offset))
#
# where, undoubtedly the first is much easier to read. 
#
# ADAPTATION:
#
# The list of commands is given by 'E_Op' and the CommandFactory's '.db' 
# member. That is, to add a new command requires an identifier in E_Op,
# and an entry in the CommandFactory's '.db' which associates the identifier
# with a CommandInfo. Additionally, the call to the CommandFactory may be 
# abbreviated by a dedicated function as in the example above.
#______________________________________________________________________________
#
# (C) Frank-Rene Schaefer
#______________________________________________________________________________
from   quex.engine.operations.content_router_on_state_key import RouterOnStateKeyContent
from   quex.engine.operations.content_accepter            import AccepterContent, \
                                                                 repr_pre_context_id
from   quex.engine.operations.content_terminal_router     import RouterContent, \
                                                                 repr_position_register
from   quex.engine.misc.tools import delete_if, typed
from   quex.constants import E_Op, \
                             E_R

from   collections import namedtuple
import numbers

class Op(namedtuple("Op_tuple", ("id", "content", "my_hash", "branch_f"))):
    """_________________________________________________________________________
    Information about an operation to be executed. It consists mainly of a 
    command identifier (from E_Op) and the content which specifies the command 
    further.
    ____________________________________________________________________________
    """
    # Commands which shall appear only once in a command list:
    unique_set     = (E_Op.TemplateStateKeySet, 
                      E_Op.PathIteratorSet)

    # Fly weight pattern: Immutable objects need to exist only once. Every 
    # other 'new operation' may refer to the existing object. 
    #
    # Not all commands are immutable!
    #
    # Distinguish between commands that are fly weight candidates by the set 
    # of fly-weight-able command identifier. Use a positive list, NOT a negative
    # list. That way, new additions do not enter accidently into the fly weight
    # set.
    fly_weight_set = (E_Op.InputPDereference,)
    fly_weight_db  = {}

    def __new__(self, Id, *ParameterList):
        global _content_db
        global _access_db
        # Fly weight pattern: immutable objects instantiated only once.
        if Id in self.fly_weight_db: return self.fly_weight_db[Id]
        
        content_type = _content_db[Id]
        if content_type is None:
            # No content
            content = None
        elif ParameterList:
            content = self._instantiate_parameter_list(content_type, ParameterList)
        else:
            # Use 'real' constructor
            content = content_type() 

        hash_value = hash(Id) ^ hash(content)
        
        # -- determine whether command is subject to 'goto/branching'
        branch_f = Id in _brancher_set

        result = super(Op, self).__new__(self, Id, content, hash_value, branch_f)

        # Store fly-weight-able objects in database.
        if Id in self.fly_weight_set: self.fly_weight_db[Id] = result
        return result

    def clone(self):         
        # If the fly weight object exists, it must be in the database.
        if self.id in self.fly_weight_db:    
            return self
        elif hasattr(self.content, "clone"): 
            content = self.content.clone()
        else:                                
            # Clone the namedtuple object
            content = self._instantiate_parameter_list(self.content.__class__, 
                                                       [p for p in self.content])
        return super(Op, self).__new__(self.__class__, self.id, content, self.my_hash, self.branch_f)

    @staticmethod
    def _instantiate_parameter_list(ContentType, ValueIterable):
        # A tuple that describes the usage of the 'namedtuple' constructor.
        L = len(ValueIterable)
        assert L != 0
        if   L == 1: return ContentType(ValueIterable[0])
        elif L == 2: return ContentType(ValueIterable[0], ValueIterable[1])
        elif L == 3: return ContentType(ValueIterable[0], ValueIterable[1], ValueIterable[2])
        elif L == 4: return ContentType(ValueIterable[0], ValueIterable[1], ValueIterable[2], ValueIterable[3])
        else:        assert False

    @staticmethod
    @typed(AccConditionSet=tuple)
    def StoreInputPosition(AccConditionSet, PositionRegister, Offset):
        return Op(E_Op.StoreInputPosition, AccConditionSet, PositionRegister, Offset)
    
    @staticmethod
    @typed(AccConditionID=int)
    def PreContextOK(AccConditionID):
        # 'PreContextOK' can only take one acceptance_condtion_id
        return Op(E_Op.PreContextOK, AccConditionID)
    
    @staticmethod
    def TemplateStateKeySet(StateKey):
        return Op(E_Op.TemplateStateKeySet, StateKey)
    
    @staticmethod
    def PathIteratorSet(PathWalkerID, PathID, Offset):
        return Op(E_Op.PathIteratorSet, PathWalkerID, PathID, Offset)
    
    @staticmethod
    def PrepareAfterReload(OnSuccessDoorId, OnFailureDoorId):
        return Op(E_Op.PrepareAfterReload, OnSuccessDoorId, OnFailureDoorId)
    
    @staticmethod
    def Increment(Register):
        return Op(E_Op.Increment, Register)
    
    @staticmethod
    def Decrement(Register):
        return Op(E_Op.Decrement, Register)
    
    @staticmethod
    def InputPDereference():
        return Op(E_Op.InputPDereference)
    
    @staticmethod
    def LexemeResetTerminatingZero():
        return Op(E_Op.LexemeResetTerminatingZero)
    
    @staticmethod
    def ColumnCountReferencePSet(Pointer, Offset=0):
        return Op(E_Op.ColumnCountReferencePSet, Pointer, Offset)
    
    @staticmethod
    def ColumnCountReferencePDeltaAdd(Pointer, ColumnNPerChunk, SubtractOneF):
        return Op(E_Op.ColumnCountReferencePDeltaAdd, Pointer, ColumnNPerChunk, SubtractOneF)
    
    @staticmethod
    def ColumnCountAdd(Value, Factor=1):
        return Op(E_Op.ColumnCountAdd, Value, Factor)
    
    @staticmethod
    def IndentationHandlerCall(ModeName):
        return Op(E_Op.IndentationHandlerCall, ModeName)
    
    @staticmethod
    def IndentationBadHandlerCall(ModeName):
        return Op(E_Op.IndentationBadHandlerCall, ModeName)
    
    @staticmethod
    @typed(AccConditionSet=tuple)
    def IfAcceptanceConditionSetPositionAndGoto(AccConditionSet, RouterElement):
        #if AccConditionSet empty and RouterElement.positioning == 0:
        #    return GotoDoorId(DoorID.incidence(RouterElement.acceptance_id))
            
        return Op(E_Op.IfAcceptanceConditionSetPositionAndGoto, AccConditionSet, RouterElement)
    
    @staticmethod
    def ColumnCountGridAdd(GridSize, StepN=1):
        return Op(E_Op.ColumnCountGridAdd, GridSize, StepN)
    
    @staticmethod
    def LineCountAdd(Value, Factor=1):
        return Op(E_Op.LineCountAdd, Value, Factor)
    
    @staticmethod
    def GotoDoorId(DoorId):
        return Op(E_Op.GotoDoorId, DoorId)
    
    @staticmethod
    def ReturnFromLexicalAnalysis():
        return Op(E_Op.ReturnFromLexicalAnalysis)
    
    @staticmethod
    def GotoDoorIdIfCounterEqualZero(DoorId):
        return Op(E_Op.GotoDoorIdIfCounterEqualZero, DoorId)

    @staticmethod
    def GotoDoorIdIfInputPNotEqualPointer(DoorId, Pointer):
        return Op(E_Op.GotoDoorIdIfInputPNotEqualPointer, DoorId, Pointer)
    
    @staticmethod
    def GotoDoorIdIfInputPEqualPointer(DoorId, Pointer):
        return Op(E_Op.GotoDoorIdIfInputPEqualPointer, DoorId, Pointer)
    
    @staticmethod
    def Assign(TargetRegister, SourceRegister, Condition=None):
        return Op(E_Op.Assign, TargetRegister, SourceRegister, Condition)
    
    @staticmethod
    def AssignPointerDifference(RegisterResult, RegisterBig, RegisterSmall):
        return Op(E_Op.AssignPointerDifference, RegisterResult, RegisterBig, RegisterSmall)
    
    @staticmethod
    def PointerAssignMin(RegisterResult, PointerA, PointerB, Condition=None):
        return Op(E_Op.PointerAssignMin, RegisterResult, PointerA, PointerB, Condition)

    @staticmethod
    def PointerAdd(RegisterResult, RegisterDelta, Condition=None):
        return Op(E_Op.PointerAdd, RegisterResult, RegisterDelta, Condition)
    
    @staticmethod
    def AssignConstant(Register, Value):
        return Op(E_Op.AssignConstant, Register, Value)
    
    @staticmethod
    def Accepter(AcceptanceScheme=None):
        # When new analysis approach is used, then AcceptanceScheme can never
        # be 'None'.
        result = Op(E_Op.Accepter)
        if AcceptanceScheme is not None:
            result.content = AccepterContent.from_iterable(AcceptanceScheme)
        return result

    @staticmethod
    def RouterByLastAcceptance():
        return Op(E_Op.RouterByLastAcceptance)
    
    @staticmethod
    def RouterOnStateKey(CompressionType, MegaStateIndex, IterableStateKeyStateIndexPairs, DoorID_provider):
        result = Op(E_Op.RouterOnStateKey)
    
        result.content.configure(CompressionType, MegaStateIndex, 
                                 IterableStateKeyStateIndexPairs, DoorID_provider)
        return result
    
    @staticmethod
    def QuexDebug(TheString):
        return Op(E_Op.QuexDebug, TheString)
    
    @staticmethod
    def QuexAssertNoPassage():
        return Op(E_Op.QuexAssertNoPassage)

    @staticmethod
    def PasspartoutCounterCall(ModeName, EndPosition):
        result = Op(E_Op.PasspartoutCounterCall, ModeName, EndPosition)
        return result

    @staticmethod
    def LineCountShift():
        return Op(E_Op.LineCountShift)

    @staticmethod
    def ColumnCountShift():
        return Op(E_Op.ColumnCountShift)

    @staticmethod
    def ColumnCountSet(Value):
        return Op(E_Op.ColumnCountSet, Value)

    def is_conditionless_goto(self):
        if self.id == E_Op.GotoDoorId: 
            return True
        elif self.id == E_Op.IfAcceptanceConditionSetPositionAndGoto:
            return     not self.content.acceptance_condition_set \
                   and self.content.router_element.positioning == 0
        return False
    
    def get_register_access_iterable(self):
        """For each command there are access infos associated with registers. For example
        a command that writes into register 'X' associates 'write-access' with X.
    
        This is MORE than what is found in '_access_db'. This function may derive 
        information on accessed registers from actual 'content' of the Op.
        
        RETURNS: An iterable over pairs (register_id, access right) meaning that the
                 command accesses the register with the given access type/right.
        """
        global _access_db
    
        for register_id, access in _access_db[self.id].items():
            if isinstance(register_id, numbers.Integral):
                register_id = self.content[register_id] # register_id == Argument number which contains E_R
            elif type(register_id) == tuple:
                main_id          = register_id[0]       # register_id[0] --> in E_R
                sub_reference_id = register_id[1]       # register_id[1] --> Argument number containing sub-id
                sub_id           = self.content[sub_reference_id]
                register_id = "%s:%s" % (main_id, sub_id)
            yield register_id, access
    
    def get_access_rights(self, RegisterId):
        """Provides information about how the command modifies the register
        identified by 'RegisterId'. The 'read/write' access information is 
        provided in form of an RegisterAccessRight object.
        
        This function MUST rely on 'get_register_access_iterable', because 
        register ids may be produced dynamically based on arguments to the 
        command.
        
        RETURNS: RegisterAccessRight for the given RegisterId.
                 None, if command does not modify the given register.
        """
        for register_id, access in self.get_register_access_iterable():
            if register_id == RegisterId: return access
        return None

    def __hash__(self):      
        return self.my_hash

    def __eq__(self, Other):
        if   self.__class__ != Other.__class__: return False
        elif self.id        != Other.id:        return False
        elif self.content   != Other.content:   return False
        else:                                   return True

    def __ne__(self, Other):
        return not (self == Other)

    def __str__(self):
        name_str = str(self.id)
        if self.content is None:
            return "%s" % name_str

        elif self.id == E_Op.StoreInputPosition:
            x = self.content
            txt = ""
            if x.acceptance_condition_set:
                for acceptance_condition_id in x.acceptance_condition_set:
                    txt += "if %s: " % repr_pre_context_id(acceptance_condition_id)
            pos_str = repr_position_register(x.position_register)
            if x.offset == 0:
                txt += "%s = input_p;" % pos_str
            else:
                txt += "%s = input_p - %i;" % (pos_str, x.offset)
            return txt

        elif self.id == E_Op.Accepter:
            return str(self.content)

        elif self.id == E_Op.RouterByLastAcceptance:
            return str(self.content)

        elif self.id == E_Op.RouterOnStateKey:
            return str(self.content)

        elif self.id == E_Op.PreContextOK:
            return "pre-context-fulfilled = %s;" % self.content.acceptance_condition_id

        else:
            def get_string(member, value):
                if value is None: return ""
                else:             return "%s=%s, " % (member, value) 
            content_str = "".join(get_string(member, value) for member, value in sorted(self.content._asdict().items()))
            return "%s: { %s }" % (name_str, content_str)   

def is_switchable(A, B):
    """Determines whether the command A and command B can be switched
    in a sequence of commands. This is NOT possible if:

       -- A and B read/write to the same register. 
          Two reads to the same register are no problem.

       -- One of the commands is goto-ing, i.e. branching.
    """
    if A.branch_f or B.branch_f: return False

    for register_id, access_a in A.get_register_access_iterable():
        access_b = B.get_access_rights(register_id)
        if access_b is None:
            # Register from command A is not found in command B
            # => no restriction from this register.
            continue
        elif access_a.write_f or access_b.write_f:
            # => at least one writes.
            # Also:
            #   access_b not None => B accesses register_id (read, write, or both)
            #   access_a not None => A accesses register_id (read, write, or both)
            # 
            # => Possible cases here:
            #
            #     (A w,  B w), (A w,  B r), (A w,  B rw)
            #     (A r,  B w), (A r,  B r), (A r,  B rw)
            #     (A rw, B w), (A rw, B r), (A rw, B rw)
            #
            # In all those cases A and B depend on the order that they are executed.
            # => No switch possible
            return False
        else:
            continue

    return True

def __configure():
    """Configure the database for commands.
            
    cost_db:      CommandId --> computational cost.
    content_db:   CommandId --> related registers
    access_db:    CommandId --> access types of the command (read/write)
    brancher_set: set of commands which may cause jumps/gotos.
    """
    cost_db    = {}
    content_db = {}
    access_db  = {}    # map: register_id --> RegisterAccessRight
    #______________________________________________________________________________
    # 1        -> Read
    # 2        -> Write
    # 1+2 == 3 -> Read/Write
    r = 1                # READ
    w = 2                # WRITE
    RegisterAccessRight = namedtuple("AccessRight", ("write_f", "read_f"))

    class RegisterAccessDB(dict):
        def __init__(self, RegisterAccessInfoList):
            for info in RegisterAccessInfoList:
                register_id = info[0]
                rights      = info[1]
                if len(info) == 3: 
                    sub_id_reference = info[2]
                    register_id = (register_id, sub_id_reference)
                self[register_id] = RegisterAccessRight(rights & w, rights & r)

    brancher_set = set() # set of ids of branching/goto-ing commands.

    def c(OpId, ParameterList, *RegisterAccessInfoList):
        # -- access to related 'registers'
        access_db[OpId] = RegisterAccessDB(RegisterAccessInfoList)

        # -- parameters that specify the command
        if type(ParameterList) != tuple: 
            content_db[OpId] = ParameterList # Constructor
        elif not ParameterList:    
            content_db[OpId] = None
        else:                            
            content_type        = namedtuple("%s_content" % OpId.name, ParameterList)
            content_type.__new__.__defaults__ = (None,)*len(ParameterList)
            #mapping            = dict((name, "copy(self.%s)" % name) for name in ParameterList)
            #content_type.clone = lambda self: self.__class__(**mapping)
            content_db[OpId]    = content_type
        
        # -- computational cost of the command
        cost_db[OpId] = 1

        # -- determine whether command is subject to 'goto/branching'
        for register_id in (info[0] for info in RegisterAccessInfoList):
            if register_id == E_R.ThreadOfControl: brancher_set.add(OpId)

    c(E_Op.Accepter,                         AccepterContent, 
                                             (E_R.PreContextFlags,r), (E_R.AcceptanceRegister,w))
    c(E_Op.Assign,                           ("target", "source", "condition"), 
                                              (0,w),     (1,r))
    c(E_Op.AssignConstant,                   ("register", "value"), 
                                              (0,w))
    c(E_Op.AssignPointerDifference,          ("result", "big",  "small"), 
                                              (0,w),    (1, r), (2, r))
    c(E_Op.PointerAssignMin,                 ("result", "a",  "b", "condition"), 
                                              (0,w),    (1, r), (2, r))
    c(E_Op.PointerAdd,                       ("pointer", "offset", "condition"),
                                              (0, w+r), (1, r))
    c(E_Op.PreContextOK,                     ("acceptance_condition_id",), 
                                              (E_R.PreContextFlags,w))
    #
    c(E_Op.ReturnFromLexicalAnalysis,         None,
                                               (E_R.ThreadOfControl,w))
    c(E_Op.GotoDoorId,                        ("door_id",), 
                                               (E_R.ThreadOfControl,w))
    c(E_Op.GotoDoorIdIfInputPNotEqualPointer, ("door_id",                              "pointer"),
                                               (E_R.ThreadOfControl,w), (E_R.InputP,r), (1,r))
    c(E_Op.GotoDoorIdIfInputPEqualPointer,    ("door_id",                              "pointer"),
                                               (E_R.ThreadOfControl,w), (E_R.InputP,r), (1,r))
    c(E_Op.GotoDoorIdIfCounterEqualZero,      ("door_id",),
                                               (E_R.ThreadOfControl,w), (E_R.Counter,r))
    #
    c(E_Op.StoreInputPosition,                (               "acceptance_condition_set",        "position_register",       "offset"),
                                               (E_R.InputP,r), (E_R.PreContextFlags,r), (E_R.PositionRegister,w,1)) # Argument '1' --> sub_id_reference
    c(E_Op.IfAcceptanceConditionSetPositionAndGoto,   ("acceptance_condition_set", "router_element"),
                                              (E_R.PreContextFlags, r), (E_R.PositionRegister, r), (E_R.ThreadOfControl, w), 
                                              (E_R.InputP, r+w))
    c(E_Op.InputPDereference,                None, (E_R.InputP,r), (E_R.Input,w))
    c(E_Op.Decrement,                        ("register",), (0,r+w))
    c(E_Op.Increment,                        ("register",), (0,r+w))
    #
    c(E_Op.LexemeResetTerminatingZero,       None, 
                                             (E_R.LexemeStartP,r), (E_R.Buffer,w), (E_R.InputP,r), (E_R.Input,w))
    #
    c(E_Op.IndentationHandlerCall,           ("mode_name",),
                                              (E_R.Column,r), (E_R.Indentation,r+w), (E_R.CountReferenceP,r))
    c(E_Op.IndentationBadHandlerCall,        ("mode_name",),
                                              (E_R.Column,r), (E_R.Indentation,r+w), (E_R.CountReferenceP,r))
    #
    c(E_Op.ColumnCountAdd,                   ("value", "factor"),
                                              (E_R.Column,r+w))
    c(E_Op.ColumnCountGridAdd,               ("grid_size", "step_n"),
                                              (E_R.Column,r+w))
    c(E_Op.ColumnCountReferencePSet,         ("pointer", "offset"),
                                              (0,r), (E_R.CountReferenceP,w))
    c(E_Op.ColumnCountReferencePDeltaAdd,    ("pointer", "column_n_per_chunk", "subtract_one_f"),
                                              (E_R.Column,r+w), (0,r), (E_R.CountReferenceP,r))
    c(E_Op.ColumnCountShift,                 None,
                                              (E_R.Column,r+w))
    c(E_Op.ColumnCountSet,                   ("value",),
                                              (E_R.Column,w))
    c(E_Op.LineCountAdd,                     ("value", "factor"),
                                              (E_R.Line,r+w))
    c(E_Op.LineCountShift,                   None,
                                              (E_R.Line,r+w))
    c(E_Op.PasspartoutCounterCall,           ("mode_name", "end_position"),
                                              (E_R.Line,r+w), (E_R.Column,r+w), (E_R.LexemeStartP,r), (E_R.Buffer,r), (E_R.InputP,r), (E_R.MinRequiredBufferPositionWithoutLexemeStartP, r))
    #
    c(E_Op.PathIteratorSet,                  ("path_walker_id", "path_id", "offset"),
                                              (E_R.PathIterator,w))
    c(E_Op.RouterByLastAcceptance,           RouterContent, 
                                              (E_R.AcceptanceRegister,r), (E_R.InputP,w), (E_R.ThreadOfControl,w))
                                             # TODO: Add "(E_R.PositionRegister,w,*)"
    c(E_Op.RouterOnStateKey,                 RouterOnStateKeyContent, 
                                              (E_R.TemplateStateKey,r), (E_R.PathIterator,r), (E_R.ThreadOfControl,w))
    c(E_Op.TemplateStateKeySet,              ("state_key",),
                                              (E_R.TemplateStateKey,w))
    #
    c(E_Op.PrepareAfterReload,               ("on_success_door_id", "on_failure_door_id"),
                                              (E_R.TargetStateIndex,w), (E_R.TargetStateElseIndex,w))
    #
    c(E_Op.QuexDebug,                        ("string",), 
                                              (E_R.StandardOutput,w))
    c(E_Op.QuexAssertNoPassage,              None, 
                                              (E_R.StandardOutput,w), (E_R.ThreadOfControl, r+w))
    #
    return access_db, content_db, brancher_set, cost_db

_access_db,    \
_content_db,   \
_brancher_set, \
_cost_db       = __configure()

class OpList(list):
    """OpList -- a list of commands -- Intend: 'tuple' => immutable.
    """
    def __init__(self, *CL):
        self.__enter_list(CL)

    def __enter_list(self, Other):
        for op in Other:
            assert isinstance(op, Op), "%s: %s" % (op.__class__, op)
        super(OpList, self).extend(Other)

    @classmethod
    def from_iterable(cls, Iterable):
        result = OpList()
        result.__enter_list(list(Iterable))
        return result

    @staticmethod
    def concatinate(*ListOfOpLists):
        """Generate a mew OpList with .cloned() elements out of self and
        the Other OpList.
        """ 
        assert all(isinstance(x, (OpList, list)) for x in ListOfOpLists)
        return OpList.from_iterable(x.clone() 
                                    for sub_list in ListOfOpLists
                                    for x in sub_list)


    def cut(self, NoneOfThis):
        """Delete all commands of NoneOfThis from this command list.
        """
        return OpList.from_iterable(
                           cmd for cmd in self if cmd not in NoneOfThis)

    def clone(self):
        return OpList.from_iterable(x.clone() for x in self)

    def is_empty(self):
        return super(OpList, self).__len__() == 0

    def cost(self):
        global _cost_db
        return sum(_cost_db[cmd.id] for cmd in self)

    def has_command_id(self, OpId):
        assert OpId in E_Op
        for cmd in self:
            if cmd.id == OpId: return True
        return False

    def access_accepter(self):
        """Gets the accepter from the command list. If there is no accepter
        yet, then it creates one and adds it to the list.
        """
        for cmd in self:
            if cmd.id == E_Op.Accepter: return cmd.content

        accepter = Op.Accepter()
        self.append(accepter)
        return accepter.content

    def insert_StoreInputPositionUniquely(self, other):
        assert other.id == E_Op.StoreInputPosition
        # First check, whether there has not been inserted any of same kind before.
        for cmd in self:
            if   cmd.id                != E_Op.StoreInputPosition: continue
            elif cmd.position_register != other.position_register: continue
            assert cmd == other
            return # No need to insert again.

        # Not yet inserted => insert now
        self.insert(0, other)

    def replace_position_registers(self, PositionRegisterMap):
        """Replace for any position register indices 'x' and 'y' given by
         
                      y = PositionRegisterMap[x]

        replace register index 'x' by 'y'.
        """
        if not PositionRegisterMap: 
            return

        for i in range(len(self)):
            cmd = self[i]
            if cmd.id == E_Op.StoreInputPosition:
                # Commands are immutable, so create a new one.
                new_command = Op.StoreInputPosition(cmd.content.acceptance_condition_set, 
                                                    PositionRegisterMap[cmd.content.position_register],
                                                    cmd.content.offset)
                self[i] = new_command
            elif cmd.id == E_Op.IfAcceptanceConditionSetPositionAndGoto:
                cmd.content.router_element.replace(PositionRegisterMap)
            elif cmd.id == E_Op.RouterByLastAcceptance:
                cmd.content.replace(PositionRegisterMap)

    def delete_superfluous_commands(self):
        """
        (1) A position storage which is unconditional makes any conditional
            storage superfluous. Those may be deleted without loss.
        (2) A position storage does not have to appear twice, leave the first!
            (This may occur due to register set optimization!)
        """
        for cmd in self:
            assert isinstance(cmd, Op), "%s" % cmd

        # (1) Unconditional rules out conditional
        unconditional_position_register_set = set(
            cmd.content.position_register
            for cmd in self \
                if     cmd.id == E_Op.StoreInputPosition \
                   and not cmd.content.acceptance_condition_set
        )
        delete_if(self,
                  lambda cmd:
                       cmd.id == E_Op.StoreInputPosition \
                   and cmd.content.position_register in unconditional_position_register_set \
                   and cmd.content.acceptance_condition_set)

        # (2) Storage command does not appear twice. Keep first.
        #     (May occur due to optimizations!)
        occured_set = set()
        size        = len(self)
        i           = 0
        while i < size:
            cmd = self[i]
            if cmd.id == E_Op.StoreInputPosition: 
                if cmd not in occured_set: 
                    occured_set.add(cmd)
                else:
                    del self[i]
                    size -= 1
                    continue
            i += 1
        return

    def __hash__(self):
        xor_sum = 0
        for cmd in self:
            xor_sum ^= hash(cmd)
        return xor_sum

    def __eq__(self, Other):
        if isinstance(Other, OpList) == False: return False
        return super(OpList, self).__eq__(Other)

    def __ne__(self, Other):
        return not (self == Other)

    def __lt__(self, Other):
        if   self.id < Other.id:           return True
        elif self.id > Other.id:           return False
        elif self.content < Other.content: return True
        elif self.content > Other.content: return False
        elif self.branch < Other.branch:   return True
        elif self.branch > Other.branch:   return False
        # 'my_hash' is a function of 'id' and 'content'
        else:                              return False
        

    def __str__(self):
        return "".join("%s\n" % str(cmd) for cmd in self)

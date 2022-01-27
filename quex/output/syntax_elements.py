# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.tools import typed

from   collections import namedtuple

Argument = namedtuple("Argument", ("type", "name", "default"))

class Symbol:
    @classmethod
    def type_and_name(cls, SubString):
        """Interpret string as argument definition.
          
                type name '=' default 

        RETURNS: (argument type, argument name, argument default value)
        """
        assert SubString
        idx = SubString.find("=")
        if idx != -1:
            core_str    = SubString[:idx]
            default_str = SubString[idx+1:].strip()
        else:
            core_str    = SubString
            default_str = ""

        fields   = [x.strip() for x in core_str.split()]
        type_str = " ".join(fields[:-1])
        name_str = fields[-1]

        return type_str, name_str, default_str

    @classmethod
    def condition_str(cls, SubString, OpenBracketF=True):
        if OpenBracketF: 
            begin_i = SubString.find("<")
            if begin_i == -1: return None, SubString
            begin_i += 1
        else:            
            begin_i = 0

        end_i     = SubString.find(">")
        condition = SubString[begin_i: end_i].strip()
        return condition, SubString[end_i+1:]

class Variable:
    @typed(ElementN=(int,None))
    def __init__(self, Name, Type, ElementN, InitialValue, Condition=None, ConditionNegatedF=False, PriorityF=False, ConstantF=False):
        """ElementN is None --> scalar value
                    is int  --> array of dimension ElementN
        """
        self.name           = Name
        self.variable_type  = Type
        self.initial_value  = InitialValue
        self.element_n      = ElementN
        self.condition      = Condition
        # Some variables need to be defined before others --> Set some to 'prior'
        self.priority_f     = PriorityF
        self.constant_f     = ConstantF    # Does not change object's state
        
    @classmethod
    def from_String(cls, String):
        """SYNTAX: return-type; function-name; argument-list [const];

        argument-list:   type name [ '=' default ]','
        """
        condition,     \
        remainder      = cls.condition_str(String)

        variable_type, \
        variable_name, \
        initial_value  = cls.type_and_name(remainder)

        remainder  = String.strip()
        constant_f = (remainder == "const")

        return cls(Name              = variable_name, 
                   Type              = variable_type, 
                   InitialValue      = initial_value, 
                   Condition         = condition, 
                   ConditionNegatedF = False,
                   PriorityF         = False,
                   ConstantF         = constant_f)

class Signature(Symbol):
    @typed(ConstantF=bool)
    def __init__(self, ReturnType, FunctionName, ArgumentList, Condition, ConstantF):
        self.return_type   = ReturnType
        self.function_name = FunctionName
        self.argument_list = ArgumentList # (type, name, default)
        self.condition     = Condition
        self.constant_f    = ConstantF    # Does not change object's state

    @classmethod
    def from_String(cls, String):
        """SYNTAX: return-type; function-name; argument-list [const];

        argument-list:   type name [ '=' default ]','
        """
        condition, string = cls.condition_str(String)

        open_i  = string.find("(")
        close_i = string.rfind(")")
        return_type, function_name, default_str = cls.type_and_name(string[:open_i])
        argument_list = [ 
            Argument(*cls.type_and_name(x))
            for x in string[open_i+1:close_i].split(",") if x.strip()
        ]

        remainder  = string[close_i+1:].strip()
        constant_f = (remainder == "const")

        return cls(return_type, function_name, argument_list, condition, constant_f)

class ConditionalCode(Symbol):
    @typed(ConstantF=bool)
    def __init__(self, Condition, Code):
        self.condition = Condition
        self.content   = Code

    @classmethod
    def from_String(cls, String):
        """SYNTAX: condition '>' '-' content 
        """
        condition, remainder = cls.condition_str(String, OpenBracketF=False)

        return ConditionalCode(condition, remainder.lstrip("-"))


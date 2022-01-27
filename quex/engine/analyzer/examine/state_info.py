# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.engine.misc.tools import flatten

class StateInfo(object):
    """Base class for state informations with respect to 'recipes' and the
    set of concerned registers 'V'. This class is to be considered 'abstract'.

                                 .------------.
                                 |_StateInfo__|
                                 |  .rsov     |
                                 |  .recipe   |
                                 '------------'
                                      |   |
                            .---->----'   '----<----.
                            |                       |
                   .-----------------.      .----------------.
                   |_LinearStateInfo_|      |_MouthStateInfo_|
                   '-----------------'      | .entry_db      |
                                            '----------------'       
                                            
    MEMBER FUNCTIONS:
    
        .mouth_f() --> Tells whether object is about linear or mouth states.
        .is_determined() --> Tells whether object contains a valid recipe.
    """
    __slots__ = ("recipe", "required_variable_set", "spring_f")
    def __init__(self):
        self.required_variable_set = None  # set():   relevant registers for state
        self.recipe                = None  # default: recipe/state is NOT determined.
        self.spring_f              = False
        
    def mouth_f(self):
        """<ABSTRACT> RETURNS:
             True  -- if class of object is 'MouthStateInfo'.
             False -- if class of object is 'LinearStateInfo'.
        """
        assert False, "Must be implemented by derived class"
        
    def is_determined(self):
        return self.recipe is not None

    def get_DropOut(self, StateIndex, RecipeType):
        """Generates a 'state.DropOut' object for the state of the given index.

        RETURNS: OpList
        """
        self.recipe_type.get_DropOut(self.recipe)

    def __str__(self):
        return "V: %s;\nrecipe: {\n%s\n}" % (self.scr, self.recipe)

class LinearStateInfo(StateInfo):
    """.recipe        = Accumulated action Recipe(i) that determines V(i) after 
                        state has been entered.

    The '.recipe' is determined from a spring state, or through accumulation of
    linear states. The 'on_drop_out' handler can be determined as soon as 
    '.recipe' is determined.
    """
    def __init__(self):
        StateInfo.__init__(self)
        
    def get_Entry(self, StateIndex, RecipeType):
        """Generates an 'state.Entry' object for the state of the given index.

        RETURNS: Dictionary:

                      'from_state_index' ---> OpList
        """
        assert False

    def mouth_f(self):
        return False

class MouthStateInfo(StateInfo):
    """
       .entry_recipe_db:

              from state index --> incoming recipe

    This member is build during analysis. Until the incoming recipe is
    determined, the associated recipe of a 'from state' is None. Once, all
    recipes are determined the following two members can be derived by
    'interference'.
    
       .recipe   = Recipe(i) that determines V(i) after state has been 
                   entered.
       .entry_db: 
           
              from state index --> operations to be performed 
              
    The difference between '.entry_recipe_db' and '.entry_db' is that the
    recipe db, has more the informative nature of a recipe. In contrast, the
    '.entry_db' tells about operations that MUST be performed upon state entry.
    This includes operations that store results in registers where later recipes
    may refer to.
    """
    __slots__ = ("entry_recipe_db", "homogeneity_db")
    def __init__(self, FromStateIndexSet):
        StateInfo.__init__(self)
        self.entry_recipe_db = dict((si, None) for si in FromStateIndexSet)
        self.homogeneity_db  = dict((si, False) for si in FromStateIndexSet)

    def entry_reicpes_all_determined(self):
        """Checks whether all entry recipes are present, so that interference
        may be applied.
        
        RETURNS: True  -- if so.
                 False -- else.
        """
        for recipe in self.entry_recipe_db.values():
            if recipe is None: return False
        return True

    def mouth_f(self):
        return True

    def get_Entry(self, StateIndex, RecipeType):
        """Generates an 'state.Entry' object for the state of the given index.

        RETURNS: Dictionary:

                      'from_state_index' ---> OpList
        """
        result = {}
        for predecessor_si, recipe in self.entry_recipe_db.items():
            if not self.homogeneity_db[predecessor_si]:
                result[predecessor_si] = self.recipe_type.get_Entry(recipe)
        return result

    def __str__(self):
        txt = StateInfo.__str__(self)
        erdb_str = "".join("%s: %s\n" % (key, cmd_list) 
                           for key, cmd_list in self.entry_recipe_db.items())
        return "%s\nentry_recipe_db: {\n%s\n}" % (txt, erdb_str)

def SnapshotSetDb(dict):
    def from_mouth(self, Mouth):
        """According to [DOC] the snapshot set for a given variable at 
        interference becomes the union of all snapshot sets for this variable.

        RETURNS: Database mapping:

                             variable_id ---> snapshot set

        """
        db = SnapshotSetDb()
        db.update(
            (variable_id, set(flatten(
                     recipe.snapshot_set_db[variable_id]
                     for recipe in Mouth.entry_recipe_db.values()))
            )
            for variable_id in Mouth.required_variable_set
        )
        return db

    def __missing__(self, Keys):
        return set()

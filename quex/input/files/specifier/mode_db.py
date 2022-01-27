import quex.input.regular_expression.core as     regular_expression
import quex.input.files.mode_option       as     mode_option
import quex.input.files.code_fragment     as     code_fragment
from   quex.input.files.specifier.mode    import ModeParsed, Mode_Builder
import quex.input.files.consistency_check as     consistency_check
from   quex.input.code.base               import SourceRef
                                          
import quex.engine.misc.error             as     error
import quex.engine.misc.similarity        as     similarity
from   quex.engine.misc.file_in           import EndOfStreamException, \
                                                 check, \
                                                 check_or_die, \
                                                 check_end_of_file, \
                                                 read_identifier, \
                                                 read_until_letter, \
                                                 read_until_whitespace, \
                                                 is_identifier, \
                                                 skip_whitespace, \
                                                 optional_flags
from   quex.output.token.id_generator     import token_id_db_enter

import quex.blackboard as     blackboard
from   quex.blackboard import setup as Setup, \
                              Lng, \
                              standard_incidence_db

from   collections import namedtuple

class ModeDb_Builder:
    def __init__(self, ModeParsedDb):
        assert not Setup.token_class_only_f
        assert not Setup.converter_only_f
        assert ModeParsedDb
        assert all(isinstance(x, ModeParsed) for x in ModeParsedDb.values())

        _add_entry_exit_permissions_to_all_if_none_is_set(ModeParsedDb)
        _check_inheritance_relationships(ModeParsedDb)

        self.builderList = [Mode_Builder(mode) for name, mode in ModeParsedDb.items()]

    @staticmethod
    def do(ModeParsedDb):
        builder = ModeDb_Builder(ModeParsedDb)
        builder.detect_empty_non_abstract_modes(ModeParsedDb)
        builder.collect_base_mode_information(ModeParsedDb)
        builder.collect_and_prioritize_patterns()
        builder.finalize()

        return builder.result

    def detect_empty_non_abstract_modes(self, ModeParsedList):
        """Detects whether there is a mode that is not abstract while it is 
        completely void of patterns/event handlers.

        THROWS: Error in case.
        
        At this point in time, the matching configuration has been expressed
        in the 'pattern_list'. That is, if there are event handler's then the
        'pattern_list' is not empty.
        """
        for mode in ModeParsedList.values():
            if   mode.option_db.value("inheritable") == "only": continue
            elif mode.pattern_action_pair_list:                 continue
            elif mode.incidence_db:                             continue

            error.warning("Mode without pattern or pattern-related event handlers.\n" + \
                          "Option <inheritable: only> will be added automatically.", mode.sr)

            mode.option_db.enter("inheritable", "only", mode.sr, mode.name)

    def collect_base_mode_information(self, ModeParsedDb):
        base_mode_sequence_db = _determine_base_mode_db(ModeParsedDb)
        derived_mode_db       = _determine_derived_mode_name_db(ModeParsedDb)

        for builder in self.builderList:
            base_mode_sequence = base_mode_sequence_db[builder.name]
            builder.collect_base_mode_information(base_mode_sequence,
                                                  derived_mode_db)

        self.mode_prep_db = dict(
            (builder.name, builder.get_Mode_Prep())
            for builder in self.builderList
        )

    def collect_and_prioritize_patterns(self):
        for builder in self.builderList:
            builder.collect_and_prioritize_patterns(self.mode_prep_db)

    def finalize(self):
        consistency_check.do(list(self.mode_prep_db.values()))

        for builder in self.builderList:
            builder.finalize_documentation(self.mode_prep_db)

        builderList_real = [
            b for b in self.builderList if b.get_Mode_Prep().implemented_f()
        ]

        if not builderList_real:
            error.log("There is no mode that can be implemented---all existing modes are empty or 'inheritable only'.\n" + \
                      "modes are = " + ", ".join(m.name for m in self.mode_prep_db.values()) + ".",
                      Prefix="consistency check")

        for builder in builderList_real:
            builder.finalize()

        self.result = dict((b.name, b.get_Mode()) for b in builderList_real)

def _determine_derived_mode_name_db(ModeParsedDb):
    """RETURNS: 'derived_db'

           mode_name ---> list of all names of derived mode
    """
    derived_db = dict((name, set([name])) for name in ModeParsedDb)
    for name in ModeParsedDb:
        base_mode_list = ModeParsedDb[name].direct_base_mode_name_list
        for base_name in base_mode_list:
            derived_db[base_name].add(name)

    for mode_name, derived_set in derived_db.items():
        worklist = set(derived_set)
        done_set = set([mode_name])
        while worklist:
            cmode_name   = worklist.pop()
            cderived_set = derived_db.get(cmode_name)
            done_set.add(cmode_name)
            if cderived_set is None: continue
            new_etsi_set = cderived_set.difference(derived_set)
            derived_set.update(new_etsi_set)
            worklist.update(x for x in new_etsi_set if x not in done_set)
        # 'derived_set' (a reference) of 'mode_name' has been updated.

    return derived_db

def _determine_base_mode_db(ModeParsedDb):
    """RETURNS: 'base_mode_db'

            mode_name --> list of base modes (according to sequentialization)
    """
    result = {}
    for mode_name in ModeParsedDb:
        base_mode_name_sequence = _determine_base_mode_db_core(mode_name, ModeParsedDb)
        result[mode_name] = [ModeParsedDb[m] for m in base_mode_name_sequence]
    return result

def _add_entry_exit_permissions_to_all_if_none_is_set(ModeParsedDb):
    """Entry/Exit Default Behavior:

    If no <entry: > or <exit: > tag is set, then every mode can enter every mode
    except for itself.
    """
    entry_exit_f = any(
        mode.option_db.has("entry", "exit") for mode in ModeParsedDb.values()
    )
    if entry_exit_f: return

    for mode in ModeParsedDb.values():
        all_but_this = [
            name for name in ModeParsedDb if name != mode.name 
        ]
        mode.option_db.enter("exit", all_but_this, SourceReference=-1, ModeName=mode.name)
        mode.option_db.enter("entry", all_but_this, SourceReference=-1, ModeName=mode.name)
        
    return

def _determine_base_mode_db_core(ModeName, ModeParsedDb):
    """Determine the sequence of base modes. The type of sequencing determines
       also the pattern precedence. The 'deep first' scheme is chosen here. For
       example a mode hierarchie of

                                   A
                                 /   \ 
                                B     C
                               / \   / \
                              D  E  F   G

       results in a sequence: (A, B, D, E, C, F, G).reverse()

       => That is the mode itself is result[-1]

       => Patterns and event handlers of 'E' have precedence over
          'C' because they are the childs of a preceding base mode.

       This function detects circular inheritance.
    """
    Node = namedtuple("Node", ("mode_name", "inheritance_path"))
    global base_name_list_db
    result   = [ ModeName ]
    done     = set()
    worklist = [ Node(ModeName, []) ]
    while worklist:
        node = worklist.pop(0)
        if node.mode_name in done: continue
        done.add(node.mode_name)

        inheritance_path = node.inheritance_path + [node.mode_name]
        
        mode = ModeParsedDb[node.mode_name]
        i    = result.index(node.mode_name)
        for name in reversed(mode.direct_base_mode_name_list):
            error.verify_word_in_list(name, list(ModeParsedDb.keys()),
                                      "Mode '%s' inherits mode '%s' which does not exist." \
                                      % (mode.name, name), mode.sr)
            if name in inheritance_path: 
                _error_circular_inheritance(inheritance_path, ModeParsedDb)
            elif name not in result:
                result.insert(i, name)
        worklist.extend(Node(name, inheritance_path) 
                        for name in mode.direct_base_mode_name_list)

    return result

def _check_inheritance_relationships(ModeParsedDb):
    for mode in ModeParsedDb.values():
        mode_name_set = set(ModeParsedDb.keys())
        for mode_name in mode.direct_base_mode_name_list:
            if mode_name not in mode_name_set:
                error.verify_word_in_list(mode_name, mode_name_set,
                          "mode '%s' inherits from a mode '%s'\nbut no such mode exists." % \
                          (mode.name, mode_name), mode.sr)
            if ModeParsedDb[mode_name].option_db.value("inheritable") == "no":
                error.log("mode '%s' inherits mode '%s' which is not inheritable." % \
                          (mode.name, mode_name), mode.sr)

def _error_circular_inheritance(InheritancePath, ModeParsedDb):
    def sr(ModeName): return ModeParsedDb[ModeName].sr
    name0     = InheritancePath[-1]
    msg       = "circular inheritance detected:\n"
    msg      += "mode '%s'\n" % name0
    prev_name = name0
    error.log(msg, sr(name0), DontExitF=True)
    for name in InheritancePath[:-1]:
        error.log("   inherits mode '%s'\n" % name, sr(prev_name), DontExitF=True)
        prev_name = name
    error.log("   inherits mode '%s'\n" % name0, sr(prev_name))


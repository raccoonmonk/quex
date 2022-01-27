# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
import quex.engine.misc.error                        as     error
import quex.engine.misc.file_in                      as     file_in
from   quex.engine.misc.quex_enum                    import QuexEnum
from   quex.engine.misc.interval_handling            import Interval, Interval_All
from   quex.constants                                import INTEGER_MAX, E_Files

import os  
import sys
from   enum import auto, EnumMeta

class Lexatom:
    def __init__(self, Lng, encoding, TypeName, SizeInByte):
        # SizeInByte  TypeName   => .size_in_byte  .type
        #    -1        ""        =>   encoding.DEFAULT_LEXATOM_TYPE_SIZE db[size]
        #    -1        "known"   =>   known size   "known"
        #    -1        "unknown" =>   -1           "unknown"
        # KnownN       ""        =>   KnownN       known type
        # KnownN       "any"     =>   KnownN       "any"
        # UnknownN     "any"     =>   UnknownN     "any"
        # UnknownN     ""        =>   << error >> 
        if SizeInByte == -1:
            if not TypeName:
                sib = encoding.DEFAULT_LEXATOM_TYPE_SIZE
                tn  = Lng.STANDARD_TYPE_DB[sib]
            elif TypeName in global_character_type_db:
                sib = global_character_type_db[TypeName][3]
                tn  = TypeName
            else:
                sib = -1
                tn = TypeName
        elif SizeInByte in Lng.STANDARD_TYPE_DB:
            if not TypeName:
                sib = SizeInByte
                tn  = Lng.STANDARD_TYPE_DB[sib]
            else:
                sib = SizeInByte
                tn  = TypeName
        else:
            if TypeName:
                sib = SizeInByte
                tn  = TypeName
            else:
                error.log("Buffer element type cannot be determined for size '%i' which\n" \
                          % SizeInByte + 
                          "has been specified by '-b' or '--buffer-element-size'.")

        self.size_in_byte = sib
        self.type         = tn
        self.type_range   = self.__get_type_range(self.size_in_byte)

    def __get_type_range(self, LexatomByteN):
        if LexatomByteN == -1: 
            result = Interval_All()
        else:
            assert LexatomByteN >= 1

            try:    
                value_n = 256 ** LexatomByteN
            except:
                error.log("Error while trying to compute 256 power the 'lexatom-size' (%i bytes)\n"   \
                          % LexatomByteN + \
                          "Adapt \"--buffer-element-size\" or \"--buffer-element-type\",\n"       + \
                          "or specify '--buffer-element-size-irrelevant' to ignore the issue.")

            result = Interval(0, min(value_n, INTEGER_MAX + 1))

        return result

class QuexSetup:
    def __init__(self, SetupInfo, BcFactory):
        self.init(SetupInfo)

    def buffer_setup(self, LexatomTypeName, LexatomSizeInByte, 
                     BufferEncoding, BufferEncodingFileName=""):
        import quex.engine.state_machine.transformation.core as bc_factory
        encoding = bc_factory.do(BufferEncoding, BufferEncodingFileName)

        self.lexatom_set(Lexatom(self.language_db, encoding,
                                 LexatomTypeName,
                                 LexatomSizeInByte))

        encoding.adapt_ranges_to_lexatom_type_range(self.lexatom.type_range)
        self.__buffer_encoding = encoding

    def adapted_encoding_name(self):
        """RETURNS: Name of buffer encoding, if name != unicode
                    A standard encoding name (uft8, utf16, utf32), else. 
                    None, if no standard encoding name could be associated 
                          with the lexatom's size.
        """
        if self.buffer_encoding.name != "unicode": 
            return self.buffer_encoding.name
        elif self.lexatom.size_in_byte == 1: 
            return "utf8"
        elif self.lexatom.size_in_byte == 2: 
            return "utf16"
        elif self.lexatom.size_in_byte == 4: 
            return "utf32"
        else:
            return None

    def set_all_character_set_UNIT_TEST(self):
        if self.language_db is None:
            import quex.output.languages.core as languages
            self.language_db = languages.db["C++"]()
        self.buffer_setup("<no-type>", -1, "none")

    @property
    def buffer_encoding(self):
        if self.__buffer_encoding is None:
            self.set_all_character_set_UNIT_TEST()
        return self.__buffer_encoding

    @property
    def lexatom(self):
        if self.__lexatom is None:
            self.set_all_character_set_UNIT_TEST()
        return self.__lexatom

    def lexatom_set(self, LexatomInfo):
        self.__lexatom = LexatomInfo
        if self.__buffer_encoding:
            self.__buffer_encoding.adapt_ranges_to_lexatom_type_range(self.lexatom.type_range)

    def init(self, SetupInfo):
        default_db = {
            SetupParTypes.LIST:            list,
            SetupParTypes.INT_LIST:        list,
            SetupParTypes.FLAG:            False,
            SetupParTypes.NEGATED_FLAG:    True,
            SetupParTypes.OPTIONAL_STRING: None,  # "" indicates no follower string
        }
        for key, entry in list(SetupInfo.items()):
            if type(entry) != list:                         
                default_value = entry
            else:
                flag_list, arg_type = entry
                default_value       = default_db.get(arg_type, arg_type)
                # Ensure, that for each value a different list is created.
                if default_value == list: default_value = []

            self.__dict__[key] = default_value

        # Default values, maybe overiden later on.
        self.language_db  = None
        self.compression_type_list = []
        self.__buffer_encoding     = None
        self.__lexatom             = None

        file_in.specify_setup_object(self)

    def set(self, Name, Type, Value):
        if Type in (SetupParTypes.LIST, SetupParTypes.INT_LIST):
            prev = self.__dict__.get(Name)
            if prev in SetupParTypes: self.__dict__[Name] = Value
            else:                     prev.extend(Value)
        else:
            self.__dict__[Name] = Value

    def get_file_reference(self, FileName):
        """When a source package is specified, then it must be given
           with 'relative coordinates' to the source package directory.
           
           if 'SourcePackager':
               $QUEX_PATH/quex/code_base --> source-package-dir/quex/code_base
               .  (current dir)          --> source-package-dir     
        """
        return os.path.normpath(os.path.join(self.output_directory, FileName))

    def prepare_file_name(self, Suffix, ContentType):
        assert ContentType in E_Files

        # Language + Extenstion Scheme + ContentType --> name of extension
        ext       = self.language_db.extension_db[ContentType]
        file_name = "%s%s%s" % (self.output_file_stem, Suffix, ext)
        return self.get_file_reference(file_name)

    def prepare_output_directory(self):
        if   self.output_directory:    return
        elif self.analyzer_class_name: directory = self.analyzer_class_name
        else:                          directory = "./"
        self.output_directory = os.path.normpath(directory)

    def prepare_all_file_names(self):
        #__________________________________________________________________________
        if self.language in ["DOT"]: return

        self.output_file_stem = self.analyzer_class_name

        self.output_code_file          = self.prepare_file_name("",               E_Files.SOURCE) 
        self.output_header_file        = self.prepare_file_name("",               E_Files.HEADER)
        self.output_configuration_file = self.prepare_file_name("-configuration", E_Files.HEADER)
        self.output_configuration_file_cmake = "%s.in" % self.output_configuration_file
        self.output_token_id_file      = self.prepare_file_name("-token_ids",     E_Files.HEADER)
        if self.extern_token_id_file:
            self.output_token_id_file_ref = self.extern_token_id_file
        else:
            self.output_token_id_file_ref = self.prepare_file_name("-token_ids",     
                                                                   E_Files.HEADER) 
        # Token class:
        if self.extern_token_class_file:
            header_file         = self.extern_token_class_file
            implementation_file = None # Must be linked outside!
        else:
            if self.token_class_only_f == False: implementation_type = E_Files.HEADER_IMPLEMTATION
            else:                                implementation_type = E_Files.SOURCE
            header_file         = self.prepare_file_name("-token", E_Files.HEADER)
            implementation_file = self.prepare_file_name("-token", implementation_type)

        self.output_token_class_file                = header_file
        self.output_token_class_file_implementation = implementation_file
        assert self.output_token_class_file != self.output_token_class_file_implementation

class SetupParTypes(QuexEnum):
    FLAG            = auto()
    INT_LIST        = auto()
    LIST            = auto()
    NEGATED_FLAG    = auto()
    OPTIONAL_STRING = auto()
    STRING          = auto()

SETUP_INFO = {         
    # [Name in Setup]                 [ Flags ]                                [Default / Type]
    "__buffer_lexatom_size_in_byte":  [["--buffer-element-size", "-b", "--bes"], -1],  # [Bytes] => ".lexatom.size_in_byte"
    "__buffer_lexatom_type":          [["--lexatom-type", "--buffer-element-type", "--bet"],     ""],
    "__no_count_line_and_column_f":   [["--no-count", "--nc"],                 SetupParTypes.FLAG],
    "__no_token_class_support_token_stamp_f":     [["--no-token-stamp",           "--nts"],   SetupParTypes.FLAG],
    "_debug_QUEX_TYPE_LEXATOM_EXT":   [["--debug-QUEX_TYPE_LEXATOM_EXT"],      SetupParTypes.FLAG], 
    "_debug_exception_f":             [["--debug-exception"],                  SetupParTypes.FLAG], 
    "_debug_limit_recursion":         [["--debug-limit-recursion"],            0], 
    "_debug_reference_original_paths_f": [["--debug-original-paths"],          SetupParTypes.FLAG], 
    "analyzer_class":                 [["-o", "--analyzer-class"],             ""],    
    "analyzer_derived_class_file":    [["--derived-class-file"],               ""],
    "analyzer_derived_class_name":    [["--derived-class", "--dc"],            ""],
    "bad_lexatom_detection_f":        [["--no-bad-lexatom-detection", "--nbld"], SetupParTypes.NEGATED_FLAG],
    "buffer_encoding_file":           [["--encoding-file"],                    ""],
    "buffer_encoding_name":           [["--encoding"],                         "unicode"],
    "buffer_limit_code":              [["--buffer-limit"],                     0x0],
    "character_display":              [["--character-display"],                "utf8"],
    "comment_mode_patterns_f":        [["--comment-mode-patterns"],            SetupParTypes.FLAG],
    "comment_state_machine_f":        [["--comment-state-machine"],            SetupParTypes.FLAG],
    "comment_transitions_f":          [["--comment-transitions"],              SetupParTypes.FLAG],
    "compression_path_f":             [["--path-compression"],                 SetupParTypes.FLAG],
    "compression_path_uniform_f":     [["--path-compression-uniform"],         SetupParTypes.FLAG],
    "compression_template_f":         [["--template-compression"],             SetupParTypes.FLAG],
    "compression_template_min_gain":  [["--template-compression-min-gain"],    0],
    "compression_template_uniform_f": [["--template-compression-uniform"],     SetupParTypes.FLAG],
    "computed_gotos_f":               [["--computed-gotos", "--cg"],           SetupParTypes.FLAG],
    "configuration_by_cmake_f":       [["--cbcm", "--config-by-cmake"],        SetupParTypes.FLAG],    
    "configuration_by_macros_f":      [["--cbm",  "--config-by-macros"],        SetupParTypes.FLAG],    
    "converter_only_f":               [["--converter-only", "--co"],           SetupParTypes.FLAG],
    "converter_source_name":          [["--converter-source-name", "--csn"],  ""],
    "count_column_number_f":          [["--no-count-columns", "--ncc"],        SetupParTypes.NEGATED_FLAG],
    "count_line_number_f":            [["--no-count-lines", "--ncl"],          SetupParTypes.NEGATED_FLAG],
    "dos_carriage_return_newline_f":  [["--no-DOS"],                           SetupParTypes.NEGATED_FLAG],
    "extern_token_class_file":        [["--token-class-file"],                 ""],
    "extern_token_id_file_show_f":    [["--foreign-token-id-file-show"],       SetupParTypes.FLAG],
    "extern_token_id_specification":  [["--foreign-token-id-file"],            SetupParTypes.LIST],  
    "fallback_mandatory_f":           [["--fallback-mandatory", "--fbm"],  SetupParTypes.FLAG],
    "fallback_optional_f":            [["--fallback-optional", "--fbo"],  SetupParTypes.FLAG],
    "implement_lexeme_null_f":        [["--no-lexeme-null", "--nln"],          SetupParTypes.NEGATED_FLAG],
    "implement_lib_lexeme_f":         [["--no-lib-lexeme", "--nll"],         SetupParTypes.NEGATED_FLAG],
    "implement_lib_quex_f":           [["--no-lib-quex", "--nlq"],           SetupParTypes.NEGATED_FLAG],
    "indentation_stack_size":         [["--indentation-stack-size", "--indss" ], 1024],
    "input_mode_files":               [["-i"],                                 SetupParTypes.LIST],
    "insight_f":                      [["--insight"],                          SetupParTypes.FLAG],
    "language":                       [["--language", "-l"],                 "C++"],
    "memory_management_extern_f":     [["--extern-memory-management", "--emm"], SetupParTypes.FLAG],
    "mode_stack_size":                [["--mode-stack-size",        "--mss" ],   64],
    "mode_transition_check_f":        [["--no-mode-transition-check"],       SetupParTypes.NEGATED_FLAG],
    "normalize_f":                    [["--normalize"],                      SetupParTypes.FLAG],
    "output_directory":               [["--output-directory", "--odir"],     ""],
    "output_file_naming_scheme":      [["--file-extension-scheme", "--fes"], ""],
    "path_limit_code":                [["--path-termination"],                 0x1],
    "post_context_end_of_line_implies_end_of_stream_f":    [["--not-eol-is-eos", "--neie"], SetupParTypes.NEGATED_FLAG],
    "pre_context_begin_of_line_implies_begin_of_stream_f": [["--not-bol-is-bos", "--nbib"], SetupParTypes.NEGATED_FLAG],
    "quex_lib":                       [["--ql", "--quex-lib"],                 ""],    
    "show_name_spaces_f":             [["--show-name-spaces", "--sns"],      SetupParTypes.FLAG],
    "standard_library_tiny_f":        [["--tiny-stdlib",  "--tsl"],            SetupParTypes.FLAG],
    "standard_library_usage_f":       [["--no-stdlib", "--nostdlib", "--nsl"], SetupParTypes.NEGATED_FLAG],
    "suppressed_notification_list":   [["--suppress", "-s"],                   SetupParTypes.INT_LIST],
    "token_class":                    [["--token-class", "--tc"],              ""],
    "token_class_only_f":             [["--token-class-only", "--tco"],        SetupParTypes.FLAG],
    "token_class_support_take_text_f":            [["--token-class-support-take-text",  "--tcstt"], SetupParTypes.FLAG],
    "token_class_support_token_stamp_column_n_f": [["--no-token-stamp-column-count", "--ntscc"], SetupParTypes.NEGATED_FLAG],
    "token_class_support_token_stamp_line_n_f":   [["--no-token-stamp-line-count",   "--ntslc"], SetupParTypes.NEGATED_FLAG],
    "token_id_counter_offset":        [["--token-id-offset"],                10000],
    "token_id_prefix":                [["--token-id-prefix"],                "QUEX_TKN_"],
    "token_id_type":                  [["--token-id-type"],                  ""],
    "token_line_n_type":              [["--token-line-n-type"],              ""],
    "token_column_n_type":            [["--token-column-n-type"],            ""],
    "token_queue_size":               [["--token-queue-size"],               64],
    "token_repetition_n_member_name": [["--token-repetition-n-member-name", "--trnmn"], ""],
    "unit_test_f":                    [["--unit-test"],                      SetupParTypes.NEGATED_FLAG],
    "user_application_version_id":    [["--version-id"],                     "0.0.0-pre-release"],
    #
    "warning_on_outrun_f":            [["--warning-on-outrun", "--woo"],   SetupParTypes.FLAG],
    #
    # QUERY MODE:
    #
    "query_version_f":                [["--version", "-v"],               SetupParTypes.FLAG],
    "query_help_f":                   [["--help", "-h"],                  SetupParTypes.FLAG],
    "query_encoding":                 [["--encoding-info",         "--ei"],  ""],
    "query_encoding_list":            [["--encoding-list",         "--el"],  SetupParTypes.FLAG],
    "query_encoding_file":            [["--encoding-info-file",    "--eif"], ""], 
    "query_encoding_language":        [["--encoding-for-language", "--eil"], ""],
    "query_property":                 [["--property", "--pr"],            SetupParTypes.OPTIONAL_STRING],
    "query_set_by_property":          [["--set-by-property", "--sbpr"],   ""], 
    "query_set_by_expression":        [["--set-by-expression", "--sbe"],  ""],
    "query_property_match":           [["--property-match", "--prm"],     ""],
    "query_numeric_f":                [["--numeric", "--num"],            SetupParTypes.FLAG],
    "query_interval_f":               [["--intervals", "--itv"],          SetupParTypes.FLAG],
    "query_unicode_names_f":          [["--names"],                       SetupParTypes.FLAG],
    #
    #__________________________________________________________________________
    # Parameters not set on the command line:
    "_quex_lib_name_space":                      None,
    "_quex_lib_prefix":                          None,
    "_quex_lib_name_safe":                       None,
    "analyzer_class_name":                       None,
    "analyzer_name_space":                       None,
    "analyzer_name_safe":                        None,
    "analyzer_derived_class_name_space":         None,
    "analyzer_derived_class_name_safe":          None,
    "__lexatom":                                 None,
    "token_class_name":                          None,
    "token_class_name_space":                    None,
    "token_class_name_safe":                     None,
    "token_id_prefix_name_space":                None,
    "token_id_prefix_plain":                     None,   # i.e. without the namespace specified.
    "extern_token_id_file":                      "",
    "token_id_foreign_definition_file_region_begin_re":  None,
    "token_id_foreign_definition_file_region_end_re":    None,
    "output_header_file":                        None,
    "output_configuration_file":                 None,
    "output_code_file":                          None,
    "output_file_stem":                          "",
    "output_token_id_file":                      None,
    "output_token_class_file_implementation":    None,
    "output_token_class_file":                   None,
    "language_db":                               None,
    "compression_type_list":                     None,
    #______________________________________________________________________________________________________
    #
    # DEPRECATED
    #______________________________________________________________________________________________________
    "XX_token_class_support_repetition_f": [["--token-class-support-repetition", "--tcsr"],  SetupParTypes.FLAG],
    "XX_OLD_query_codec":                [["--codec-info", "--ci"],          ""],
    "XX_OLD_query_codec_list":           [["--codec-list", "--cl"],          SetupParTypes.FLAG],
    "XX_OLD_query_codec_file":           [["--codec-info-file", "--cif"],    ""], 
    "XX_OLD_query_codec_language":       [["--codec-for-language", "--cil"], ""],
    "XX_OLD_buffer_codec_name":          [["--codec"],                            "unicode"],
    "XX_OLD_buffer_codec_file":          [["--codec-file"],                       ""],
    "XX_token_memory_management_by_user_f": [["--token-memory-management-by-user", "--tmmbu"], SetupParTypes.FLAG],
    "XX_post_categorizer_f":             [["--post-categorizer"],               SetupParTypes.FLAG],
    "XX_token_policy":                   [["--token-policy", "--tp"],           "queue"],                
    "XX_begin_of_stream_code":           [["--begin-of-stream"],                "0x19"],                  
    "XX_buffer_element_size":            [["--bytes-per-ucs-code-point"],       "1"],                  
    "XX_buffer_element_size2":           [["--bytes-per-trigger"],              -1],                  
    "XX_end_of_stream_code":             [["--end-of-stream"],                  "0x1A"],                  
    "XX_flex_engine_f":                  [["--flex-engine"],                    SetupParTypes.FLAG],      
    "XX_read_pattern_file":              [["-p", "--pattern-file"],             ""],                      
    "XX_input_token_id_db":              [["-t", "--token-id-db"],              SetupParTypes.LIST],
    "XX_leave_temporary_files_f":        [["--leave-tmp-files"],                SetupParTypes.FLAG],      
    "XX_plain_memory_f":                 [["--plain-memory"],                   SetupParTypes.FLAG],           
    "XX_std_istream_support_f":          [["--istream-support"],                SetupParTypes.FLAG],           
    "XX_yywrap_is_ok_f":                 [["--yywrap-is-ok"],                   SetupParTypes.FLAG],           
    "XX_input_token_sending_via_queue_f":[["--token-queue"],                    SetupParTypes.FLAG],           
    "XX_no_string_accumulator_f":        [["--no-string-accumulator", "--nsacc"], SetupParTypes.NEGATED_FLAG],
    "XX_string_accumulator_f":           [["--string-accumulator", "--sacc"],   SetupParTypes.FLAG],  
    "XX_disable_token_queue_f":          [["--no-token-queue", "--ntq"],        SetupParTypes.FLAG],       
    "XX_disable_return_token_id_f":      [["--no-return-token-id"],             SetupParTypes.FLAG],  
    "XX_input_lexer_class_friends":      [["--friend-class"],                   SetupParTypes.LIST], 
    "XX_token_class_name":               [["--token-class-name"],               ""],             
    "XX_token_class_stringless_check_f": [["--token-type-no-stringless-check",  "--ttnsc"], SetupParTypes.NEGATED_FLAG], 
    "XX_token_id_counter_offset":        [["--token-offset"],                     "10000"],        
    "XX_token_id_termination":           [["--token-id-termination"],             "0"],            
    "XX_token_id_uninitialized":         [["--token-id-uninitialized"],           "1"],            
    "XX_token_id_indentation_error":     [["--token-id-indentation-error"],       "2"],            
    "XX_output_debug_f":                 [["--debug"],                            SetupParTypes.FLAG],
    "XX_plot_graphic_format":            [["--plot"],                             ""],
    "XX_plot_character_display":         [["--plot-character-display", "--pcd"],  "utf8"],
    "XX_plot_graphic_format_list_f":     [["--plot-format-list"],                 SetupParTypes.FLAG],
    "XX_compression_template_coef":      [["--template-compression-coefficient"], 1.0],
    "XX_token_id_prefix":                [["--token-prefix"],                     "QUEX_TKN_"],
    "XX_message_on_extra_options_f":     [["--no-message-on-extra-options"],      SetupParTypes.NEGATED_FLAG],
    "XX_error_on_dominated_pattern_f":      [["--no-error-on-dominated-pattern",      "--neodp"],   SetupParTypes.NEGATED_FLAG],
    "XX_error_on_special_pattern_same_f":   [["--no-error-on-special-pattern-same",   "--neosps"],  SetupParTypes.NEGATED_FLAG],
    "XX_error_on_special_pattern_outrun_f": [["--no-error-on-special-pattern-outrun", "--neospo"],  SetupParTypes.NEGATED_FLAG],
    "XX_error_on_special_pattern_subset_f": [["--no-error-on-special-pattern-subset", "--neospsu"], SetupParTypes.NEGATED_FLAG],
    "XX_warning_disabled_no_token_queue_f": [["--no-warning-on-no-token-queue"], SetupParTypes.FLAG],
    "XX_state_entry_analysis_complexity_limit": [["--state-entry-analysis-complexity-limit", "--seacl"], 1000],
    "XX_mode_files":                        [["--mode-files"], None],
    "XX_engine":                            [["--engine"], None],
    "XX_token_class_take_text_check_f":  [["--token-type-no-take_text-check",     "--ttnttc"], SetupParTypes.NEGATED_FLAG], 
    "XX_buffer_based_analyzis_f":        [["--buffer-based", "--bb"],             SetupParTypes.FLAG],
    "XX_converter_user_new_func":        [["--converter-new", "--cn"],            ""],
    "XX_converter_iconv_f":              [["--iconv"],                            SetupParTypes.FLAG],
    "XX_converter_icu_f":                [["--icu"],                              SetupParTypes.FLAG],
    "XX_external_lexeme_null_object":    [["--lexeme-null-object", "--lno"],      ""],
    "XX_token_queue_safety_border":      [["--token-queue-safety-border"],      16],
    "XX_source_package_directory":       [["--source-package", "--sp"],         ""],
    "XX_single_mode_analyzer_f":         [["--single-mode-analyzer", "--sma"],  SetupParTypes.FLAG],
    "XX_include_stack_support_f":        [["--no-include-stack", "--nois"],       SetupParTypes.NEGATED_FLAG],
    "XX_buffer_byte_order":              [["--endian"],                           ""],    # default => sys.byteorder
    "XX_converter_ucs_coding_name":      [["--converter-ucs-coding-name", "--cucn"], ""],
}

class NotificationDB:
    # IMPORTANT: The notification ids are NOT supposed to changed between
    #            different versions. Otherwise, updates of quex may cause
    #            compatibility issues.
    #
    # Notification Name:                              Notification ID:
    token_id_ignored_files_report                     = 0
    message_on_extra_options                          = 1
    error_on_dominated_pattern                        = 2
    error_on_special_pattern_same                     = 3
    error_on_special_pattern_outrun                   = 4
    error_on_special_pattern_subset                   = 5
    warning_on_no_token_queue                         = 6
    warning_usage_of_undefined_token_id_name          = 7
    warning_repeated_token_not_yet_defined            = 8
    warning_token_id_prefix_appears_in_token_id_name  = 9
    warning_codec_error_with_non_unicode              = 10
    warning_counter_setup_without_newline             = 11
    warning_counter_setup_without_else                = 12
    warning_default_newline_0A_impossible             = 13
    warning_default_newline_0D_impossible             = 14
    warning_on_no_token_class_take_text               = 15
    warning_on_no_warning_on_missing_take_text        = 16
    error_ufo_on_command_line_f                       = 17
    warning_on_duplicate_token_id                     = 18
    warning_incidence_handler_overwrite               = 19
    warning_pattern_contains_elements_beyond_encoding = 20

DEPRECATED = { 
  "XX_token_class_support_repetition_f": 
    ("Options '--token-class-support-repetition', respectively '--tcsr' no longer supported."),
  "XX_converter_ucs_coding_name": 
    ("Option '--converter-ucs-coding-name' no longer supported.",
     "0.69.1"),
  "XX_buffer_byte_order": 
    ("Option '--endian' no longer supported. Endianness is determined at run-time.",
     "0.69.1"), 
  "XX_include_stack_support_f": 
    ("Option '--no-include-stack' is no longer supported.", 
      "0.69.1"), 
  "XX_single_mode_analyzer_f": 
    ("Single mode analyzer's no longer have to be indicated on the command line.",
     "0.69.1"),
  "XX_source_package_directory": 
    ("Since version 0.69.1, only complete source packages are produced.\n"
     "Explicit source packaging is obsolete.",
     "0.69.1"),
  "XX_token_queue_safety_border":
    ("Command line option '--token-queue-safety-border' considered useless with new\n"
     "token queue implementation.", 
     "0.68.2"),
  "XX_OLD_query_codec": 
    ("Use '--encoding-info' or '--ei' instead of '--codec-info', '--ci'",
     "0.67.5"),
  "XX_OLD_query_codec_list":           
    ("Use '--encoding-list' or '--el' instead of '--codec-list' or '--cl'",        
     "0.67.5"),
  "XX_OLD_query_codec_file":           
    ("Use '--encoding-info-file' or '--eif' instead of '--codec-info-file' or '--cif'",  
     "0.67.5"),
  "XX_OLD_query_codec_language":       
    ("User of '--encoding-for-language' or '--eil' instead of '--codec-for-language' or '--cil'", 
     "0.67.5"),
  "XX_OLD_buffer_codec_name": 
    ("Buffer encoding is no longer specified via '--codec' use '--encoding'.",
     "0.67.5"), 
  "XX_OLD_buffer_codec_file":          
    ("Buffer encoding specification file is no longer specified via\n"
     "'--codec-file' use '--encoding-file'.",
     "0.67.5"), 
  "XX_token_memory_management_by_user_f": 
     ("User token memory management option no longer available.",
      "0.67.4"), 
  "XX_post_categorizer_f": 
     ("The post categorizer  has been pulled out of the generator. It's header\n"
      "can be included anyway.",
      "0.67.3"),
  "XX_no_string_accumulator_f":
     ("The string accumulator has been pulled out of the generator. It's header\n"
      "can be included anyway.",
      "0.67.3"),
  "XX_token_policy": 
     ("There is only one token policy 'queue' in recent versions of Quex.\n" + \
      "Option '--token-policy' or '--tp' are considered superfluous."
      "0.67.3"),
  "XX_read_pattern_file": 
     ("Write a 'pattern { ... }' section inside the mode files instead.\n" + \
      "Syntax of the 'pattern { ... }' section and the previous file syntax\n" + \
      "are backward compatible.", "0.9.x"),        
  "XX_input_token_id_db":
     ("Write a 'token { ... }' section inside the mode files instead.\n" + \
      "Syntax of the 'token { ... }' section and the previous file syntax\n" + \
      "are backward compatible.", "0.9.x"),        
  "XX_yywrap_is_ok_f":
     ("Since the mentioned version, the flex core engine is no longer supported. The\n" + \
      "flag makes only sense for flex core engines.", "0.13.1"),
  "XX_flex_engine_f":
     ("Since the mentioned version, the flex core engine is no longer supported. The\n" + \
      "flag makes only sense for flex core engines.", "0.13.1"),
  "XX_leave_temporary_files_f":
     ("Since the mentioned version, the flex core engine is no longer supported. The\n" + \
      "flag makes only sense for flex core engines.", "0.13.1"),
  "XX_plain_memory_f":                 
     ("Since the mentioned version, quex does no longer need the '--plain-memory' command\n" + \
      "line argument. The engine can be used with plain memory directly. Please, consider\n" + \
      "reading the documentation on this issue.", "0.31.1"),
  "XX_std_istream_support_f":
     ("The lexical analyzer has a flexible interface now, for both C++ istreams and FILE*\n" + \
      "so that rigid setting with this option is superfluous", "0.13.1"),
  "XX_begin_of_stream_code":
     ("Since the mentioned version, there is no need for end of stream and end of stream\n" + \
      "characters anymore. Options '--end-of-stream' and '--begin-of-stream' are no longer\n" + \
      "supported.", "0.25.2"),
  "XX_end_of_stream_code":
     ("Since the mentioned version, there is no need for end of stream and end of stream\n" + \
      "characters anymore. Options '--end-of-stream' and '--begin-of-stream' are no longer\n" + \
      "supported.", "0.25.2"),
  "XX_input_token_sending_via_queue_f":
     ("The token queue was temporarily turned off by default. Since 0.31.5 the token queue is again\n" + \
      "turned on by default, since the lexical analysers can be described much more natural. If you\n" + \
      "want to disable the token queue, please, use '--no-token-queue', or '--ntq'.", "0.31.5"),
  "XX_string_accumulator_f":
     ("The string accumulator was temporarily turned off by default. Since 0.31.5 the it is again\n" + \
      "turned on by default. If you want to disable the token queue, please, use '--no-string-accumulator',\n" + \
      "or '--nsacc'.", "0.31.5"),
  "XX_disable_token_queue_f":
     ("Since version 0.36.5 the flag '--no-token-queue' and '--ntq' have been deprecated.\n" + \
      "Use flag '--token-policy' or '--tp' instead.", "0.36.5"),     
  "XX_disable_return_token_id_f":      
     ("Flag --no-return-token-id is no longer supported. In recent versions of quex\n" + \
      "token-IDs are not passed as return values at all.", "0.37.1"), 
  "XX_input_lexer_class_friends":  
      ("Since version 0.46.3, friend classes are no longer defined on the command line. Please,\n"
       "use the 'body { ... }' section and fill be-'friend'-ing code there.", "0.46.3"),
  "XX_token_class_name":
      ("Command line option '--token-class-name' has been renamed to '--token-class'\n"
       "for uniformity.", "0.46.3"),
  "XX_token_class_stringless_check_f": 
      ("Command line options --token-type-no-stringless-check and --ttnsc are deprecated. Please,\n"
       "use --token-type-no-take_text-check or --ttnttc", 
       "0.48.1"), 
  "XX_buffer_element_size": 
      ("The command line option '--bytes-per-ucs-code-point' has been renamed to\n"
       "'--buffer-element-size'. The old name causes heavy confusion when it was\n"
       "used in combination with dynamic length codecs (option --encoding).", "0.49.1"),
  "XX_buffer_element_size2": 
      ("The command line option '--bytes-per-trigger' has been renamed to\n"
       "'--buffer-element-size'. This naming was chose to harmonize with the\n"  
       "new command line option '--buffer-element-type'.", "0.54.1"),
  "XX_token_id_counter_offset":
      ("The command line option '--token-offset' has been replaced by '--token-id-offset'."
       "0.51.1"),
  "XX_token_id_termination":
      ("Option '--token-id-termination' is no longer supported.\n" \
       "Numeric value for token ids are no longer defined on the command line.\n" \
       "Numeric values for token ids can be defined in token sections, e.g.\n" \
       "    token {\n" \
       "       TERMINATION = 4711;\n"
       "    }", "0.51.1"),
  "XX_token_id_uninitialized":         
      ("Option '--token-id-uninitialized' is no longer supported.\n" \
       "Numeric value for token ids are no longer defined on the command line.\n" \
       "Numeric values for token ids can be defined in token sections, e.g.\n" \
       "    token {\n" \
       "       UNINITIALIZED = 4711;\n"
       "    }", "0.51.1"),
  "XX_token_id_indentation_error":     
      ("Option '--token-id-indentation-error' is no longer supported.\n"          \
       "Numeric value for token ids are no longer defined on the command line.\n" \
       "Numeric values for token ids can be defined in token sections, e.g.\n"    \
       "    token {\n"                                                            \
       "       INDENTATION_ERROR = 4711;\n"                                       \
       "    }", "0.51.1"),
  "XX_output_debug_f":
      ("Option '--debug' is no longer supported. Column and line number counting\n" \
       "is supported by the compile option '-DQUEX_OPTION_DEBUG_SHOW_EXT'.",            \
       "0.58.3"),
  "XX_plot_graphic_format":         
      ("Option '--plot' no longer supported, use '--language dot' for example\n" \
       "to generate source code for the plot utility 'graphviz'\n"               \
       "(See http://www.graphviz.org)", 
       "0.59.9"),
  "XX_plot_character_display": 
      ("Option '--plot-character-display' and '--pcd' are no longer supported.\n" \
       "Please, use '--character-display' instead.", 
       "0.59.9"), 
  "XX_plot_graphic_format_list_f":     
      ("Option '--plot-format-list' is no longer supported. Note, that since 0.59.9\n" \
       "Quex does no longer call the GraphViz utility directly. Use '--language dot'.\n",
       "0.59.9"),
  "XX_compression_template_coef":      
      ("Option '--template-compression-coefficient' has been replaced by \n" \
       "'--template-compression-min-gain' which tells the minimum estimated number of\n" \
       "bytes that can be spared before two states would be combined.",
       "0.60.1"),
  "XX_token_id_prefix":
      ("Command line option '--token-prefix' has been renamed to '--token-id-prefix'\n"
       "for the sake of precision in expression.", "0.62.1"),
  "XX_message_on_extra_options_f": 
      ("Option '--no-message-on-extra-options' has been replaced with '--suppress %s'" 
       % NotificationDB.message_on_extra_options, "0.64.3"),
  "XX_error_on_dominated_pattern_f":
      ("Option '--no-error-on-dominated-pattern' or '--neodp' has been replaced with '--suppress %s'"
       % NotificationDB.error_on_dominated_pattern, "0.64.3"),
  "XX_error_on_special_pattern_same_f":   
      ("Option '--no-error-on-special-pattern-same' or '--neosps' has been replaced with '--suppress %s'"
       % NotificationDB.error_on_special_pattern_same, "0.64.3"),
  "XX_error_on_special_pattern_outrun_f": 
      ("Option '--no-error-on-special-pattern-outrun' or '--neospo' has been replaced with '--suppress %s'"
       % NotificationDB.error_on_special_pattern_outrun, "0.64.3"),
  "XX_error_on_special_pattern_subset_f": 
      ("Option '--no-error-on-special-pattern-subset' or '--neospsu' has been replaced with '--suppress %s'"
       % NotificationDB.error_on_special_pattern_subset, "0.64.3"),
  "XX_warning_disabled_no_token_queue_f": 
      ("Option '--no-warning-on-no-token-queue' has been replaced with '--suppress %s'"
       % NotificationDB.warning_on_no_token_queue, "0.64.3"),
  "XX_state_entry_analysis_complexity_limit":
      ("Option '--state-entry-analysis-complexity-limit' is no longer necessary.\n"
       "The related algorithm has been improved.", "0.65.1"),
  "XX_mode_files":
      ("Option '--mode-files' is no longer supported. Use '-i' instead.",
       "0.65.1"),
  "XX_engine":
      ("Option '--engine' is no longer supported, use '-o' or '--analyzer-class' instead.",
       "0.65.1"),
  "XX_token_class_take_text_check_f":  
      ("Option '--token-type-no-take_text-check' or '--ttnttc' is replaced by '--suppress %i'."
       % NotificationDB.warning_on_no_token_class_take_text,
       "0.65.1"),
  "XX_buffer_based_analyzis_f":        
    ("Option '--buffer-base' and '--bb' are deprecated. Buffer fillers are\n"
     "used for manual filling.", "0.65.1"),
  "XX_converter_user_new_func":        
    ("Options '--converter-new' and '--cn' are deprecated. Converters are now\n"
     "allocated by the user and passed to constructor, include-push, and reset\n"
     "functions.", "0.67.2"),
  "XX_converter_iconv_f": 
    ("Option '--iconv' no longer supported. Converters are passed created by\n"
     "user and passed to constructor. See demo examples or documentation.",
     "0.67.2"),
  "XX_converter_icu_f":                
    ("Option '--icu' no longer supported. Converters are passed created by\n"
     "user and passed to constructor. See demo examples or documentation.",
     "0.67.2"),
    "XX_external_lexeme_null_object":    
    ("Options '--lexeme-null-object' and '--lno' are no longer supported.\n"
     "The lexeme null is now located in the token class' namespace.\n",
     "0.67.3"),
}
 
global_character_type_db = {
        # Name:         Type:         LittleEndian     Big Endian       Bytes per 
        #                             Converter Name:  Converter Name:  engine character:
        "uint8_t":    [ "uint8_t",    "ASCII",         "ASCII",         1],
        "uint16_t":   [ "uint16_t",   "UCS-2LE",       "UCS-2BE",       2],
        "uint32_t":   [ "uint32_t",   "UCS-4LE",       "UCS-4BE",       4],
        "byte":       [ "byte",       "ASCII",         "ASCII",         1],
        "u8":         [ "u8",         "ASCII",         "ASCII",         1],
        "u16":        [ "u16",        "UCS-2LE",       "UCS-2BE",       2],
        "u32":        [ "u32",        "UCS-4LE",       "UCS-4BE",       4],
        "unsigned8":  [ "unsigned8",  "ASCII",         "ASCII",         1],
        "unsigned16": [ "unsigned16", "UCS-2LE",       "UCS-2BE",       2],
        "unsigned32": [ "unsigned32", "UCS-4LE",       "UCS-4BE",       4],
        "wchar_t":    [ "wchar_t",    "WCHAR_T",       "WCHAR_T",       -1],
}

DOC = {
    "_debug_exception_f":             ("Verbose output on internal exception.", ""),
    "analyzer_class":                 ("Specify analyzer class with optional namespace.", ""),
    "analyzer_derived_class_file":    ("Name of file containing derived class.", ""),
    "analyzer_derived_class_name":    ("Name of derived class with optional namespace.", ""),
    "buffer_encoding_name":              ("Buffer internal codec.", ""),
    "buffer_encoding_file":              ("Codec file describing mapping to unicode code points.", ""),
    "buffer_limit_code":              ("Buffer limit code.", ""),
    "__buffer_lexatom_size_in_byte":  ("Buffer element size.", ""),
    "__buffer_lexatom_type":          ("Buffer element type.", ""),
    "comment_state_machine_f":        ("Provide state machine description in comment of generated code.", ""),
    "comment_transitions_f":          ("Provided UTF8 representation of transition characters in comments of generated code.", ""),
    "comment_mode_patterns_f":        ("", ""),
    "compression_template_f":         ("Activate template compression.", ""),
    "compression_template_uniform_f": ("Activate template compression with constraint of uniformity.", ""),
    "compression_template_min_gain":  ("Specifies minimum gain for template compression.", ""),
    "compression_path_f":             ("Activate path compression.", ""),
    "compression_path_uniform_f":     ("Activate path compression with constraint of uniformity.", ""),
    "count_column_number_f":          ("Activate column number counting.", ""),
    "count_line_number_f":            ("Activate line number counting.", ""),
    "character_display":              ("", ""),
    "path_limit_code":                ("", ""),
    "dos_carriage_return_newline_f":  ("", ""),
    "string_accumulator_f":           ("", ""),
    "converter_iconv_f":              ("Use 'iconv' library for character conversions.", ""),
    "converter_icu_f":                ("Use 'icu' library for character conversions.", ""),
    "include_stack_support_f":        ("", ""),
    "input_mode_files":               ("", ""),
    "extern_token_class_file":               ("", ""),
    "token_class":                    ("", ""),
    "token_class_only_f":             ("", ""),
    "token_id_counter_offset":        ("", ""),
    "token_id_type":                  ("", ""),
    "token_id_prefix":                ("", ""),
    "token_queue_size":               ("", ""),
    "token_policy":                   ("", ""),
    "token_memory_management_by_user_f": ("", ""),
    "mode_transition_check_f":        ("", ""),
    "language":                       ("", ""),
    "normalize_f":                    ("", ""),
    "external_lexeme_null_object":    ("", ""),
    "output_file_naming_scheme":      ("", ""),
    "post_categorizer_f":             ("", ""),
    "output_directory":               ("", ""),
    "show_name_spaces_f":             ("", ""),
    "single_mode_analyzer_f":         ("", ""),
    "state_entry_analysis_complexity_limit": ("", ""),
    "user_application_version_id":           ("", ""),
    #
    "version_information":               ("", ""),
    "help":                              ("", ""),
    "warning_disabled_no_token_queue_f": ("", ""),
    "warning_on_outrun_f":               ("", ""),
}

def command_line_arg_position(ParameterName):
    arg_list = SETUP_INFO[ParameterName][0]
    min_position = 1e37
    for arg in arg_list:
        if arg not in sys.argv[1:]: continue
        position = sys.argv[1:].index(arg)
        if position < min_position: min_position = position
    return min_position

def command_line_args(ParameterName):
    return SETUP_INFO[ParameterName][0]

def command_line_args_defined(cl, ParameterName):
    cl.reset_cursor() # Necessary to capture all arguments
    return cl.search(command_line_args(ParameterName))

def command_line_args_string(ParameterName):
    args = command_line_args(ParameterName)
    if len(args) == 1: return "'%s'"          % args[0]
    if len(args) == 2: return "'%s' or '%s'" % (args[0], args[1])
    txt = ""
    for arg in args[:-1]:
        txt += "%s, " % arg
    return "%sor %s" % (txt, args[-1])


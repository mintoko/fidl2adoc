""" Generates an ASCIIDoc file from a list of Franca IDL files. """

import sys
import getopt
from typing import Dict, List, Union
from pyfranca import Processor, LexerException, ParserException
from pyfranca import ProcessorException, ast

adoc = []  # List of text lines for ASCIIDoc output.
type_references: Dict[ast.Type, List[ast.Type]] = {}


def get_namespace(ast_type: ast.Type) -> str:
    """ Returns the namespace name for parameter ast_type. TODO: Remove? """
    if isinstance(ast_type, ast.Reference):
        ast_type = ast_type.reference
    return ast_type.namespace.name


def fix_descr_intent(description: str) -> str:
    """ Corrects the indentation of a Franca IDL comment."""
    description_lines = description.split('\n')
    min_leading_spaces = -1
    for line in description_lines:
        leading_spaces = 0
        for character in line:
            if character == ' ':
                leading_spaces += 1
            else:
                break
        if leading_spaces > 0 and not line.isspace():
            if min_leading_spaces < 0:
                min_leading_spaces = leading_spaces
            min_leading_spaces = min(min_leading_spaces, leading_spaces)
    min_leading_spaces = max(min_leading_spaces, 0)
    fixed_intent_lines = []
    for line in description_lines:
        if line.startswith(' ' * min_leading_spaces):
            fixed_intent_lines.append(line[min_leading_spaces:])
        else:
            fixed_intent_lines.append(line)
    return '\n'.join(fixed_intent_lines)


def get_type_name(ast_type: ast.Type) -> str:
    """ Returns an adoc link to the adoc section describing ast_type. """
    name = ''
    if isinstance(ast_type, ast.PrimitiveType):
        name = ast_type.name
    elif isinstance(ast_type, ast.Array):
        if isinstance(ast_type.type, ast.PrimitiveType):
            name = 'Array of ' + ast_type.type.name
        else:
            if_name = get_namespace(ast_type.type)
            type_name = ast_type.type.name
            if isinstance(ast_type.type, ast.Reference):
                type_name = ast_type.type.reference.name
            name = 'Array of <<' + if_name + '-' + type_name + '>>'
    else:
        type_name = ast_type.name
        if isinstance(ast_type, ast.Reference):
            type_name = ast_type.reference.name
        if_name = get_namespace(ast_type)
        name = '<<' + if_name + '-' + type_name + '>>'
    return name


def add_type_reference(ast_type, reference):
    """ Adds an entry to the type_references dictionary. """
    if isinstance(ast_type, ast.Array):
        ast_type = ast_type.type
    if isinstance(ast_type, ast.Reference):
        ast_type = ast_type.reference
    if ast_type in type_references:
        type_references[ast_type] += [reference]
    else:
        type_references[ast_type] = [reference]


def adoc_type_references(ast_type):
    """ Adds a 'Used in' section to adoc with all references of ast_type. """
    if ast_type in type_references:
        adoc.append('\nUsed in: ')
        for used in type_references[ast_type]:
            # Append comma separator if not first item in list.
            if used != type_references[ast_type][0]:
                adoc.append(', ')
            adoc.append('<<' + get_namespace(used) + '-' + used.name + '>>')


def adoc_section_title(ast_type):
    """ Adds a ASCIIDoc section title. """
    adoc.append(f'[[{ast_type.namespace.name}-{ast_type.name}]]')
    if not hasattr(ast_type, 'extends') or ast_type.extends == None:
        adoc.append(f'=== {ast_type.__class__.__name__} {ast_type.name}\n')
    else:
        adoc.append(f'=== {ast_type.__class__.__name__} {ast_type.name} extends <<{ast_type.namespace.name}-{ast_type.extends}>> \n')


def get_adoc_from_comments(ast_elem: Union[ast.Type, ast.Namespace,
                           ast.Package]) -> str:
    """ Returns an ASCIIDoc string for AST type or namespace comments"""
    comment = ''
    if ast_elem.comments and '@description' in ast_elem.comments:
        comment = f'\n{fix_descr_intent(ast_elem.comments["@description"])}\n'
    if ast_elem.comments and '@see' in ast_elem.comments:
        sees = ast_elem.comments['@see'].split()
        comment_see = ''
        for see in sees:
            last_char = see[-1]
            if last_char in [',', '.']:
                see = see[:-1]
            try:
                see_elem = ast_elem.namespace.__getitem__(see)
                comment_see += get_type_name(see_elem)
            except (KeyError, AttributeError):
                comment_see += see
            if last_char in [',', '.']:
                comment_see += last_char
            comment_see += ' '
        comment += '\nSee also: ' + comment_see
    return comment


def adoc_table(title: str, entries: List[List[str]]):
    """ Adds an ASCIIDoc table to adoc with 'entries' as table rows.
        There must be at least 2 rows.  """
    if not entries or len(entries) <= 1:
        return
    adoc.append('\n' + title + '\n')
    adoc.append('[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    for entry in entries:
        adoc.append('|' + '|'.join(entry))
    adoc.append('|===\n')


def do_nothing(*_):
    """ do_nothing does nothing """


def add_references_for_ast_type(ast_type: ast.Type) -> None:
    """ Extend type_references dictionary with the references of ast_type. """
    if isinstance(ast_type, ast.Method):
        for arg in (list(ast_type.in_args.values()) +
                    list(ast_type.out_args.values())):
            add_type_reference(arg.type, ast_type)
        if ast_type.errors:
            add_type_reference(ast_type.errors, ast_type)
    elif isinstance(ast_type, ast.Attribute):
        add_type_reference(ast_type.type, ast_type)
    elif isinstance(ast_type, ast.Broadcast):
        for arg in ast_type.out_args.values():
            add_type_reference(arg.type, ast_type)
    elif isinstance(ast_type, ast.Struct):
        for field in ast_type.fields.values():
            add_type_reference(field.type, ast_type)
    elif isinstance(ast_type, ast.Array):
        add_type_reference(ast_type.type, ast_type)
    elif isinstance(ast_type, ast.Map):
        add_type_reference(ast_type.key_type, ast_type)
        add_type_reference(ast_type.value_type, ast_type)


def adoc_for_arg_list(args: List[Union[ast.StructField, ast.Argument]]
                      ) -> List[List[str]]:
    """ Adds ASCIIDoc for a Franca IDL method (TODO: rename) """
    return list(map(lambda arg: [get_type_name(arg.type), str(arg.name),
                                 get_adoc_from_comments(arg)], args))


def process_enumerators(enumerators: List[ast.Enumerator]) -> List[List[str]]:
    """ Adds ASCIIDoc for a Franca IDL enumerator list (TODO: rename) """
    enum_value = 0
    table_elements = []
    for enumerator in enumerators:
        if enumerator.value:
            enum_value = int(str(enumerator.value.value))
        table_elements.append([str(enumerator.name), str(enum_value),
                              get_adoc_from_comments(enumerator)])
        enum_value = enum_value + 1
    return table_elements


def adoc_for_ast_type(ast_type: ast.Type) -> None:
    """ Extends global ASCIIDoc adoc with documentation for ast_type. """
    adoc_section_title(ast_type)
    adoc.append(get_adoc_from_comments(ast_type))
    if isinstance(ast_type, ast.Method):
        adoc_table('Input Parameters:', [['Type', 'Name', 'Description']] +
                   adoc_for_arg_list(ast_type.in_args.values()))
        adoc_table('Output Parameters:', [['Type', 'Name', 'Description']] +
                   adoc_for_arg_list(ast_type.out_args.values()))
        if ast_type.errors:
            adoc.append('\nErrors: ' + get_type_name(ast_type.errors))
    elif isinstance(ast_type, ast.Attribute):
        adoc.append('\nAttribute data type: ' + get_type_name(ast_type.type))
    elif isinstance(ast_type, ast.Broadcast):
        adoc_table('Output Parameters:', [['Type', 'Name', 'Description']] +
                   adoc_for_arg_list(ast_type.out_args.values()))
    elif isinstance(ast_type, ast.Struct):
        values = ()
        ref_type = ast_type
        while True:
            values = tuple(ref_type.fields.values()) + values
            if ref_type.extends != None:
                ref_type = ref_type.reference
            else:
                break
        adoc_table('Struct fields:', [['Type', 'Name', 'Description']] +
                   adoc_for_arg_list(values))
    elif isinstance(ast_type, ast.Enumeration):
        values = ()
        ref_type = ast_type
        while True:
            values = tuple(ref_type.enumerators.values()) + values
            if ref_type.extends != None:
                ref_type = ref_type.reference
            else:
                break
        adoc_table('', [['Enumerator', 'Values', 'Description']] +
                   process_enumerators(values))
    elif isinstance(ast_type, ast.Array):
        adoc.append(f'Array item type: {get_type_name(ast_type.type)}\n')
    elif isinstance(ast_type, ast.Map):
        adoc.append(f'Key type: {get_type_name(ast_type.key_type)}\n')
        adoc.append(f'Value type: {get_type_name(ast_type.value_type)}\n')
    adoc_type_references(ast_type)


def adoc_major_section_title(values: Dict[str, ast.Type]) -> None:
    """ Adds ASCIIDoc section title for a Franca IDL types list. """
    if values:
        adoc.append(f'\n== {list(values.values())[0].__class__.__name__}s\n')


def adoc_for_namespace(package: ast.Package, namespace: ast.Namespace) -> None:
    """ Adds ASCIIDoc for an Franca IDL interface. """
    namespace_type = namespace.__class__.__name__
    adoc.append('\n[[' + namespace.name + ']]')
    adoc.append(f'= {namespace_type} {package.name}.{namespace.name}')
    if namespace.version:
        adoc.append('\nVersion: ' + str(namespace.version))
    adoc.append('\nThis section is generated from the Franca IDL file for ' +
                f'{namespace_type} {namespace.name} in package {package.name}')
    package_descr = get_adoc_from_comments(package)
    if_descr = get_adoc_from_comments(namespace)
    if package_descr:
        adoc.append('\nPackage description: ' + package_descr)
    if if_descr:
        adoc.append('\n' + namespace_type + ' description: ' + if_descr)


def process_item_lists(item_lists, ast_type_func, start_section_func):
    """ Processes a list of item lists with the function table funcs """
    for item_list in item_lists:
        start_section_func(item_list)
        for item in item_list.values():
            ast_type_func(item)


def iterate_fidl(processor, ast_type_func, namespace_func, start_section_func):
    """ Iterates through a Franca IDL AST. """
    for package in processor.packages.values():
        for namespace in (list(package.interfaces.values()) +
                          list(package.typecollections.values())):
            namespace_func(package, namespace)
            if isinstance(namespace, ast.Interface):
                process_item_lists([namespace.attributes,
                                   namespace.methods, namespace.broadcasts],
                                   ast_type_func, start_section_func)
            process_item_lists([namespace.structs, namespace.enumerations,
                               namespace.arrays, namespace.maps],
                               ast_type_func, start_section_func)


def process_inputfiles(inputfiles: List[str]) -> bool:
    """ Process inputfiles and append ASCIIDoc output to adoc. """
    processor = Processor()
    for fidl_file in inputfiles:
        try:
            processor.import_file(fidl_file.strip())
        except (LexerException, ParserException, ProcessorException) as exc:
            print("ERROR in " + fidl_file.strip() + ": " + str(exc))
            return False
    iterate_fidl(processor, add_references_for_ast_type,
                 do_nothing, do_nothing)
    iterate_fidl(processor, adoc_for_ast_type,
                 adoc_for_namespace, adoc_major_section_title)
    return True


def main(argv):
    """ Generates ASCIDoc file from a list of Franca IDL files. """
    inputfiles = []
    outputfile = ''
    help_txt = 'fidl2adoc.py -i <inputfile> [-i <inputfile2>]* -o <outputfile>'
    try:
        opts, _ = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print(help_txt)
        return 1
    for opt, arg in opts:
        if opt == '-h':
            print(help_txt)
            return 0
        if opt in ("-i", "--ifile"):
            inputfiles.append(arg)
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    if not inputfiles or not outputfile:
        print(help_txt)
        return 1
    print(f'Parsing documentation from Franca IDL files: {inputfiles}')
    print(f'Generating ASCIIDoc to file: {outputfile}')
    if not process_inputfiles(inputfiles):
        return 2
    with open(outputfile, 'w', encoding='utf-8') as file:
        file.write('\n'.join(adoc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

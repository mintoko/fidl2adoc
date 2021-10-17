""" Generates ASCIDoc file from a list of Franca IDL files. """

import sys
import getopt
from typing import Dict, List, Optional
from pyfranca import Processor, LexerException, ParserException
from pyfranca import ProcessorException, ast

adoc = []
type_references: Dict[ast.Type, List[ast.Type]] = {}


def get_namespace(ast_type: ast.Type) -> str:
    """ Returns the namespace name for parameter ast_type."""
    if isinstance(ast_type, ast.Reference):
        ast_type = ast_type.reference
    return ast_type.namespace.name


def fix_descr_intent(description: str) -> str:
    """ Corrects the intentation of a Franca IDL comment."""
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


def get_comment(obj: ast.Type, comment_type: str) -> Optional[str]:
    """ Returns comment_type from the comments dictionary. """
    comment = None
    if obj.comments and comment_type in obj.comments:
        comment = obj.comments[comment_type]
    return comment


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
    adoc.append('[[' + ast_type.namespace.name + '-' + ast_type.name + ']]')
    adoc.append('=== ' + str(ast_type.__class__.__name__) + ' ' +
                ast_type.name + '\n')


def get_adoc_link_from_name(namespace: ast.Namespace, name: str) -> str:
    """ Returns an ASCIIDoc link to documentation of name.
        TODO: Refactor w7 adoc_type_reference, get_namespace, get_type_name"""
    try:
        namespace.__getitem__(name)
        return '<<' + namespace.name + '-' + name + '>>'
    except KeyError:
        return name


def adoc_description(ast_type: ast.Type) -> None:
    """ Adds the comments from ast_type to adoc. """
    comment_description = get_comment(ast_type, '@description')
    comment_see = get_comment(ast_type, '@see')
    if comment_description:
        adoc.append('\n' + fix_descr_intent(comment_description))
    if comment_see:
        sees = comment_see.split()
        comment_see = ''
        for see in sees:
            comment_see += get_adoc_link_from_name(ast_type.namespace, see)
            comment_see += ' '
        adoc.append('\nSee also: ' + comment_see)


def adoc_table(title: str, columns: List[str], entries, entries_func):
    """ Adds a table to adoc TODO Change entries param . """
    if not entries:
        return
    adoc.append('\n' + title + '\n')
    adoc.append('[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    adoc.append('|' + '|'.join(columns))
    entries_func(entries)
    adoc.append('|===\n')


def do_nothing(*_):
    """ do_nothing does nothing """


def prep_method(method):
    """ Adds type references of a Franca IDL method. """
    for arg in list(method.in_args.values()) + list(method.out_args.values()):
        add_type_reference(arg.type, method)


def prep_attribute(attr):
    """ Adds type references of a Franca IDL attribute. """
    add_type_reference(attr.type, attr)


def prep_broadcast(broadcast):
    """ Adds type references of a Franca IDL broadcast. """
    for arg in broadcast.out_args.values():
        add_type_reference(arg.type, broadcast)


def prep_struct(struct):
    """ Adds type references of a Franca IDL struct. """
    for field in struct.fields.values():
        add_type_reference(field.type, struct)


def prep_array(array):
    """ Adds type references of a Franca IDL array. """
    add_type_reference(array.type, array)


def prep_map(ast_map):
    """ Adds type references of a Franca IDL map. """
    add_type_reference(ast_map.key_type, ast_map)
    add_type_reference(ast_map.value_type, ast_map)


def process_method_args(args):
    """ Adds ASCIIDoc for a Franca IDL method (TODO: Move down)"""
    for arg in args:
        adoc.append('| ' + get_type_name(arg.type) + ' | ' + arg.name + ' | ')
        adoc_description(arg)


def process_method(method):
    """ Adds ASCIIDoc for a Franca IDL method. """
    adoc_section_title(method)
    adoc_description(method)
    adoc_table('Input Parameters:', ['Type', 'Name', 'Description'],
               method.in_args.values(), process_method_args)
    adoc_table('Output Parameters:', ['Type', 'Name', 'Description'],
               method.out_args.values(), process_method_args)


def process_attribute(attr):
    """ Adds ASCIIDoc for a Franca IDL attribute. """
    adoc_section_title(attr)
    adoc.append('\nAttribute data type: ' + get_type_name(attr.type))
    adoc_description(attr)


def process_broadcast_args(args):
    """ Adds ASCIIDoc for a Franca IDL args (TODO: move down). """
    for arg in args:
        adoc.append('| ' + get_type_name(arg.type) + ' | ' + arg.name + ' | ')
        adoc_description(arg)


def process_broadcast(broadcast):
    """ Adds ASCIIDoc for a Franca IDL broadcast. """
    adoc_section_title(broadcast)
    adoc_description(broadcast)
    adoc_table('Output Parameters:', ['Type', 'Name', 'Description'],
               broadcast.out_args.values(), process_broadcast_args)


def process_struct_field(fields):
    """ Adds ASCIIDoc for a Franca IDL field (TODO: Move down). """
    for field in fields:
        adoc.append('|' + get_type_name(field.type) + '|' + field.name + '|')
        adoc_description(field)


def process_struct(struct):
    """ Adds ASCIIDoc for a Franca IDL struct. """
    adoc_section_title(struct)
    adoc_description(struct)
    adoc_type_references(struct)
    adoc_table('Struct fields:', ['Type', 'Name', 'Description'],
               struct.fields.values(), process_struct_field)


def process_enumerators(enumerators):
    """ Adds ASCIIDoc for a Franca IDL enumerator list (TODO: Move down). """
    enum_value = 0
    for enumerator in enumerators:
        if enumerator.value:
            enum_value = int(str(enumerator.value.value))
        adoc.append('|' + enumerator.name + '|' + str(enum_value) + '|')
        adoc_description(enumerator)
        enum_value = enum_value + 1


def process_enumeration(enum):
    """ Adds ASCIIDoc for a Franca IDL enumeration. """
    adoc_section_title(enum)
    adoc_description(enum)
    adoc_type_references(enum)
    adoc_table('', ['Enumerator', 'Values', 'Description'],
               enum.enumerators.values(), process_enumerators)


def process_array(array):
    """ Adds ASCIIDoc for a Franca IDL array. """
    adoc_section_title(array)
    adoc.append('Array element data type: ' + get_type_name(array.type) + '\n')
    adoc_description(array)
    adoc_type_references(array)


def process_map(ast_map):
    """ Adds ASCIIDoc for a Franca IDL map. """
    adoc_section_title(ast_map)
    adoc.append('Key type: ' + get_type_name(ast_map.key_type) + '\n')
    adoc.append('Value type: ' + get_type_name(ast_map.value_type) + '\n')
    adoc_description(ast_map)
    adoc_type_references(ast_map)


def adoc_major_section_title(values):
    """ Adds ASCIIDoc section title for a Franca IDL types list. """
    if values:
        adoc.append('\n== ' + list(values.values())[0].__class__.__name__ +
                    's\n')


def process_interface(package, interface):
    """ Adds ASCIIDoc for an Franca IDL interface. TODO:Use adoc_description"""
    adoc.append('\n[[' + interface.name + ']]')
    adoc.append('= Interface ' + package.name + '.' + interface.name)
    if interface.version:
        adoc.append('\nVersion: ' + str(interface.version))
    adoc.append('\nThis section is generated from the Franca IDL file for ' +
                'interface ' + interface.name + ' in package ' + package.name)
    package_descr = get_comment(package, '@description')
    if_descr = get_comment(interface, '@description')
    if package_descr:
        adoc.append('\nPackage description: ' + package_descr)
    if if_descr:
        adoc.append('\nInterface description: ' + if_descr)


def process_typecollection(package, tyco):
    """ Adds ASCIIDoc for a Franca IDL typecollection. """
    adoc.append('\n[[' + tyco.name + ']]')
    adoc.append('= Type Collection ' + package.name + '.' + tyco.name)


def process_item_lists(item_lists, funcs):
    """ Processes a list of item lists with the function table funcs """
    for item_list in item_lists:
        funcs['major_section_title'](item_list)
        for item in item_list.values():
            funcs[item.__class__](item)


adoc_funcs = {
    ast.Interface: process_interface,
    ast.TypeCollection: process_typecollection,
    ast.Attribute: process_attribute,
    ast.Method: process_method,
    ast.Broadcast: process_broadcast,
    ast.Struct: process_struct,
    ast.Enumeration: process_enumeration,
    ast.Array: process_array,
    ast.Map: process_map,
    'major_section_title': adoc_major_section_title}


type_reference_funcs = {
    ast.Interface: do_nothing,
    ast.TypeCollection: do_nothing,
    ast.Attribute: prep_attribute,
    ast.Method: prep_method,
    ast.Broadcast: prep_broadcast,
    ast.Struct: prep_struct,
    ast.Enumeration: do_nothing,
    ast.Array: prep_array,
    ast.Map: prep_map,
    'major_section_title': do_nothing
}


def iterate_fidl(processor, processing_funcs):
    """ Iterates through a Franca IDL AST. """
    for package in processor.packages.values():
        for tyco in package.typecollections.values():
            processing_funcs[ast.TypeCollection](package, tyco)
            process_item_lists([tyco.structs,
                               tyco.enumerations, tyco.arrays,
                               tyco.maps], processing_funcs)
        for interface in package.interfaces.values():
            processing_funcs[ast.Interface](package, interface)
            process_item_lists([interface.attributes,
                               interface.methods, interface.broadcasts,
                               interface.structs, interface.enumerations,
                               interface.arrays, interface.maps],
                               processing_funcs)


def main(argv):
    """ Generates ASCIDoc file from a list of Franca IDL files. """
    processor = Processor()
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
    print('Input files are: ' + str(inputfiles))
    print('Output file is: ' + str(outputfile))

    for fidl_file in inputfiles:
        try:
            processor.import_file(fidl_file.strip())
        except (LexerException, ParserException, ProcessorException) as exc:
            print("ERROR in " + fidl_file.strip() + ": " + str(exc))
            return 2

    iterate_fidl(processor, type_reference_funcs)

    iterate_fidl(processor, adoc_funcs)

    with open(outputfile, 'w', encoding='utf-8') as file:
        file.write('\n'.join(adoc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

from pyfranca import Processor, LexerException, ParserException
from pyfranca import ProcessorException, ast
import sys
import getopt

adoc = []
type_references = {}


def get_namespace(package, type):
    if isinstance(type, ast.Reference):
        type = type.reference
    return type.namespace.name


def fix_descr_intent(description):
    description_lines = description.split('\n')
    INVALID_INTENT = -1
    min_leading_spaces = INVALID_INTENT
    for line in description_lines:
        leading_spaces = 0
        for character in line:
            if character == ' ':
                leading_spaces += 1
            else:
                break
        if leading_spaces > 0 and not line.isspace():
            if min_leading_spaces == INVALID_INTENT:
                min_leading_spaces = leading_spaces
            min_leading_spaces = min(min_leading_spaces, leading_spaces)

    if min_leading_spaces == INVALID_INTENT:
        min_leading_spaces = 0
    # print ('min leading spaces: ' + str(min_leading_spaces))

    fixed_intent_lines = []
    leading_spaces = ' ' * min_leading_spaces
    for line in description_lines:
        if line.startswith(leading_spaces):
            fixed_intent_lines.append(line[min_leading_spaces:])
        else:
            fixed_intent_lines.append(line)

    return '\n'.join(fixed_intent_lines)


def get_comment(obj, type):
    comment = None
    if obj.comments and type in obj.comments:
        comment = obj.comments[type]
    return comment


def get_type_name(package, type):
    name = ''
    if isinstance(type, ast.PrimitiveType):
        name = type.name
    elif isinstance(type, ast.Array):
        if isinstance(type.type, ast.PrimitiveType):
            name = 'Array of ' + type.type.name
        else:
            if_name = get_namespace(package, type.type)
            type_name = type.type.name
            if isinstance(type.type, ast.Reference):
                type_name = type.type.reference.name
            name = 'Array of <<' + if_name + '-' + type_name + '>>'
    else:
        type_name = type.name
        if isinstance(type, ast.Reference):
            type_name = type.reference.name
        if_name = get_namespace(package, type)
        name = '<<' + if_name + '-' + type_name + '>>'
    return name


def add_type_reference(type, reference):
    global type_references
#    while isinstance(type, ast.Reference) or isinstance(type, ast.Array):
    if True:
        if isinstance(type, ast.Array):
            type = type.type
        if isinstance(type, ast.Reference):
            type = type.reference
    if type in type_references:
        type_references[type] += [reference]
    else:
        type_references[type] = [reference]


def adoc_type_references(package, type):
    global adoc
    if type in type_references:
        adoc.append('\nUsed in: ')
        for used in type_references[type]:
            # Append comma separator if not first item in list.
            if used != type_references[type][0]:
                adoc.append(', ')
            adoc.append('<<' + get_namespace(package, used) + '-' +
                        used.name + '>>')


def adoc_section_title(package, type):
    global adoc
    adoc.append('[[' + type.namespace.name + '-' + type.name + ']]')
    adoc.append('=== ' + str(type.__class__.__name__) + ' ' + type.name + '\n')


def get_adoc_link_from_name(namespace, name):
    try:
        namespace.__getitem__(name)
        return '<<' + namespace.name + '-' + name + '>>'
    except KeyError:
        return name


def adoc_description(package, type):
    global adoc
    comment_description = get_comment(type, '@description')
    comment_see = get_comment(type, '@see')
    if comment_description:
        adoc.append('\n' + fix_descr_intent(comment_description))
    if comment_see:
        sees = comment_see.split()
        adoc.append('\nSee also: ')
        comment_with_links = ''
        for see in sees:
            comment_with_links += get_adoc_link_from_name(type.namespace, see)
            comment_with_links += ' '
        adoc.append(comment_with_links)


def adoc_table(package, title, columns, entries, entries_func):
    global adoc
    if not entries:
        return
    adoc.append('\n' + title + '\n')
    adoc.append('[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    adoc.append('|' + '|'.join(columns))
    entries_func(package, entries)
    adoc.append('|===\n')


def do_nothing(*args):
    pass


def prep_method(package, method):
    for arg in list(method.in_args.values()) + list(method.out_args.values()):
        add_type_reference(arg.type, method)


def prep_attribute(package, attr):
    add_type_reference(attr.type, attr)


def prep_broadcast(package, broadcast):
    for arg in broadcast.out_args.values():
        add_type_reference(arg.type, broadcast)


def prep_struct(package, struct):
    for field in struct.fields.values():
        add_type_reference(field.type, struct)


def prep_array(package, array):
    add_type_reference(array.type, array)


def prep_map(package, map):
    add_type_reference(map.key_type, map)
    add_type_reference(map.value_type, map)


def process_method_args(package, args):
    global adoc
    for arg in args:
        adoc.append('| ' + get_type_name(package, arg.type) + ' | ' +
                    arg.name + ' | ')
        adoc_description(package, arg)


def process_method(package, method):
    adoc_section_title(package, method)
    adoc_description(package, method)
    adoc_table(package, 'Input Parameters:', ['Type', 'Name', 'Description'],
               method.in_args.values(), process_method_args)
    adoc_table(package, 'Output Parameters:', ['Type', 'Name', 'Description'],
               method.out_args.values(), process_method_args)


def process_attribute(package, attr):
    global adoc
    adoc_section_title(package, attr)
    adoc.append('\nAttribute data type: ' +
                 get_type_name(package, attr.type))
    adoc_description(package, attr)


def process_broadcast_args(package, args):
    global adoc
    for arg in args:
        adoc.append('| ' + get_type_name(package, arg.type) + ' | ' +
                    arg.name + ' | ')
        adoc_description(package, arg)


def process_broadcast(package, broadcast):
    adoc_section_title(package, broadcast)
    adoc_description(package, broadcast)
    adoc_table(package, 'Output Parameters:', ['Type', 'Name', 'Description'],
               broadcast.out_args.values(), process_broadcast_args)


def process_struct_field(package, fields):
    global adoc
    for field in fields:
        adoc.append('| ' + get_type_name(package, field.type) + ' | ' +
                    field.name + ' | ')
        adoc_description(package, field)


def process_struct(package, struct):
    adoc_section_title(package, struct)
    adoc_description(package, struct)
    adoc_type_references(package, struct)
    adoc_table(package, 'Struct fields:', ['Type', 'Name', 'Description'],
               struct.fields.values(), process_struct_field)


def process_enumerators(package, enumerators):
    global adoc
    enum_value = 0
    for en in enumerators:
        if en.value:
            enum_value = int(str(en.value.value))
        adoc.append('|' + en.name + '|' + str(enum_value) + '|')
        adoc_description(package, en)
        enum_value = enum_value + 1


def process_enumeration(package, enum):
    adoc_section_title(package, enum)
    adoc_description(package, enum)
    adoc_type_references(package, enum)
    adoc_table(package, '', ['Enumerator', 'Values', 'Description'],
               enum.enumerators.values(), process_enumerators)


def process_array(package, array):
    global adoc
    adoc_section_title(package, array)
    adoc.append('Array element data type: ' +
                get_type_name(package, array.type) + '\n')
    adoc_description(package, array)
    adoc_type_references(package, array)


def process_map(package, map):
    global adoc
    adoc_section_title(package, map)
    adoc.append('Key type: ' + get_type_name(package, map.key_type) + '\n')
    adoc.append('Value type: ' +
                get_type_name(package, map.value_type) + '\n')
    adoc_description(package, map)
    adoc_type_references(package, map)


def adoc_major_section_title(values):
    global adoc
    if values:
        adoc.append('\n== ' + list(values.values())[0].__class__.__name__ +
                    's\n')


def process_interface(package, interface):
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


def process_typecollection(package, tc):
    global adoc
    adoc.append('\n[[' + tc.name + ']]')
    adoc.append('= Type Collection ' + package.name + '.' + tc.name)


def process_item_lists(package, item_lists, funcs):
    for item_list in item_lists:
        funcs['major_section_title'](item_list)
        for item in item_list.values():
            funcs[item.__class__](package, item)


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
    for package in processor.packages.values():
        for tc in package.typecollections.values():
            processing_funcs[ast.TypeCollection](package, tc)
            process_item_lists(package, [tc.structs,
                               tc.enumerations, tc.arrays,
                               tc.maps], processing_funcs)
        for interface in package.interfaces.values():
            processing_funcs[ast.Interface](package, interface)
            process_item_lists(package, [interface.attributes,
                               interface.methods, interface.broadcasts,
                               interface.structs, interface.enumerations,
                               interface.arrays, interface.maps],
                               processing_funcs)


def main(argv):
    processor = Processor()
    inputfiles = []
    outputfile = ''
    help = 'fidl2adoc.py -i <inputfile> [-i <inputfile2>]* -o <outputfile>'
    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print(help)
        return 1
    for opt, arg in opts:
        if opt == '-h':
            print(help)
            return 0
        elif opt in ("-i", "--ifile"):
            inputfiles.append(arg)
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    print('Input files are: ' + str(inputfiles))
    print('Output file is: ' + str(outputfile))

    for fidl_file in inputfiles:
        try:
            processor.import_file(fidl_file.strip())
        except (LexerException, ParserException, ProcessorException) as e:
            print("ERROR in " + fidl_file.strip() + ": {}".format(e))
            return 2

    iterate_fidl(processor, type_reference_funcs)

    iterate_fidl(processor, adoc_funcs)

    with open(outputfile, 'w') as f:
        f.write('\n'.join(adoc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

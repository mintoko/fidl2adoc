from pyfranca import Processor, LexerException, ParserException
from pyfranca import ProcessorException, ast
import sys
import getopt

processor = Processor()
inputfiles = []
outputfile = ''
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
        # The @see comment must be a comma separated list
        sees = comment_see.split()
        adoc.append('\nSee also: ')
        comment_with_links = ''
        for see in sees:
            comment_with_links += get_adoc_link_from_name(type.namespace, see)
            comment_with_links += ' '
        adoc.append(comment_with_links)


def do_nothing(*args):
    pass


def prep_method_args(package, args, method):
    if not args:
        return
    for arg in args.values():
        add_type_reference(arg.type, method)


def prep_method(package, if_name, method, comment_descr, comment_see):
    prep_method_args(package, method.in_args, method)
    prep_method_args(package, method.out_args, method)


def prep_methods(methods):
    pass


def prep_attribute(package, interface_name, attr, attr_name, attr_type,
                   attr_type_name, comment_description, comment_see):
    add_type_reference(attr.type, attr)


def prep_attributes(attributes):
    pass


def prep_broadcast(package, if_name, method, comment_descr, comment_see):
    if not method.out_args:
        return
    for arg in method.out_args.values():
        add_type_reference(arg.type, method)


def prep_broadcasts(broadcasts):
    pass


def prep_struct(package, if_name, struct, description_comment):
    fields = struct.fields
    if (fields):
        for field in fields.values():
            add_type_reference(field.type, struct)


def prep_structs(structs):
    pass


def prep_enumeration(package, interface_name, enum, comment_description):
    pass


def prep_enumerations(enumerations):
    pass


def prep_array(package, if_name, array, comment):
    add_type_reference(array.type, array)


def prep_arrays(arrays):
    pass


def prep_map(package, map):
    add_type_reference(map.key_type, map)
    add_type_reference(map.value_type, map)

    
def prep_maps(maps):
    pass


def prep_interface(package, interface):
    pass


def prep_typecollection(package, tc):
    pass


def process_method_args(package, args, title, if_name, method_name):
    global adoc
    if not args:
        return
    # print (args)
    adoc.append(title)
    adoc.append('[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    adoc.append('|Type | Name | Description ')
    for parameter in args:
        arg = args[parameter]
        comment = ""
        if arg and arg.comments:
            comment = arg.comments['@description']
        adoc.append('| ' + get_type_name(package, arg.type) + ' | ' +
                    arg.name + ' | ' + comment)
    adoc.append('|===\n')


def process_method(package, if_name, method, comment_descr, comment_see):
    global adoc
    adoc.append('[[' + if_name + '-' + method.name + ']]')
    adoc.append('=== Method ' + method.name)
    adoc.append('')
    if comment_descr:
        adoc.append(comment_descr + '\n')
    if comment_see:
        sees = comment_see.split(',')
        adoc.append('\nSee also: ')
        for see in sees:
            adoc.append('<<' + if_name + '-' + see.strip() + '>>')
        adoc.append('\n')
    process_method_args(package, method.in_args, 'Input Parameters: ', if_name,
                        method.name)
    process_method_args(package, method.out_args, 'Output Parameters: ',
                        if_name, method.name)


def process_methods(methods):
    global adoc
    if methods:
        adoc.append('\n')
        adoc.append('== Methods')
        adoc.append('')


def process_attribute(package, interface_name, attr, attr_name, attr_type,
                      attr_type_name, comment_description, comment_see):
    global adoc
    adoc.append('\n[[' + interface_name + '-' + attr_name + ']]')
    adoc.append('=== Attribute ' + attr_name)
    adoc.append('\nAttribute data type: ' +
                get_type_name(package, attr_type))
    if comment_description:
        adoc.append('\n' + fix_descr_intent(comment_description))
    if comment_see:
        # The @see comment must be a comma separated list
        sees = comment_see.split(',')
        adoc.append('\nSee also: ')
        for see in sees:
            adoc.append('<<' + interface_name + '-' + see.strip() + '>>')


def process_attributes(attributes):
    global adoc
    if attributes:
        adoc.append('\n== Attributes\n')


def process_broadcast_args(package, args, title, if_name, method_name):
    global adoc
    if not args:
        return
    # print (args)
    adoc.append(title)
    adoc.append('[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    adoc.append('|Type | Name | Description ')
    for parameter in args:
        arg = args[parameter]
        comment = ""
        if arg and arg.comments:
            comment = arg.comments['@description']
        adoc.append('| ' + get_type_name(package, arg.type) + ' | ' +
                    arg.name + ' | ' + comment)
    adoc.append('|===\n')


def process_broadcast(package, if_name, method, comment_descr, comment_see):
    global adoc
    adoc.append('[[' + if_name + '-' + method.name + ']]')
    adoc.append('=== Broadcast ' + method.name)
    adoc.append('')
    if comment_descr:
        adoc.append(comment_descr + '\n')
    if comment_see:
        sees = comment_see.split(',')
        adoc.append('\nSee also: ')
        for see in sees:
            adoc.append('<<' + if_name + '-' + see.strip() + '>>')
        adoc.append('\n')
    process_broadcast_args(package, method.out_args, 'Output Parameters: ',
                           if_name, method.name)


def process_broadcasts(broadcasts):
    global adoc
    if broadcasts:
        adoc.append('\n== Broadcasts\n')


def process_struct_field(package, interface_name, struct, field,
                         description_comment):
    global adoc
#    comment = ""
#    if description_comment:
#        comment = description_comment
    adoc.append('| ' + get_type_name(package, field.type) + ' | ' +
                field.name + ' | ')
    adoc_description(package, field)


def process_struct(package, if_name, struct, description_comment):
    global adoc
#    struct_name = struct.name
#    adoc.append('[[' + if_name + '-' + struct_name + ']]')
#    adoc.append('=== Struct ' + struct_name + '\n')
#    if description_comment:
#        adoc.append(description_comment + '\n')
    adoc_section_title(package, struct)
    adoc_description(package, struct)
    adoc_type_references(package, struct)
    if (struct.fields):
        # print (fidl_interface.methods[method].in_args)
        adoc.append('\nStruct fields: ')
        adoc.append('[options="header",cols="20%,20%,60%"]')
        adoc.append('|===')
        adoc.append('|Type | Name | Description ')
        for field in struct.fields.values():
            comment = None
#            if field.comments and '@description' in field.comments:
#                comment = field_obj.comments['@description']
            process_struct_field(package, if_name, struct, field,
                                 comment)
        adoc.append('|===\n')


def process_structs(structs):
    global adoc
    if structs:
        adoc.append('\n== Structs\n')


def process_enumeration(package, interface_name, enum,
                        comment_description):
    global adoc
    adoc.append('[[' + interface_name + '-' + enum.name + ']]')
    adoc.append('=== Enumeration ' + enum.name)
    if comment_description:
        adoc.append('\n' + fix_descr_intent(comment_description))
    adoc_type_references(package, enum)
    adoc.append('\n[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    adoc.append('|Enumerator | Value | Description ')
    enum_value = 0
    for en in enum.enumerators.values():
#        comment = ""
#        if en.comments:
#            comment = en.comments['@description']
        if en.value:
            enum_value = int(str(en.value.value))
        adoc.append('|' + en.name + '|' + str(enum_value) + '|')
        adoc_description(package, en)
        enum_value = enum_value + 1
    adoc.append('|===')


# Starts an ASCIIDoc section for Enumerations
def process_enumerations(enumerations):
    global adoc
    if enumerations:
        adoc.append('\n== Enumerations\n')


def process_array(package, if_name, array, comment):
    global adoc
#    adoc.append('[[' + if_name + '-' + array.name + ']]')
#    adoc.append('=== Array ' + array.name + '\n')
    adoc_section_title(package, array)
    adoc.append('Array element data type: ' +
                get_type_name(package, array.type) + '\n')
#    if comment:
#        adoc.append(array.comments['@description'])
    adoc_description(package, array)
    adoc_type_references(package, array)


# Starts an ASCIIDoc section for Arrays
def process_arrays(arrays):
    global adoc
    if arrays:
        adoc.append('\n== Arrays\n')


def process_map(package, map):
    global adoc
    adoc_section_title(package, map)
    adoc.append('Key type: ' + get_type_name(package, map.key_type) + '\n')
    adoc.append('Value type: ' +
                get_type_name(package, map.value_type) + '\n')
    adoc_description(package, map)

    
def process_maps(maps):
    global adoc
    if maps:
        adoc.append('\n== Maps\n')


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


def iterate_interface(package, fidl_interface, process_typecollection,
                      process_interface, process_attributes, process_attribute,
                      process_methods, process_method,
                      process_broadcasts, process_broadcast,
                      process_structs, process_struct, process_enumerations,
                      process_enumeration, process_arrays, process_array,
                      process_maps, process_map):
    process_interface(package, fidl_interface)
    process_attributes(fidl_interface.attributes)
    for attribute in fidl_interface.attributes:
        attr = fidl_interface.attributes[attribute]
        process_attribute(package, fidl_interface.name, attr, attr.name,
                          attr.type, attr.type.name,
                          get_comment(attr, '@description'),
                          get_comment(attr, '@see'))
    process_methods(fidl_interface.methods)
    for method in fidl_interface.methods:
        method_obj = fidl_interface.methods[method]
        process_method(package, fidl_interface.name, method_obj,
                       get_comment(method_obj, '@description'),
                       get_comment(method_obj, '@see'))
    process_broadcasts(fidl_interface.broadcasts)
    for broadcast in fidl_interface.broadcasts:
        broadcast_obj = fidl_interface.broadcasts[broadcast]
        process_broadcast(package, fidl_interface.name, broadcast_obj,
                          get_comment(broadcast_obj, '@description'),
                          get_comment(broadcast_obj, '@see'))
    process_structs(fidl_interface.structs)
    for struct in fidl_interface.structs:
        struct_data = fidl_interface.structs[struct]
        process_struct(package, fidl_interface.name, struct_data,
                       get_comment(struct_data, '@description'))
    process_enumerations(fidl_interface.enumerations)
    for enumeration in fidl_interface.enumerations:
        enum = fidl_interface.enumerations[enumeration]
        process_enumeration(package, fidl_interface.name, enum,
                            get_comment(enum, '@description'))
    process_arrays(fidl_interface.arrays)
    for array in fidl_interface.arrays:
        array_data = fidl_interface.arrays[array]
        process_array(package, fidl_interface.name, array_data,
                      get_comment(array_data, '@description'))
    process_maps(fidl_interface.maps)
    for map in fidl_interface.maps.values():
        process_map(package, map)


def iterate_fidl(processor, process_typecollection, process_interface,
                 process_attributes, process_attribute,
                 process_methods, process_method,
                 process_broadcasts, process_broadcast,
                 process_structs,
                 process_struct, process_enumerations, process_enumeration,
                 process_arrays, process_array,
                 process_maps, process_map):
    # print (processor.packages.values())
    for package in processor.packages.values():
        # print (package.name)
        for typecollection in package.typecollections:
            tc = package.typecollections[typecollection]
            process_typecollection(package, tc)
            process_structs(tc.structs)
            for struct in tc.structs:
                struct_data = tc.structs[struct]
                process_struct(package, tc.name, struct_data,
                               get_comment(struct_data, '@description'))
            process_enumerations(tc.enumerations)
            for enumeration in tc.enumerations:
                enum = tc.enumerations[enumeration]
                process_enumeration(package, tc.name, enum,
                                    get_comment(enum, '@description'))
            process_arrays(tc.arrays)
            for array in tc.arrays:
                array_data = tc.arrays[array]
                process_array(package, tc.name, array_data,
                              get_comment(array_data, '@description'))
            process_maps(tc.maps)
            for map in tc.maps.values():
                process_map(package, map)
        for fidl_interface in package.interfaces.values():
            iterate_interface(package, fidl_interface, process_typecollection,
                              process_interface,
                              process_attributes, process_attribute,
                              process_methods, process_method,
                              process_broadcasts, process_broadcast,
                              process_structs, process_struct,
                              process_enumerations, process_enumeration,
                              process_arrays, process_array,
                              process_maps, process_map)


def main(argv):
    global inputfiles
    global outputfile
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

    iterate_fidl(processor, do_nothing, prep_interface,
                 prep_attributes, prep_attribute,
                 prep_methods, prep_method,
                 prep_broadcasts, prep_broadcast,
                 prep_structs,
                 prep_struct, prep_enumerations, prep_enumeration,
                 prep_arrays, prep_array, prep_maps, prep_map)

    iterate_fidl(processor, process_typecollection, process_interface,
                 process_attributes, process_attribute,
                 process_methods, process_method,
                 process_broadcasts, process_broadcast,
                 process_structs,
                 process_struct, process_enumerations, process_enumeration,
                 process_arrays, process_array, process_maps, process_map)

    with open(outputfile, 'w') as f:
        f.write('\n'.join(adoc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

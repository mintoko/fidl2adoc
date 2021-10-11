from pyfranca import Processor, LexerException, ParserException
from pyfranca import ProcessorException, ast
import sys
import getopt

processor = Processor()
inputfiles = []
outputfile = ''
adoc = []
types_list = {}
tc_int_types_map = {}


def get_namespace(package, type):
    ns = None
    try:
        type.namespace.__getitem__(type.name)
        return type.namespace.name
    except KeyError:
        print('Item ' + str(type) + ' not found in interface.')
    for tc in package.typecollections.values():
        for struct in tc.structs.values():
            if type.name == struct.name:
                return tc.name
        for enum in tc.enumerations.values():
            if type.name == enum.name:
                return tc.name
        for array in tc.arrays.values():
            if type == array.name:
                return tc.name
    return ns


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


def get_type_name(package, type, if_name):
    name = ''
    if isinstance(type, ast.PrimitiveType):
        name = type.name
    elif isinstance(type, ast.Array):
        if isinstance(type.type, ast.PrimitiveType):
            name = 'Array of ' + type.type.name
        else:
            if_name = get_namespace(package, type.type)
            name = 'Array of <<' + if_name + '-' + type.type.name + '>>'
    else:
        if_name = get_namespace(package, type)
        name = '<<' + if_name + '-' + type.name + '>>'
    return name


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
        adoc.append('| ' + get_type_name(package, arg.type, if_name) + ' | ' +
                    arg.name + ' | ' + comment)
        if arg.type.name in types_list:
            # Todo: check used in for inline arrays
            types_list[arg.type.name] += [method_name]
        else:
            types_list[arg.type.name] = [method_name]

    adoc.append('|===\n')


def process_method(package, if_name, method, comment_descr, comment_see):
    global types_list
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


def process_attribute(package, interface_name, attr_name, attr_type,
                      attr_type_name, comment_description, comment_see):
    global types_list
    global adoc
    adoc.append('\n[[' + interface_name + '-' + attr_name + ']]')
    adoc.append('=== Attribute ' + attr_name)
    adoc.append('\nAttribute data type: ' +
                get_type_name(package, attr_type, interface_name))
    if attr_type_name in types_list:
        types_list[attr_type_name] = types_list[attr_type_name] + [attr_name]
    else:
        types_list[attr_type_name] = [attr_name]
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
        adoc.append('| ' + get_type_name(package, arg.type, if_name) + ' | ' +
                    arg.name + ' | ' + comment)
        if arg.type.name in types_list:
            # Todo: check used in for inline arrays
            types_list[arg.type.name] += [method_name]
        else:
            types_list[arg.type.name] = [method_name]

    adoc.append('|===\n')


def process_broadcast(package, if_name, method, comment_descr, comment_see):
    global types_list
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
        adoc.append('\n')
        adoc.append('== Broadcasts')
        adoc.append('')


def process_struct_field(package, interface_name, struct, field,
                         description_comment):
    global types_list
    global adoc
    comment = ""
    if description_comment:
        comment = description_comment
    adoc.append('| ' + get_type_name(package, field.type, interface_name) +
                ' | ' + field.name + ' | ' + comment)
    if field.type.name in types_list:
        types_list[field.type.name] += [struct.name]
    else:
        types_list[field.type.name] = [struct.name]


def process_struct(package, if_name, struct, description_comment):
    global types_list
    global adoc
    struct_name = struct.name
    adoc.append('[[' + if_name + '-' + struct_name + ']]')
    adoc.append('=== Struct ' + struct_name + '\n')
    if description_comment:
        adoc.append(description_comment + '\n')
        if struct_name in types_list:
            adoc.append('\nUsed in: ')
            for used in types_list[struct_name]:
                adoc.append('<<' + if_name + '-' + used + '>>')
        fields = struct.fields
        if (fields):
            # print (fidl_interface.methods[method].in_args)
            adoc.append('\nStruct fields: ')
            adoc.append('[options="header",cols="20%,20%,60%"]')
            adoc.append('|===')
            adoc.append('|Type | Name | Description ')
            for field in fields:
                comment = None
                field_obj = fields[field]
                if field_obj.comments and '@description' in field_obj.comments:
                    comment = field_obj.comments['@description']
                process_struct_field(package, if_name, struct, field_obj,
                                     comment)
            adoc.append('|===\n')
        else:
            print('ERROR: No struct fields found\n')


def process_structs(structs):
    global adoc
    if structs:
        adoc.append('\n== Structs\n')


def process_enumeration(package, interface_name, enum,
                        comment_description):
    global types_list
    adoc.append('[[' + interface_name + '-' + enum.name + ']]')
    adoc.append('=== Enumeration ' + enum.name)
    if comment_description:
        adoc.append('\n' + fix_descr_intent(comment_description))
    if enum.name in types_list:
        adoc.append('\nUsed in: ')
        for used in types_list[enum.name]:
            adoc.append('<<' + interface_name + '-' + used + '>>')
    adoc.append('\n[options="header",cols="20%,20%,60%"]')
    adoc.append('|===')
    adoc.append('|Enumerator | Value | Description ')
    enum_value = 0
    for en in enum.enumerators.values():
        comment = ""
        if en.comments:
            comment = en.comments['@description']
        if en.value:
            enum_value = int(str(en.value.value))
        adoc.append('|' + en.name + '|' + str(enum_value) + '|' + comment)
        enum_value = enum_value + 1
    adoc.append('|===')


# Starts an ASCIIDoc section for Enumerations
def process_enumerations(enumerations):
    global adoc
    if enumerations:
        adoc.append('== Enumerations\n')


def process_array(package, if_name, array, comment):
    adoc.append('[[' + if_name + '-' + array.name + ']]')
    adoc.append('=== Array ' + array.name + '\n')
    adoc.append('Array element data type: ' +
                get_type_name(package, array.type, if_name) + '\n')
    if comment:
        adoc.append(array.comments['@description'])
    if array.name in types_list:
        adoc.append('\nUsed in: ')
        for used in types_list[array.name]:
            adoc.append('<<' + if_name + '-' + used + '>>')


# Starts an ASCIIDoc section for Arrays
def process_arrays(arrays):
    global adoc
    if arrays:
        adoc.append('\n== Arrays\n')


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


def iterate_interface(package, fidl_interface, process_typecollection, process_structs,
                 process_struct, process_enumerations, process_enumeration,
                 process_arrays, process_array):
    process_interface(package, fidl_interface)
    process_attributes(fidl_interface.attributes)
    for attribute in fidl_interface.attributes:
        attr = fidl_interface.attributes[attribute]
        process_attribute(package, fidl_interface.name, attr.name, attr.type,
                          attr.type.name,
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


def iterate_fidl(processor, process_typecollection, process_structs,
                 process_struct, process_enumerations, process_enumeration,
                 process_arrays, process_array):
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
        for fidl_interface in package.interfaces.values():
            iterate_interface(package, fidl_interface, process_typecollection, process_structs,
                 process_struct, process_enumerations, process_enumeration,
                 process_arrays, process_array)


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

    iterate_fidl(processor, process_typecollection, process_structs,
                 process_struct, process_enumerations, process_enumeration,
                 process_arrays, process_array)

    with open(outputfile, 'w') as f:
        f.write('\n'.join(adoc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

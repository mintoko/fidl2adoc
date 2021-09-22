from pyfranca import Processor, LexerException, ParserException, ProcessorException, ast

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
        if leading_spaces > 0:
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

processor = Processor()

import sys, getopt
inputfiles = []
outputfile = ''

def main(argv):
   global inputfiles
   global outputfile
   try:
      opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
   except getopt.GetoptError:
      print ('test.py -i <inputfile> -o <outputfile>')
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print ('test.py -i <inputfile> -o <outputfile>')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfiles.append(arg)
      elif opt in ("-o", "--ofile"):
         outputfile = arg
   print ('Input files are: ' + str(inputfiles))
   print ('Output file is: ' + str(outputfile))

if __name__ == "__main__":
   main(sys.argv[1:])
   
adoc = []

for fidl_file in inputfiles:
    try:
        processor.import_file(fidl_file.strip())        
    except (LexerException, ParserException, ProcessorException) as e:
        print("ERROR in " + fidl_file.strip() + ": {}".format(e)) 


# Test fidl file with methods (parameters in tables), attributes, enumerator description, see/description, used in

# Not yet supported:
# TypeCollections
# Inline Array Definition
# Broadcasts
# HTML linking for Enumerations used in Arrays
# interface version
# Out parameters from methods

types_list = {}

# print (processor.packages.values())
for package in processor.packages.values() :
    # print (package.name)
    for fidl_interface in package.interfaces.values():
        adoc.append('\n[[' + fidl_interface.name + ']]')
        adoc.append('= Interface ' + package.name + '.' + fidl_interface.name)
        adoc.append('\nThis section is generated from the FIDL file for ' +
           'interface ' + fidl_interface.name + ' in package ' + package.name)
        if package.comments and '@description' in package.comments:
            adoc.append('\nPackage description: ' + package.comments['@description'])
        if fidl_interface.comments and '@description' in fidl_interface.comments:
            adoc.append('\nInterface description: ' + fidl_interface.comments['@description'])
        # print (fidl_interface.name)
        adoc.append('\n== Attributes\n')
        for attribute in fidl_interface.attributes:
            adoc.append('\n[[' + fidl_interface.name + '-' + fidl_interface.attributes[attribute].name + ']]')
            adoc.append('=== Attribute ' + fidl_interface.attributes[attribute].name)
            attribute_type = fidl_interface.attributes[attribute].type.name
            if isinstance(fidl_interface.attributes[attribute].type, ast.PrimitiveType) :
                adoc.append('\nAttribute data type: ' + attribute_type)
            else :
                adoc.append('\nAttribute data type: <<' + fidl_interface.name + '-' + attribute_type + '>>')
            if attribute_type in types_list:
                types_list[attribute_type] = types_list[attribute_type] + [fidl_interface.attributes[attribute].name]
            else :
                types_list[attribute_type] = [fidl_interface.attributes[attribute].name]
            if '@description' in fidl_interface.attributes[attribute].comments:
                adoc.append('\n' + fix_descr_intent(fidl_interface.attributes[attribute].comments['@description']))
            if '@see' in fidl_interface.attributes[attribute].comments:
                sees = fidl_interface.attributes[attribute].comments['@see'].split(',')
                adoc.append('\nSee also: ')
                for see in sees:
                    adoc.append('<<' + fidl_interface.name + '-' + see.strip() + '>>')
        adoc.append('\n')
        adoc.append('== Methods')
        adoc.append('')
        for method in fidl_interface.methods:
            adoc.append('[[' + fidl_interface.name + '-' + fidl_interface.methods[method].name + ']]')  
            adoc.append('=== Method ' + fidl_interface.methods[method].name)
            adoc.append('')
            if '@description' in fidl_interface.methods[method].comments:
                adoc.append(fidl_interface.methods[method].comments['@description'] + '\n')
            if '@see' in fidl_interface.methods[method].comments:
                sees = fidl_interface.methods[method].comments['@see'].split(',')
                adoc.append('\nSee also: ')
                for see in sees:
                    adoc.append('<<' + fidl_interface.name + '-' + see.strip() + '>>')
            adoc.append('\n')
            in_args = fidl_interface.methods[method].in_args
            if (in_args) :
                # print (fidl_interface.methods[method].in_args)
                adoc.append('Input Parameters: ')
                adoc.append('[options="header",cols="20%,20%,60%"]')
                adoc.append('|===')
                adoc.append('|Type | Name | Description ')
                for parameter in in_args :
                    in_arg = in_args[parameter]
                    comment = ""
                    if in_arg.comments :
                        comment = in_arg.comments['@description']
                    if in_arg and in_arg.name and in_arg.type:
                        type_name = in_arg.type.name
                        if not type_name:
                            type_name = str(in_arg.type)
                        if isinstance(in_arg.type, ast.PrimitiveType) :
                            adoc.append('|' + in_arg.type.name + ' | ' + in_arg.name + ' | ' + comment)
                        else :
                            adoc.append('| <<' + fidl_interface.name + '-' + type_name + '>> | ' + in_arg.name + ' | ' + comment)
                        if in_arg.type.name in types_list:
                            types_list[in_arg.type.name] = types_list[in_arg.type.name] + [fidl_interface.methods[method].name]
                        else :
                            types_list[in_arg.type.name] = [fidl_interface.methods[method].name]
                    else:
                        adoc.append('Parse error, see: ' + comment)
            # print (fidl_interface.methods[method].comments)
            # print (method)
            # print (fidl_interface.methods[method].in_args)
                adoc.append('|===\n')
            else :
                adoc.append('No parameters\n')
        # print (types_list)
		
        adoc.append('\n== Structs\n')
        for struct in fidl_interface.structs:
            struct_data = fidl_interface.structs[struct]
            struct_name = struct_data.name
            adoc.append('[[' + fidl_interface.name + '-' + struct_name + ']]')
            adoc.append('=== Struct ' + struct_name + '\n')
            if struct_data.comments :
                adoc.append(struct_data.comments['@description'] + '\n')
            if struct_name in types_list:
                adoc.append('\nUsed in: ')
                for used in types_list[struct_name]:
                    adoc.append('<<' + fidl_interface.name + '-' + used + '>>')
            fields = struct_data.fields
            if (fields) :
                # print (fidl_interface.methods[method].in_args)
                adoc.append('\nStruct fields: ')
                adoc.append('[options="header",cols="20%,20%,60%"]')
                adoc.append('|===')
                adoc.append('|Type | Name | Description ')
                for field in fields :
                    field_data = fields[field]
                    comment = ""
                    if field_data.comments :
                        comment = field_data.comments['@description']
                    if isinstance(field_data.type, ast.PrimitiveType) :
                        adoc.append('|' + field_data.type.name + ' | ' + field_data.name + ' | ' + comment)
                    else :
                        adoc.append('| <<' + fidl_interface.name + '-' + field_data.type.name + '>> | ' + field_data.name + ' | ' + comment)
                    if field_data.type.name in types_list:
                        types_list[field_data.type.name] = types_list[field_data.type.name] + [struct_data.name]
                    else :
                        types_list[field_data.type.name] = [struct_data.name]
                adoc.append('|===\n')
            else :
                print ('ERROR: No struct fields found\n')				
				
        adoc.append('== Enumerations\n')
        for enumeration in fidl_interface.enumerations:
            enum = fidl_interface.enumerations[enumeration]
            enum_name = enum.name
            adoc.append('[[' + fidl_interface.name + '-' + enum_name + ']]')            
            adoc.append('=== Enumeration ' + enum_name + '\n')
            if enum.comments :
                adoc.append(enum.comments['@description'])
				
            if enum.name in types_list:
                adoc.append('\nUsed in: ')
                for used in types_list[enum.name]:
                    adoc.append('<<' + fidl_interface.name + '-' + used + '>>')
            adoc.append('\n[options="header",cols="20%,20%,60%"]')
            adoc.append('|===')
            adoc.append('|Enumerator | Value | Description ')
            enum_value = 0
            for enumerator in enum.enumerators :
			
#                print (enumerator)
                en = enum.enumerators[enumerator]
                comment = ""
                if en.comments :
                    comment = en.comments['@description']
                if en.value :
                    enum_value = int(str(en.value.value))
                adoc.append('|' + en.name + '|' + str(enum_value) + '|' + comment)
                enum_value = enum_value + 1
            adoc.append('|===')

        adoc.append('\n== Arrays\n')
        for array in fidl_interface.arrays:
            array_data = fidl_interface.arrays[array]
            array_name = array_data.name
            adoc.append('[[' + fidl_interface.name + '-' + array_name + ']]')            
            adoc.append('=== Array ' + array_name + '\n')
            if isinstance(array_data.type, ast.PrimitiveType) :
                adoc.append('Array element data type: ' + array_data.type.name)
            else :
                adoc.append('Array element data type: <<' + fidl_interface.name + '-' + array_data.type.name + '>>')
            if array_data.comments :
                adoc.append(array_data.comments['@description'])
				
            if array_name in types_list:
                adoc.append('\nUsed in: ')
                for used in types_list[array_name]:
                    adoc.append('<<' + fidl_interface.name + '-' + used + '>>')
					
    # print (types_list)

with open(outputfile, 'w') as f:
    f.write('\n'.join(adoc))
	

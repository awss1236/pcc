from back import desugar_code
import os
import sys

compile_cmd = 'gcc'
temps = []
no_delete_temps = False
for arg in sys.argv[1:]:
    compile_cmd += ' '
    arg = arg.strip()
    if arg[0] == '-':
        if arg == '--no-delete-pps':
            no_delete_temps = True
        else:
            compile_cmd = compile_cmd + arg
        continue
    if arg.endswith('.c') or arg.endswith('.h'):
        newname = arg + '.temporaryout' + arg[-2:]
        compile_cmd = compile_cmd + newname
        code = open(arg).read()
        newcode = desugar_code(code)
        open(newname, 'w').write(newcode)
        temps.append(newname)
        continue
    compile_cmd = compile_cmd + arg
#print(compile_cmd)
os.system(compile_cmd)

if no_delete_temps:
    exit()

for temp in temps:
    #print('rm ' + temp)
    os.system('rm ' + temp)

from tree_sitter import Parser, Language, Query, QueryCursor, Point
import tree_sitter_c as tsc

clang = Language(tsc.language())
parser = Parser(clang)

basetypes = [
b'signed char', b'short', b'int', b'long', b'long long',
b'char', b'unsigned short', b'unsigned int', b'unsigned long', b'unsigned long long',
b'float', b'double', b'long double',
b'pointer'
]

oper_to_str = {'+': b'add', '-': b'sub', '*': b'mul', '/': b'div'}

def get_oper_str(o):
    if o in oper_to_str:
        return oper_to_str[o]
    print('UNSUPPORTED OPERATION: ' + o)
    return b'add'

#print(tree.root_node)

def get_declarator_pcount_name(decl):
    if decl.type == 'identifier':
        return 0, decl.text
    if decl.type == 'function_declarator':
        return 0, decl.child(0).text
    if decl.type == 'init_declarator':
        return 0, decl.child(0).text
    if decl.type == 'pointer_declarator':
        res = get_declarator_pcount_name(decl.child(1))
        if res is not None:
            c, n = res
            return c+1, n
    return None

def get_function_type(name, root):
    decl = QueryCursor(Query(clang,
        f"""
          (declaration
            type: (_) @type
            declarator: (_) @decl
          )
          (function_definition
            type: (_) @type
            declarator: (_) @decl
          )
        """))
    col = decl.matches(root)
    for _, m in col:
        res = get_declarator_pcount_name(m['decl'][0])
        if res is None:
            continue
        if res[1] == name:
            return res[0], m['type'][0].text
    print("failed to find function with name: " + name.decode())
    return None

def get_ident_type(name, node):
    declordef = QueryCursor(Query(clang,
        f"""
          (declaration
            type: (_) @type
            declarator: (_) @decl
          )
        """))
    col = declordef.matches(node)
    for (_, match) in col:
        base_type = match['type'][0].text
        res = get_declarator_pcount_name(match['decl'][0])
        if res is not None:
            if res[1] == name:
                return res[0], base_type

    if node.type == 'function_definition':
        param_list = node.child(1).child(1)
        for i in param_list.children:
            if i.type == '(' or i.type == ')' or i.type == ',':
                continue
            base_type = i.child(0).text
            res = get_declarator_pcount_name(i.child(1))
            if res is not None:
                if res[1] == name:
                    return res[0], base_type

    if node.parent == None:
        print("couldn't find the type for " + name.decode())
        return None
    else:
        return get_ident_type(name, node.parent)

def get_number_type(num):
    num = num.lower()
    isdeci = b'.' in num
    if b'u' in num:
        if b'll' in num:
            return b'unsigned long long'
        if b'l' in num:
            return b'unsigned long'
        return b'unsigned int'
    if b'll' in num:
        return b'long long'
    if b'l' in num:
        return b'long double' if isdeci else b'long'
    if b'f' in num:
        return b'float'

    if isdeci:
        return b'double'
    else:
        return b'int'

def get_desc_type(cast):
    if cast.child_count == 1:
        return 0, cast.child(0).text
    i = 1
    d = cast.child(1)
    while d.child_count > 1:
        d = d.child(1)
        i = i+1
    return i, cast.child(0).text

def get_comb_type(t1, t2):
    def isfloat(t):
        return t in [b'float', b'double', b'long double']

    if isfloat(t1) or isfloat(t2):
        if t2 == b'long double' or t1 == b'long double':
            return b'long double'
        if t2 == b'double' or t1 == b'double':
            return b'double'
        return b'float'
    def issmall(t):
        return t in [b'char', b'signed char', b'short', b'unsigned short']
    if issmall(t1) and issmall(t2):
        return b'int'
    if issmall(t1):
        return t2
    if issmall(t2):
        return t1
    if t1 == t2:
        return t1

    if (t1 == b'unsigned int' and t2 == b'long long') or (t2 == b'unsigned int' and t1 == b'long long'):
        return b'long long'

    t = b''
    if b'unsigned' in t1 or b'unsigned' in t2:
        t = t + b'unsigned'
        if b'unsigned' in t1:
            t1 = t1[9:]
        if b'unsigned' in t2:
            t2 = t2[9:]

    combs = {
        (b'int', b'long'): b'long',
        (b'int', b'long long'): b'long long',
        (b'long', b'long long'): b'long long',
    }

    if (t1, t2) in combs:
        t = t + combs[t1, t2]
    else:
        t = t + combs[t2, t1]
    
    return t

def get_struct_def(name, root):
    decl = QueryCursor(Query(clang,
        f"""
          (type_definition
            type: (_) @type
            declarator: (_) @decl
          )
        """))
    col = decl.matches(root)
    for _, m in col:
        print(m)
        decl = m['decl'][0]
        print(decl)
        res = get_declarator_pcount_name(decl)
        if res is not None:
            print('--------------------', res)

def get_expr_type(expr, root):
    if expr.type == 'identifier':
        return get_ident_type(expr.text, expr)
    if expr.type == 'call_expression':
        return get_function_type(expr.child(0).text, root)
    if expr.type == 'parenthesized_expression':
        return get_expr_type(expr.child(1))
    if expr.type == 'pointer_expression':
        c, inner_type = get_expr_type(expr.child(1))
        i = -1
        if expr.child(0).text == b'&':
            i = 1
        return c+i, inner_type
    if expr.type == 'cast_expression':
        return get_desc_type(expr.child(1))
    if expr.type == 'field_expression': # -> syntax arrow
        _, struct_type = get_expr_type(expr.child(0), root)
        struct_def = get_struct_def(struct_type, root)
        # find the definition of said structure somehow
        # do the yammy jammy ig

    if expr.type == 'number_literal':
        return 0, get_number_type(expr.text)
    if expr.type == 'binary_expression':
        lt = get_expr_type(expr.child(0))
        rt = get_expr_type(expr.child(2))
        op = expr.child(1).text.strip()
        if lt[0] != 0 or rt[0] != 0:
            return 0, b'pointer'
        return 0, get_comb_type(lt[1], rt[1])

    print('UNHANDLED EXPRESSION TYPE: '+expr.type)
    return 0, basetypes[0]

def sort_ops(col):
    def get_depth(n):
        if n.parent == None:
            return 0
        return 1 + get_depth(n.parent)
    xs = [(get_depth(c['expr'][0]), (i, c)) for i, c in col]
    xs = sorted(xs, key=lambda a:a[0], reverse=True)
    return [c for _, c in xs]

def desugar_code(code):
    tree = parser.parse(bytes(code, "utf8"))
    print(tree.root_node)
    query = Query(clang,
    """
    (binary_expression left: (_) @left right: (_) @right) @expr
    """
    )
    query_cur = QueryCursor(query)
    done = False
    while not done:
        col = query_cur.matches(tree.root_node)
        done = True

        col = sort_ops(col)

        for _, match in col:
            expr = match['expr'][0]

            left = match['left'][0]
            lefttype = get_expr_type(left, tree.root_node)
            right = match['right'][0]
            righttype = get_expr_type(right, tree.root_node)
            oper = code[left.byte_range[1]:right.byte_range[0]].strip()

            if not lefttype or not righttype:
                continue

            if lefttype[0] != 0:
                lefttype = b'pointer'
            else:
                lefttype = lefttype[1]
            if righttype[0] != 0:
                righttype = b'pointer'
            else:
                righttype = righttype[1]

            if (lefttype in basetypes) and (righttype in basetypes):
                continue
            lefttype = lefttype.replace(b' ', b'')
            righttype = righttype.replace(b' ', b'')

            lefttext = left.text
            righttext = right.text
            if right.type == 'parenthesized_expression':
                righttext = right.text[1:-1]
            if left.type == 'parenthesized_expression':
                lefttext = left.text[1:-1]
            newstr = b'oper'+lefttype+get_oper_str(oper)+righttype+b'('+lefttext+b','+righttext+b')'
            code = code[:expr.byte_range[0]] + newstr.decode() + code[expr.byte_range[1]:]
            tree.edit(expr.byte_range[0], expr.byte_range[1], expr.byte_range[0] + len(newstr), expr.start_point, expr.end_point, Point(expr.start_point.row, expr.start_point.column+len(newstr)))
            tree = parser.parse(bytes(code, 'utf8'), old_tree = tree)
            done = False
            break
        #print('--------------------------------------------------------------------------------------------------------------------------------------------------------')
        #print('--------------------------------------------------------------------------------------------------------------------------------------------------------')
        #print(code)
        #print(tree.root_node)
    return code

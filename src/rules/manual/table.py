from .pythonrepl import checks
from .shell import shell_predicates

# code-domain predicates
predicate_table = {}
for id in checks:
    for check_func in checks[id]:
        predicate_table[check_func.__name__] = check_func

for name, func in shell_predicates.items():
    predicate_table[name] = func
    
# print( "' | '".join(predicate_table.keys()))
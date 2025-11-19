# lab4/semantic_analyzer.py Balys Žalneravičius. Kodo generavimui naudota Gemini Flash 2.5
import sys

# saugoti informacijai apie kintamąjį
class SymbolEntry:
    def __init__(self, name, data_type, is_const):
        self.name = name
        self.data_type = data_type
        self.is_const = is_const

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = {}
        self.errors = []
        self.current_scope = "main" # analizuojame tik main

    def _error(self, message):
        error_msg = f"[SEMANTINĖ KLAIDA] {message}"
        self.errors.append(error_msg)
        print(error_msg, file=sys.stderr)
    # pagrindinė funkcija kuri naršo AST 
    def analyze(self, ast_root_node):
        if ast_root_node is None:
            return False
        
        # Pradedame nuo PROGRAM
        main_function = next((c for c in ast_root_node.children if c.kind == "FUNCTION_MAIN"), None)
        
        if main_function:
            self.visit_function_main(main_function)
        else:
            self._error("Nerasta pagrindinė 'int main()' funkcija.")

        if not self.errors:
            print("Analizė sėkmingai baigta. Klaidų nerasta.")
            return True
        else:
            print(f"Analizė baigta su {len(self.errors)} klaidomis.")
            return False

    def visit_function_main(self, node):
        for statement in node.children:
            self.visit_statement(statement)

    def visit_statement(self, node):
        if node.kind == "VAR_DECL":
            self.visit_var_decl(node)
        elif node.kind == "PRINTF_CALL":
            self.visit_printf_call(node)
        elif node.kind == "RETURN":
            self.visit_return(node)
    
    # Deklaracijos ir simbolių lentelės valdymas
    def visit_var_decl(self, node):
        name = node.value
        
        # 1. Dvigubos deklaracijos patikra
        if name in self.symbol_table:
            self._error(f"Kintamasis '{name}' jau deklaruotas.")
            return

        data_type = next((c.value for c in node.children if c.kind == "TYPE"), "int")
        is_const = next((c.value == 'True' for c in node.children if c.kind == "CONST"), False)
        
        # Pridedame į simbolių lentelę
        self.symbol_table[name] = SymbolEntry(name, data_type, is_const)
        print(f"  [SIMBOLIS] Pridėtas: {data_type}{' const' if is_const else ''} {name}")

        # ar išraiška naudoja tik deklaruotus kintamuosius
        assign_node = next((c for c in node.children if c.kind == "ASSIGN_VALUE"), None)
        if assign_node and assign_node.children:
            expression_node = assign_node.children[0]
            self.check_expression_types(expression_node)

    # Rekursyvi funkcija tipams tikrinti
    def check_expression_types(self, node):
        if node.kind == "LITERAL":
            # Visi skaičiai laikomi 'int'
            return "int"
            
        elif node.kind == "VAR_REF":
            return self.visit_var_ref(node)
            
        elif node.kind == "BIN_OP":
            # tikriname, ar vaikai yra int.
            left_type = self.check_expression_types(node.children[0])
            right_type = self.check_expression_types(node.children[1])
            
            # tipų suderinamumo patikrinimas
            if left_type == "int" and right_type == "int":
                return "int"
            else:
                self._error(f"Tipų neatitikimas operacijoje '{node.value}'. Tikimasi 'int'.")
                return "error"
            
        return "error" 

    # Tikrina, ar kintamasis buvo deklaruotas.
    def visit_var_ref(self, node):
        name = node.value
        
        # Deklaracijos patikrinimas
        if name not in self.symbol_table:
            self._error(f"Kintamasis '{name}' nebuvo deklaruotas. (Nenaudojamo kintamojo klaida)")
            return "error"

        return self.symbol_table[name].data_type

    # Tikrina printf
    def visit_printf_call(self, node):
        format_string = node.value
        arg_name = node.children[0].value
        
        # ar argumentas deklaruotas?
        if arg_name not in self.symbol_table:
            self._error(f"Printf argumentas '{arg_name}' nėra deklaruotas kintamasis.")
        else:
            entry = self.symbol_table[arg_name]
            if entry.data_type != "int":
                 self._error(f"Printf tikėtasi 'int', bet gautas kintamasis '{arg_name}' yra '{entry.data_type}'.")
    
    # Tikrina, ar main grąžina int
    def visit_return(self, node):
        if node.children:
            expr_type = self.check_expression_types(node.children[0])
            if expr_type != "int":
                self._error(f"Funkcija 'main' reikalauja grąžinti 'int', gauta '{expr_type}'.")
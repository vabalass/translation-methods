# III. Sintaksinio analizatoriaus projektavimas ir realizavimas rekursyvaus nusileidimo metodu:
# 1. konstruoti analizės lenteles ir FIRST, FOLLOW aibes
# 2. rašyti rekursyvaus nusileidimo kodą
# 3. pasiieškoti gero instrumento AST formavimui, arba tokį parašyti
import re
import sys
import os

# --- I. AST Mazgo Bazinė Klasė ---
class ASTNode:
    """Abstraktusis Sintaksės Medžio (AST) mazgo bazinė klasė."""
    def __init__(self, kind, children=None, value=None):
        self.kind = kind
        self.children = children if children is not None else []
        self.value = value
    
    def __repr__(self):
        if self.value is not None:
            return f"<{self.kind} val='{self.value}'>"
        return f"<{self.kind} ({len(self.children)} children)>"

    def pretty_print(self, indent=0):
        """Funkcija, skirta gražiai atspausdinti medį (pagelbėja debug'inimui)."""
        print('    ' * indent + f"[{self.kind}]" + (f": {self.value}" if self.value is not None else ""))
        for child in self.children:
            if isinstance(child, ASTNode):
                child.pretty_print(indent + 1)
            else:
                print('    ' * (indent + 1) + str(child))

# --- II. Parserio Klasė (Rekursyvinis Nusileidimas) ---
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.errors = []
        
        # Pirmą kartą praleidžiame visus nereikalingus žetonus (tarpus, komentarus, naujas eilutes)
        self._skip_insignificant_tokens() 

    def _error(self, expected_kinds):
        """Išmeta sintaksės klaidą su tikėtinais žetonų tipais."""
        if self.current_token_index < len(self.tokens):
            kind, value, line = self.tokens[self.current_token_index]
            error_msg = f"Sintaksės klaida eilutėje {line}: Lauktas {', '.join(expected_kinds)}, gautas {kind} ('{value}')."
        else:
            # Reikšminga klaida: baigėsi failas per anksti
            error_msg = f"Sintaksės klaida: Lauktas {', '.join(expected_kinds)}, bet pasiekta kodo pabaiga."
        
        self.errors.append(error_msg)
        raise SyntaxError(error_msg)

    def _peek(self):
        """Grąžina dabartinio žetono tipą, arba 'EOF'."""
        if self.current_token_index < len(self.tokens):
            return self.tokens[self.current_token_index][0]
        return "EOF"
    
    def _skip_insignificant_tokens(self):
        """Perkelia indeksą per NEWLINE, SKIP ir COMMENT žetonus."""
        while self.current_token_index < len(self.tokens):
            kind = self.tokens[self.current_token_index][0]
            if kind in ("NEWLINE", "SKIP", "COMMENT"):
                self.current_token_index += 1
            else:
                break


    def _consume(self, expected_kind):
        """Suvartoja ir grąžina žetoną, jei jo tipas sutampa su tikėtinu, ir praleidžia tarpus."""
        if self._peek() == expected_kind:
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            self._skip_insignificant_tokens() # PRALEIDŽIAME nereikšmingus žetonus po vartojimo
            return token
        
        self._error([expected_kind])

    def parse(self):
        """Pradeda analizavimą nuo <program> taisyklės."""
        try:
            ast = self.parse_program()
            # Patikrinimas ar pasiekta failo pabaiga po programos
            if self._peek() != "EOF":
                self._error(["EOF"])
            return ast
        except SyntaxError:
            print("\nAnalizavimas baigtas su klaidomis.")
            # Atspausdiname visas surinktas klaidas
            for err in self.errors:
                print(f"-> {err}")
            return None

    # --- BNF TAISYKLIŲ METODAI ---
    # Taisyklė: <program> ::= <include_stmt>* <main_function>
    # Dabar <include_stmt> yra NEPrivaloma!
    def parse_program(self):
        elements = []
        
        # 1. <include_stmt>* (leidžiame kelias arba nulis include eilutes)
        while self._peek() == "INCLUDE_KW":
            elements.append(self.parse_include_stmt())
            
        # 2. <main_function> (privalomas)
        if self._peek() == "INT_KW":
            elements.append(self.parse_main_function())
        else:
            self._error(["INT_KW (main funkcijos apibrėžimas)"])

        return ASTNode("PROGRAM", children=elements)

    # Taisyklė: <include_stmt> ::= INCLUDE_KW LT IDENTIFICATOR GT SEMICOLON (arba NEWLINE, bet čia NEWLINE bus praleistas)
    def parse_include_stmt(self):
        self._consume("INCLUDE_KW")
        self._consume("LT") # <
        
        header_name = self._consume("IDENTIFICATOR") # pvz., stdio.h
        
        self._consume("GT") # >
        # Nereikalaujame NEWLINE, nes jis bus praleistas _skip_insignificant_tokens()

        return ASTNode("INCLUDE", value=header_name[1])

    # Taisyklė: <main_function> ::= INT_KW MAIN_KW LPAREN RPAREN LBRACE <statement_list> RBRACE
    def parse_main_function(self):
        self._consume("INT_KW")
        self._consume("MAIN_KW")
        self._consume("LPAREN")
        self._consume("RPAREN")
        self._consume("LBRACE")

        statements = self.parse_statement_list()

        self._consume("RBRACE")
        # Nereikalaujame NEWLINE

        return ASTNode("FUNCTION_MAIN", children=statements, value="int main")

    # Taisyklė: <statement_list> ::= <statement>*
    def parse_statement_list(self):
        statements = []
        # Statements tikrinami tol, kol pasiekiamas } (RBRACE)
        while self._peek() != "RBRACE":
            statements.append(self.parse_statement())
        return statements

    # Taisyklė: <statement> ::= <declaration_assignment> | <return_stmt> | <printf_call>
    def parse_statement(self):
        token_kind = self._peek()

        if token_kind in ("CONST_KW", "INT_KW"):
            return self.parse_declaration_assignment()
        elif token_kind == "RETURN_KW":
            return self.parse_return_stmt()
        elif token_kind == "PRINTF_KW":
            return self.parse_printf_call()
        else:
            # Jei joks raktinis žodis neatpažįstamas, tikriname, ar tai ne RBRACE, kuris turėtų baigti statements
            if token_kind == "RBRACE":
                 self._error(["CONST_KW", "INT_KW", "RETURN_KW", "PRINTF_KW"])
            else:
                self._error(["CONST_KW", "INT_KW", "RETURN_KW", "PRINTF_KW", "arba RBRACE"])

    # Taisyklė: <declaration_assignment> ::= (CONST_KW)? INT_KW IDENTIFICATOR EQUAL <expression> SEMICOLON
    def parse_declaration_assignment(self):
        is_const = False
        if self._peek() == "CONST_KW":
            self._consume("CONST_KW")
            is_const = True
        
        self._consume("INT_KW") # int
        identifier = self._consume("IDENTIFICATOR")
        
        assignment_node = ASTNode("VAR_DECL", 
                                  value=identifier[1], 
                                  children=[ASTNode("TYPE", value="int"), ASTNode("CONST", value=str(is_const))])
        
        # Priskyrimo dalis (EQUAL <expression>)
        self._consume("EQUAL")
        expression = self.parse_expression()
        assignment_node.children.append(ASTNode("ASSIGN_VALUE", children=[expression]))
        
        self._consume("SEMICOLON")
        
        return assignment_node


    # Taisyklė: <printf_call> ::= PRINTF_KW LPAREN STRING_LITERAL COMMA IDENTIFICATOR RPAREN SEMICOLON
    def parse_printf_call(self):
        self._consume("PRINTF_KW")
        self._consume("LPAREN")
        
        format_string = self._consume("STRING_LITERAL")
        self._consume("COMMA")
        
        argument = self._consume("IDENTIFICATOR") 
        
        self._consume("RPAREN")
        self._consume("SEMICOLON")
        
        return ASTNode("PRINTF_CALL", 
                       value=format_string[1], 
                       children=[ASTNode("ARGUMENT", value=argument[1])])

    # Taisyklė: <return_stmt> ::= RETURN_KW <expression> SEMICOLON
    def parse_return_stmt(self):
        self._consume("RETURN_KW")
        expression = self.parse_expression()
        self._consume("SEMICOLON")
        
        return ASTNode("RETURN", children=[expression])

    # --- Išraiškos analizė (Precedencija: * > +) ---
    # Taisyklė: <expression> ::= <term> { (PLUS) <term> } 
    def parse_expression(self):
        node = self.parse_term()
        
        while self._peek() == "PLUS":
            operator = self._consume(self._peek())
            right = self.parse_term()
            node = ASTNode("BIN_OP", value=operator[1], children=[node, right])
            
        return node

    # Taisyklė: <term> ::= <factor> { (STAR) <factor> } 
    def parse_term(self):
        node = self.parse_factor()
        
        while self._peek() == "STAR":
            operator = self._consume(self._peek())
            right = self.parse_factor()
            node = ASTNode("BIN_OP", value=operator[1], children=[node, right])
            
        return node

    # Taisyklė: <factor> ::= NUMBER | IDENTIFICATOR | LPAREN <expression> RPAREN
    def parse_factor(self):
        token_kind = self._peek()
        
        if token_kind == "NUMBER":
            num_token = self._consume("NUMBER")
            return ASTNode("LITERAL", value=num_token[1])
        
        elif token_kind == "IDENTIFICATOR":
            id_token = self._consume("IDENTIFICATOR")
            return ASTNode("VAR_REF", value=id_token[1])
        
        elif token_kind == "LPAREN":
            self._consume("LPAREN")
            expression = self.parse_expression()
            self._consume("RPAREN")
            return expression 
        
        else:
            self._error(["NUMBER", "IDENTIFICATOR", "LPAREN"])


# --- III. Lekseris ir Vykdymas ---

if __name__ == "__main__":
    
    # 1. Patikriname, ar pateiktas failo pavadinimas
    if len(sys.argv) < 2:
        print("Naudojimas: python c_parser.py <c_failo_pavadinimas>")
        # Sukuriame pavyzdinį failą, jei nepateiktas argumentas
        example_filename = "sample_code.c"
        print(f"Bandomasis kodas bus sukurtas faile: {example_filename}")
        
        example_code = """
/* Šis kodas bus automatiškai nuskaitomas, jei nepateiksite failo kaip argumento */
int main() {
    const int multiplier = 7;
    int two = multiplier * 2;
    int result = two + 6 + 2;

    printf("Rezultatas: %d", result);
    return 0;
}
"""
        with open(example_filename, 'w', encoding='utf-8') as f:
            f.write(example_code.strip())
            
        code_filepath = example_filename

    else:
        code_filepath = sys.argv[1]

    # 2. Skaitome C kodą iš failo
    try:
        with open(code_filepath, 'r', encoding='utf-8') as f:
            test_code = f.read()
    except FileNotFoundError:
        print(f"Klaida: Failas '{code_filepath}' nerastas.")
        sys.exit(1)


    # Lekserio taisyklės
    tokens = [
        # Keywords
        ("CONST_KW", r"\bconst\b"),
        ("INT_KW", r"\bint\b"),
        ("RETURN_KW", r"\breturn\b"),
        ("MAIN_KW", r"\bmain\b"),
        ("PRINTF_KW", r"\bprintf\b"),
        ("INCLUDE_KW", r"#[ \t]*include"), # Atpažinti #include

        # Operators and symbols
        ("PLUS", r"\+"),
        ("STAR", r"\*"),
        ("EQUAL", r"="),
        ("SEMICOLON", r";"),
        ("COMMA", r","),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("LT", r"<"),  # Mažiau nei / include pradžia
        ("GT", r">"),  # Daugiau nei / include pabaiga

        # Literals
        ("NUMBER", r"\b\d+\b"),
        ("STRING_LITERAL", r'"(\\"|[^"])*"'),
        
        # Identifiers (turi būti tikrinami po raktinių žodžių)
        ("IDENTIFICATOR", r"[A-Za-z_][A-Za-z0-9_]*"),
        
        # Whitespace and control (Svarbu: NEWLINE turi būti atskiras tokenas linijų numeracijai)
        ("NEWLINE", r"\n"),
        ("SKIP", r"[ \t]+"),
        ("COMMENT", r"//.*|/\*[\s\S]*?\*/"), # Pridedamas ir blokinio komentaro palaikymas
        
        # Neatpažinti simboliai
        ("NEATPAŽINTA", r"."),
    ]
    tokens_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in tokens)
    lexer = re.compile(tokens_regex, re.MULTILINE).match 

    
    # Generuojame žetonus (Tokens)
    all_tokens = []
    position = 0
    line_num = 1
    
    print("--- Leksinė analizė (Žetonai) ---")
    
    next_match = lexer(test_code, position)
    while next_match:
        kind = next_match.lastgroup
        value = next_match.group()
        
        if kind == "NEWLINE":
            line_num += 1
            all_tokens.append((kind, value, line_num)) # Įtraukiame NEWLINE, kad būtų galima praleisti
        elif kind in ("SKIP", "COMMENT"):
            all_tokens.append((kind, value, line_num)) # Įtraukiame ir juos, kad parseris galėtų juos praleisti
        elif kind == "NEATPAŽINTA":
            print(f"Leksinė klaida eilutėje {line_num}: Neatpažintas simbolis ('{value}')")
            sys.exit(1)
        else:
            all_tokens.append((kind, value, line_num))
            print(f"({kind}, '{value}', eil. {line_num})")
            
        position = next_match.end()
        next_match = lexer(test_code, position)

    if position < len(test_code) and next_match is None:
        print(f"Leksinė klaida: Neatpažintas simbolis pozicijoje {position}")
        sys.exit(1)

    print("\n--- Sintaksinė analizė (AST) ---")
    parser = Parser(all_tokens)
    ast = parser.parse()
    
    if ast:
        print("\n--- ABSTRAKTUSIS SINTAKSĖS MEDIS (AST) ---")
        ast.pretty_print()
    else:
        print("\nAnalizavimas nepavyko.")

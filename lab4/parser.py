# lab4/parser.py Balys Žalneravičius. Kodo generavimui naudota Gemini Flash 2.5
import sys

class ASTNode:
    def __init__(self, kind, children=None, value=None):
        self.kind = kind
        self.children = children if children is not None else []
        self.value = value
    
    def __repr__(self):
        if self.value is not None:
            return f"<{self.kind} val='{self.value}'>"
        return f"<{self.kind} ({len(self.children)} children)>"

    # gražiai atspausdina medį
    def pretty_print(self, indent=0):
        print('    ' * indent + f"[{self.kind}]" + (f": {self.value}" if self.value is not None else ""))
        for child in self.children:
            if isinstance(child, ASTNode):
                child.pretty_print(indent + 1)
            else:
                print('    ' * (indent + 1) + str(child))

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.errors = []
        
        # Pirmą kartą praleidžiame visus nereikalingus tokenus (tarpus, komentarus, naujas eilutes)
        self._skip_insignificant_tokens() 

    def _error(self, expected_kinds):
        if self.current_token_index < len(self.tokens):
            kind, value, line = self.tokens[self.current_token_index]
            error_msg = f"Sintaksės klaida eilutėje {line}: Lauktas {', '.join(expected_kinds)}, gautas {kind} ('{value}')."
        else:
            error_msg = f"Sintaksės klaida: Lauktas {', '.join(expected_kinds)}, bet pasiekta kodo pabaiga."
        
        self.errors.append(error_msg)
        raise SyntaxError(error_msg)

    def _peek(self):
        if self.current_token_index < len(self.tokens):
            return self.tokens[self.current_token_index][0]
        return "EOF"
    
    def _skip_insignificant_tokens(self):
        while self.current_token_index < len(self.tokens):
            kind = self.tokens[self.current_token_index][0]
            if kind in ("NEWLINE", "SKIP", "COMMENT"):
                self.current_token_index += 1
            else:
                break


    def _consume(self, expected_kind):
        if self._peek() == expected_kind:
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            self._skip_insignificant_tokens()
            return token
        
        self._error([expected_kind])

    def parse(self):
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

    # BNF TAISYKLĖS
    def parse_program(self):
        elements = []
        
        while self._peek() == "INCLUDE_KW":
            elements.append(self.parse_include_stmt())
            
        if self._peek() == "INT_KW":
            elements.append(self.parse_main_function())
        else:
            self._error(["INT_KW (main funkcijos apibrėžimas)"])

        return ASTNode("PROGRAM", children=elements)

    def parse_include_stmt(self):
        self._consume("INCLUDE_KW")
        self._consume("LT") # <
        
        header_name = self._consume("IDENTIFICATOR") # pvz., stdio.h
        
        self._consume("GT") # >

        return ASTNode("INCLUDE", value=header_name[1])

    def parse_main_function(self):
        self._consume("INT_KW")
        self._consume("MAIN_KW")
        self._consume("LPAREN")
        self._consume("RPAREN")
        self._consume("LBRACE")

        statements = self.parse_statement_list()

        self._consume("RBRACE")

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
            if token_kind == "RBRACE":
                 self._error(["CONST_KW", "INT_KW", "RETURN_KW", "PRINTF_KW"])
            else:
                self._error(["CONST_KW", "INT_KW", "RETURN_KW", "PRINTF_KW", "arba RBRACE"])

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
        
        self._consume("EQUAL")
        expression = self.parse_expression()
        assignment_node.children.append(ASTNode("ASSIGN_VALUE", children=[expression]))
        
        self._consume("SEMICOLON")
        
        return assignment_node


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
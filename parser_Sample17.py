# III. Sintaksinio analizatoriaus projektavimas ir realizavimas rekursyvaus nusileidimo metodu:
# 1. konstruoti analizės lenteles ir FIRST, FOLLOW aibes
# 2. rašyti rekursyvaus nusileidimo kodą
# 3. pasiieškoti gero instrumento AST formavimui, arba tokį parašyti
import re

# AST mazgo bazinė klasė
class ASTNode:
    def __init__(self, kind, children=None, value=None):
        self.kind = kind
        self.children = children if children is not None else []
        self.value = value
    
    def __repr__(self):
        # Šiek tiek sutrumpinta atvaizdavimo funkcija, kad būtų patogiau debug'inti
        if self.value is not None:
            return f"<{self.kind} val='{self.value}'>"
        return f"<{self.kind} ({len(self.children)} children)>"

    # Funkcija, skirta gražiai atspausdinti medį (pagelbėja debug'inimui)
    def pretty_print(self, indent=0):
        print('  ' * indent + f"[{self.kind}]" + (f": {self.value}" if self.value is not None else ""))
        for child in self.children:
            if isinstance(child, ASTNode):
                child.pretty_print(indent + 1)
            else:
                print('  ' * (indent + 1) + str(child))

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.errors = []

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
        return "EOF" # End Of File

    def _consume(self, expected_kind):
        if self._peek() == expected_kind:
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        self._error([expected_kind])

    def parse(self):
        try:
            ast = self.parse_program()
            if self._peek() != "EOF":
                self._error(["EOF"]) # Kodo pabaiga turi būti pasiekta
            return ast
        except SyntaxError:
            print("Analizavimas baigtas su klaidomis.")
            return None

    ## BNF TAISYKLIŲ METODAI:

    # <program> ::= { <code_element> }
    def parse_program(self):
        elements = []
        while self._peek() != "EOF":
            # Perduodam žymeklio indeksą, jei parseris randa neteisingą
            # simbolį, kad galėtų praleisti jį ir tęsti darbą (angl. error recovery)
            start_index = self.current_token_index
            try:
                element = self.parse_code_element()
                if element:
                    elements.append(element)
            except SyntaxError:
                # Paprasta klaidų atkūrimo strategija: praleisti dabartinę eilutę/tokeną ir tęsti
                self.current_token_index = start_index + 1
                while self._peek() not in ("NEWLINE", "EOF"):
                    self.current_token_index += 1
        
        return ASTNode("PROGRAM", children=elements)

    # <code_element> ::= <comment> | <keyword_definition> | ...
    def parse_code_element(self):
        token_kind = self._peek()
        
        # Tikriname FIRST aibes, kad pasirinktume taisyklę
        
        # 1. <comment> ::= ";" { <character> } <EOL>
        # PASTABA: Jūsų skeneris apdoroja komentarus, todėl čia tik praleidžiam "COMMENT" ir "NEWLINE"
        if token_kind == "COMMENT":
            token = self._consume("COMMENT")
            # Po komentaro gali sekti NEWLINE, bet BNF to nereikalauja (COMMENT jau turi būti iki EOL)
            # Reikėtų patikrinti, kaip Jūsų skeneris traktuoja EOL po komentaro.
            # Darant prielaidą, kad skeneris palieka NEWLINE:
            if self._peek() == "NEWLINE":
                self._consume("NEWLINE")
            return ASTNode("COMMENT", value=token[1])
        
        # 2. <structure_definition> ::= <identifier> "struc" ...
        # FIRST(<structure_definition>) yra IDENTIFICATOR.
        # Kadangi IDENTIFICATOR taip pat yra FIRST(<assignment>), reikia žiūrėti toliau.
        elif token_kind == "IDENTIFICATOR":
            # Žiūrime antrą tokeną, kad atskirtume nuo <assignment>
            # (Čia reikalinga LL(2) gramatika, bet galime imituoti)
            if self.current_token_index + 1 < len(self.tokens) and \
               self.tokens[self.current_token_index + 1][1].lower() == "struc":
                return self.parse_structure_definition()
            
            # 3. <assignment> ::= <identifier> "=" <value>
            elif self.current_token_index + 1 < len(self.tokens) and \
                 self.tokens[self.current_token_index + 1][0] == "OPERATOR" and \
                 self.tokens[self.current_token_index + 1][1] == "=":
                return self.parse_assignment()
            
            # Jei neradome nei "struc", nei "=", bandome <keyword_definition>
            # <keyword_definition> ::= <keyword> | <keyword> <data_type> <constant>
            # Nors BNF apibrėžia <keyword> kaip atskirus žodžius, Jūsų skeneris tai
            # atpažįsta kaip "IDENTIFICATOR" (klaida skeneryje arba BNF neatitikimas).
            # Turiu prisitaikyti prie Jūsų skenerio:
            else:
                return self.parse_keyword_definition()
                
        # 4. <keyword_definition> (Jei skeneris atpažįsta teisingai, pvz., "FALSE" yra KEYWORD)
        elif token_kind == "KEYWORD":
            # Ieškome raktinių žodžių, kurie nėra struc, ends, ifndef, endif (jie turi savo taisykles)
            value = self.tokens[self.current_token_index][1].upper()
            if value in ("FALSE", "TRUE", "NULL", "RECT", "WNDCLASS"):
                 return self.parse_keyword_definition()
        
        # 5. <conditional_block> ::= "IFNDEF" <identifier> <code_element> "ENDIF"
        elif token_kind == "KEYWORD":
            if self.tokens[self.current_token_index][1].upper() == "IFNDEF":
                return self.parse_conditional_block()
        
        # 6. <empty_line> (praleista Jūsų BNF, bet būtina realiam apdorojimui)
        elif token_kind == "NEWLINE":
            self._consume("NEWLINE")
            return ASTNode("EMPTY_LINE")

        self._error(["COMMENT", "IDENTIFICATOR", "KEYWORD", "NEWLINE"])
        return None # Grąžinama, jei klaidų atkūrimas nepavyko

    # <keyword_definition> ::= <keyword> | <keyword> <data_type> <constant>
    def parse_keyword_definition(self):
        # NOTE: Darant prielaidą, kad skeneris pažymės visus raktinius žodžius kaip "KEYWORD"
        
        keyword_token = self._consume("IDENTIFICATOR") # Pritaikyta Jūsų skeneriui (turėtų būti KEYWORD)
        keyword_node = ASTNode("KEYWORD_NAME", value=keyword_token[1])
        
        node = ASTNode("KEYWORD_DEF", children=[keyword_node])
        
        # Tikriname, ar seka <data_type> (dw, dd, db)
        if self._peek() == "KEYWORD": # Jūsų skeneryje dw/dd/db yra KEYWORD
            if self.tokens[self.current_token_index][1].lower() in ("dw", "dd", "db"):
                data_type_node = self.parse_data_type()
                node.children.append(data_type_node)
                
                # Būtina <constant> ::= <number> | "?"
                constant_node = self.parse_constant()
                node.children.append(constant_node)

        return node

    # <constant> ::= <number> | "?"
    def parse_constant(self):
        token_kind = self._peek()
        if token_kind == "NUMBER":
            num_token = self._consume("NUMBER")
            return ASTNode("CONSTANT_NUMBER", value=num_token[1])
        elif token_kind == "OPERATOR" and self.tokens[self.current_token_index][1] == "?":
            q_token = self._consume("OPERATOR")
            return ASTNode("CONSTANT_UNKNOWN", value=q_token[1])
        else:
            self._error(["NUMBER", "?"])

    # <data_type> ::= "dw" | "dd" | "db"
    def parse_data_type(self):
        # Jūsų skeneryje dw/dd/db yra KEYWORD
        type_token = self._consume("KEYWORD") 
        return ASTNode("DATA_TYPE", value=type_token[1])

    # <structure_definition> ::= <identifier> "struc" <structure_members> <identifier> "ends"
    def parse_structure_definition(self):
        struct_name_start = self._consume("IDENTIFICATOR")
        self._consume("KEYWORD") # "struc"

        members = self.parse_structure_members()
        
        struct_name_end = self._consume("IDENTIFICATOR")
        self._consume("KEYWORD") # "ends"
        
        if struct_name_start[1] != struct_name_end[1]:
            # Pridėta papildoma semantinė patikra (nors tai sintaksinis analizatorius)
            self._error([f"Struktūros pavadinimai nesutampa: {struct_name_start[1]} != {struct_name_end[1]}"])

        return ASTNode("STRUCT_DEF", 
                       value=struct_name_start[1], 
                       children=members)

    # <structure_members> ::= { <structure_member> }
    def parse_structure_members(self):
        members = []
        # Tęsti tol, kol nepasiekiam "ends" (FOLLOW(<structure_members>) = "ends" | IDENTIFICATOR)
        while self._peek() != "KEYWORD" or self.tokens[self.current_token_index][1].lower() != "ends":
            members.append(self.parse_structure_member())
            # Po kiekvieno nario turi sekti nauja eilutė, bet BNF to nereikalauja, todėl praleidžiame NEWLINE
            if self._peek() == "NEWLINE":
                self._consume("NEWLINE")
            
        return members

    # <structure_member> ::= <identifier> <data_type> [ <constant> ]
    def parse_structure_member(self):
        member_name = self._consume("IDENTIFICATOR")
        data_type = self.parse_data_type()
        
        member_node = ASTNode("STRUCT_MEMBER", children=[data_type], value=member_name[1])
        
        # [ <constant> ] - neprivaloma dalis (remiamės FOLLOW aibe, kuri yra IDENTIFICATOR arba ends)
        if self._peek() in ("NUMBER", "OPERATOR") and self.tokens[self.current_token_index][1] == "?":
            constant_node = self.parse_constant()
            member_node.children.append(constant_node)
            
        return member_node

    # <conditional_block> ::= "IFNDEF" <identifier> <code_element> "ENDIF"
    def parse_conditional_block(self):
        # PASTABA: BNF apibrėžia 2 alternatyvas, kurios skiriasi tik raidžių dydžiu ("IFNDEF" ir "ifndef")
        # Jūsų skeneris ignoruoja didžiąsias/mažąsias raides (r"\b(struc...|IFNDEF...)\b"), todėl užtenka 1 taisyklės.
        self._consume("KEYWORD") # IFNDEF
        identifier = self._consume("IDENTIFICATOR")
        
        # Rekursyviai kviečiame <code_element> vidinį kodą
        # Čia reikėtų sukurti taisyklę, leidžiančią daug <code_element>
        
        # Čia darome prielaidą, kad IFNDEF viduje gali būti daug <code_element>
        block_elements = []
        while self._peek() != "KEYWORD" or self.tokens[self.current_token_index][1].upper() != "ENDIF":
            element = self.parse_code_element()
            if element:
                block_elements.append(element)
            
            # Klaidų atveju, kad neužsiciklintume:
            if self.current_token_index >= len(self.tokens):
                self._error(["ENDIF"])

        self._consume("KEYWORD") # ENDIF

        return ASTNode("CONDITIONAL_BLOCK", 
                       value=identifier[1], 
                       children=block_elements)
    
    # <assignment> ::= <identifier> "=" <value>
    def parse_assignment(self):
        identifier = self._consume("IDENTIFICATOR")
        self._consume("OPERATOR") # "="
        value = self.parse_value()
        
        return ASTNode("ASSIGNMENT", 
                       value=identifier[1], 
                       children=[value])
        
    # <value> ::= <number> | <identifier> | <data_type>
    def parse_value(self):
        token_kind = self._peek()
        
        if token_kind == "NUMBER":
            num_token = self._consume("NUMBER")
            return ASTNode("VALUE_NUMBER", value=num_token[1])
        
        elif token_kind == "IDENTIFICATOR":
            id_token = self._consume("IDENTIFICATOR")
            return ASTNode("VALUE_IDENTIFIER", value=id_token[1])
        
        elif token_kind == "KEYWORD" and self.tokens[self.current_token_index][1].lower() in ("dw", "dd", "db"):
            # <data_type> Jūsų skeneryje yra KEYWORD
            return self.parse_data_type()
            
        self._error(["NUMBER", "IDENTIFICATOR", "DATA_TYPE"])


if __name__ == "__main__":
    # Testavimo kodas (Pavyzdys, patikrinimui)
    test_code = """
; Čia yra komentaras
    WNDCLASS dw 10 ?
    RECT struc RECT_NAME
        top dw 0
        left dw 0
    RECT_NAME ends
    
    MyVar = 5
    IFNDEF DEBUG_MODE
        AnotherVar = RECT
    ENDIF
    """
    
    # Pradinė tokenų analizė su Jūsų skeneriu
    # REIKALINGA: Prieš paleidžiant patikrinkite, kad Jūsų skeneryje būtų viskas teisingai
    # (pvz., KEYWORD - RECT, WNDCLASS, FALSE, TRUE, NULL, struc, endif, ifndef, ends, dw, dd, db)
    # Pataisyti skenerį, kad atpažintų visus raktinius žodžius!
    
    # Toliau pateiktas skeneris, kuris labiau atitinka BNF:
    tokens = [
        ("COMMENT", r";[^\n]*"),
        ("NUMBER", r"\b\d+\b"),
        ("KEYWORD", r"\b(FALSE|TRUE|NULL|RECT|WNDCLASS|struc|endif|ifndef|ends|IFNDEF|ENDIF|dw|dd|db|equ|dup)\b"),
        ("IDENTIFICATOR", r"[A-Za-z_][A-Za-z0-9_]*"),
        ("OPERATOR", r"=|\?|;"),
        ("SKLIAUSTAI", r"[()\[\],]"), 
        ("NEWLINE", r"\n"),
        ("SKIP", r"[ \t]+"),
        ("NEATPAŽINTA", r"."),
    ]
    tokens_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in tokens)
    lexer = re.compile(tokens_regex, re.IGNORECASE).match # re.IGNORECASE, kad veiktų didžiosios/mažosios raidės

    
    # Generuojame tokenus
    all_tokens = []
    position = 0
    line_num = 1
    next_match = lexer(test_code)
    while next_match:
        kind = next_match.lastgroup
        value = next_match.group()
        if kind == "NEWLINE":
            line_num += 1
        elif kind == "SKIP":
            pass
        elif kind != "COMMENT": # Komentarai išmetami
            all_tokens.append((kind, value, line_num))
        position = next_match.end()
        next_match = lexer(test_code, position)
    
    if position < len(test_code):
        print(f"Leksinė klaida: Neatpažintas simbolis pozicijoje {position}")
        sys.exit(1)

    print("--- SINTAKSINĖ ANALIZĖ ---")
    parser = Parser(all_tokens)
    ast = parser.parse()
    
    if ast:
        print("\n--- ABSTRAKTUSIS SINTAKSĖS MEDIS (AST) ---")
        ast.pretty_print()
    else:
        print("\nAnalizavimas nepavyko.")
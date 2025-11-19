# lab4/compiler.py Balys Žalneravičius. Kodo generavimui naudota Gemini Flash 2.5
import re
import sys
import os

from parser import ASTNode, Parser
from semantic_analyzer import SemanticAnalyzer

if __name__ == "__main__":
    # Patikrina ar pateiktas failas
    if len(sys.argv) < 2:
        print("Naudojimas: python compiler.py <c_failo_pavadinimas>")
        sys.exit(1)
    else:
        code_filepath = sys.argv[1]

    # Nuskaitom kodą
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
        ("INCLUDE_KW", r"#[ \t]*include"),

        ("PLUS", r"\+"),
        ("STAR", r"\*"),
        ("EQUAL", r"="),
        ("SEMICOLON", r";"),
        ("COMMA", r","),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("LT", r"<"),
        ("GT", r">"),

        ("NUMBER", r"\b\d+\b"),
        ("STRING_LITERAL", r'"(\\"|[^"])*"'),
        
        ("IDENTIFICATOR", r"[A-Za-z_][A-Za-z0-9_]*"),
        
        ("NEWLINE", r"\n"),
        ("SKIP", r"[ \t]+"),
        ("COMMENT", r"//.*|/\*[\s\S]*?\*/"),
        
        ("NEATPAŽINTA", r"."),
    ]
    tokens_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in tokens)
    lexer = re.compile(tokens_regex, re.MULTILINE).match 

    # lab2: Leksemų suskirstymas
    all_tokens = []
    position = 0
    line_num = 1
    
    print("##### Leksinė analizė #####")
    
    next_match = lexer(test_code, position)
    while next_match:
        kind = next_match.lastgroup
        value = next_match.group()
        
        if kind == "NEWLINE":
            line_num += 1
            all_tokens.append((kind, value, line_num))
        elif kind in ("SKIP", "COMMENT"):
            all_tokens.append((kind, value, line_num))
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

    # lab3: Parseris
    print("\n##### Parseris - sintaksinė analizė (AST) ####")
    parser_instance = Parser(all_tokens)
    ast = parser_instance.parse()
    
    if ast:
        ast.pretty_print()
        
        # lab4: semantinė analizė
        print("\n--- SEMANTINĖ ANALIZĖ ---")
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
    else:
        print("\nAnalizavimas nepavyko.")
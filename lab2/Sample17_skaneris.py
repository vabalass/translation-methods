import re
import sys
from collections import Counter

tokens = [
    ("COMMENT",   r";[^\n]*"),
    ("NUMBER",    r"\b\d+\b"),
    ("HEX_NUMBER", r"\b[0-9A-F]+[Hh]\b"),
    ("KEYWORD",   r"\b(struc|ends|equ|dw|dd|db|dup|IFNDEF|ENDIF)\b"),
    ("IDENTIFICATOR",     r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OPERATOR",  r"=|\?|\+|\-"),
    ("SKLIAUSTAI",     r"[()\[\],]"), 
    ("NEWLINE",   r"\n"),
    ("SKIP",      r"[ \t]+"),
    ("NEATPAŽINTA",  r"."),
]

tokens_regex = "|".join(f"(?P<{name}>{pattern})" for name, pattern in tokens)
lexer = re.compile(tokens_regex).match

def scanner(code):
    tokens = []
    line_num = 1
    position = 0
    next = lexer(code)
    while next:
        kind = next.lastgroup
        value = next.group()
        if kind == "NEWLINE":
            line_num += 1
        elif kind == "SKIP":
            pass
        else:
            tokens.append((kind, value, line_num))
        position = next.end()
        next = lexer(code, position)
    return tokens

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Naudojimas: python scanner.py failas.trm")
        sys.exit(1)
    
    file_name = sys.argv[1]
    
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Klaida: failas '{file_name}' nerastas.")
        sys.exit(1)
    
    tokens = scanner(code)
    counts = Counter(kind for kind, _, _ in tokens)
    
    print("Skanerio rezultatai:")
    for token_type, count in counts.items():
        print(f"{token_type:15s}: {count}")

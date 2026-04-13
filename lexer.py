r"""
Analizador Léxico — v3
Arquitectura: regex por patrones (como tu versión funcional) +
fusión multi-línea para operadores relacionales/lógicos de dos caracteres.

Patrones (orden importa):
    ESPACIO       →  [ \t]+
    NUEVA_LINEA   →  \n
    COMENTARIO    →  // ... \n   |   /* ... */   |   # ...
    CADENA_DOBLE  →  "..."
    CADENA_SIMPLE →  '...'
    NUMERO_REAL   →  \d+\.\d+          (válido)
    ERROR_REAL    →  \d+\.             (número con punto sin dígitos → error)
    NUMERO_ENTERO →  d+
    IDENTIFICADOR →  [a-zA-Z_][a-zA-Z0-9_]*
    OP_MULTI      →  ++, --, &&, ||    (operadores dobles, sin espacio)
    OP_SIMPLE     →  + - * / % ^ < > ! = & |  (candidatos a fusión)
    SIMBOLO       →  ( ) { } [ ] , ; :
    ERROR         →  .                  (cualquier otro carácter)

Fusión multi-línea:
    Los pares  ++  --  ==  !=  <=  >=  &&  ||
    se reconocen aunque haya ESPACIOS o NUEVA_LINEA entre ellos.
    Sólo aplica a los caracteres que pueden formar esos pares:
        '+'→'+',  '-'→'-',  '='→'=',  '!'→'=',  '<'→'=',  '>'→'=',
        '&'→'&',  '|'→'|'
"""

import re
from dataclasses import dataclass

# ─────────────────────────────────────────────
#  TIPOS DE TOKEN  (mismo enum que main.py usa)
# ─────────────────────────────────────────────
from enum import Enum

class TipoToken(Enum):
    NUMERO_ENTERO   = "Número Entero"
    NUMERO_REAL     = "Número Real"
    ERROR_REAL      = "Error Real"          # ← NUEVO: 32. sin dígitos
    IDENTIFICADOR   = "Identificador"
    RESERVADA       = "Palabra Reservada"
    OP_SUMA         = "Op. Aritmético +"
    OP_RESTA        = "Op. Aritmético -"
    OP_MULT         = "Op. Aritmético *"
    OP_DIV          = "Op. Aritmético /"
    OP_MOD          = "Op. Aritmético %"
    OP_POT          = "Op. Aritmético ^"
    OP_INCR         = "Op. Aritmético ++"
    OP_DECR         = "Op. Aritmético --"
    OP_MENOR        = "Op. Relacional <"
    OP_MAYOR        = "Op. Relacional >"
    OP_MENOR_IGUAL  = "Op. Relacional <="
    OP_MAYOR_IGUAL  = "Op. Relacional >="
    OP_DIFERENTE    = "Op. Relacional !="
    OP_IGUAL_IGUAL  = "Op. Relacional =="
    OP_AND          = "Op. Lógico &&"
    OP_OR           = "Op. Lógico ||"
    OP_NOT          = "Op. Lógico !"
    ASIGNACION      = "Asignación ="
    PARENTESIS_A    = "Símbolo ("
    PARENTESIS_C    = "Símbolo )"
    LLAVE_A         = "Símbolo {"
    LLAVE_C         = "Símbolo }"
    CORCHETE_A      = "Símbolo ["
    CORCHETE_C      = "Símbolo ]"
    COMA            = "Símbolo ,"
    PUNTO_COMA      = "Símbolo ;"
    DOS_PUNTOS      = "Símbolo :"
    CADENA_DOBLE    = 'Cadena ""'
    CADENA_SIMPLE   = "Cadena ''"
    COMENTARIO      = "Comentario"
    ERROR           = "Error Léxico"


PALABRAS_RESERVADAS = {
    "if", "else", "end", "do", "while", "switch",
    "case", "int", "float", "main", "cin", "cout",
    "until", "then", "real",
}

COLORES_TOKEN = {
    TipoToken.NUMERO_ENTERO:   "#4FC3F7",
    TipoToken.NUMERO_REAL:     "#4FC3F7",
    TipoToken.ERROR_REAL:      "#EF5350",   # mismo rojo que ERROR
    TipoToken.IDENTIFICADOR:   "#FFFFFF",
    TipoToken.RESERVADA:       "#CE93D8",
    TipoToken.OP_SUMA:         "#FFCC02",
    TipoToken.OP_RESTA:        "#FFCC02",
    TipoToken.OP_MULT:         "#FFCC02",
    TipoToken.OP_DIV:          "#FFCC02",
    TipoToken.OP_MOD:          "#FFCC02",
    TipoToken.OP_POT:          "#FFCC02",
    TipoToken.OP_INCR:         "#FFCC02",
    TipoToken.OP_DECR:         "#FFCC02",
    TipoToken.OP_MENOR:        "#80DEEA",
    TipoToken.OP_MAYOR:        "#80DEEA",
    TipoToken.OP_MENOR_IGUAL:  "#80DEEA",
    TipoToken.OP_MAYOR_IGUAL:  "#80DEEA",
    TipoToken.OP_DIFERENTE:    "#80DEEA",
    TipoToken.OP_IGUAL_IGUAL:  "#80DEEA",
    TipoToken.OP_AND:          "#F48FB1",
    TipoToken.OP_OR:           "#F48FB1",
    TipoToken.OP_NOT:          "#F48FB1",
    TipoToken.ASIGNACION:      "#80DEEA",
    TipoToken.PARENTESIS_A:    "#E0E0E0",
    TipoToken.PARENTESIS_C:    "#E0E0E0",
    TipoToken.LLAVE_A:         "#E0E0E0",
    TipoToken.LLAVE_C:         "#E0E0E0",
    TipoToken.CORCHETE_A:      "#E0E0E0",
    TipoToken.CORCHETE_C:      "#E0E0E0",
    TipoToken.COMA:            "#E0E0E0",
    TipoToken.PUNTO_COMA:      "#E0E0E0",
    TipoToken.DOS_PUNTOS:      "#E0E0E0",
    TipoToken.CADENA_DOBLE:    "#A5D6A7",
    TipoToken.CADENA_SIMPLE:   "#A5D6A7",
    TipoToken.COMENTARIO:      "#757575",
    TipoToken.ERROR:           "#EF5350",
}


@dataclass
class Token:
    tipo: TipoToken
    valor: str
    linea: int
    columna: int

    def __str__(self):
        return (f"[{self.tipo.value}]  '{self.valor}'"
                f"  (Lín:{self.linea}, Col:{self.columna})")


@dataclass
class ErrorLexico:
    caracter: str
    linea: int
    columna: int
    descripcion: str = ""

    def __str__(self):
        desc = self.descripcion or f"Carácter no reconocido '{self.caracter}'"
        return f"Error Léxico: {desc}  (Lín:{self.linea}, Col:{self.columna})"


# ─────────────────────────────────────────────────────────────────
#  Tabla de símbolos simples  →  TipoToken
# ─────────────────────────────────────────────────────────────────
_SIMBOLO_TIPO = {
    '(': TipoToken.PARENTESIS_A, ')': TipoToken.PARENTESIS_C,
    '{': TipoToken.LLAVE_A,      '}': TipoToken.LLAVE_C,
    '[': TipoToken.CORCHETE_A,   ']': TipoToken.CORCHETE_C,
    ',': TipoToken.COMA,         ';': TipoToken.PUNTO_COMA,
    ':': TipoToken.DOS_PUNTOS,
}

_PARES_CIERRE   = {')': '(', '}': '{', ']': '['}
_PARES_APERTURA = {'(', '{', '['}

# Operador simple → tipo cuando aparece SOLO (sin par)
_OP_SIMPLE_TIPO = {
    '+': TipoToken.OP_SUMA,   '-': TipoToken.OP_RESTA,
    '*': TipoToken.OP_MULT,   '/': TipoToken.OP_DIV,
    '%': TipoToken.OP_MOD,    '^': TipoToken.OP_POT,
    '<': TipoToken.OP_MENOR,  '>': TipoToken.OP_MAYOR,
    '!': TipoToken.OP_NOT,    '=': TipoToken.ASIGNACION,
    '&': None,   # '&' solo → error
    '|': None,   # '|' solo → error
}

# Par fusionado → TipoToken
_FUSION_TIPO = {
    '++': TipoToken.OP_INCR,
    '--': TipoToken.OP_DECR,
    '==': TipoToken.OP_IGUAL_IGUAL,
    '!=': TipoToken.OP_DIFERENTE,
    '<=': TipoToken.OP_MENOR_IGUAL,
    '>=': TipoToken.OP_MAYOR_IGUAL,
    '&&': TipoToken.OP_AND,
    '||': TipoToken.OP_OR,
}

# Caracteres que buscan un segundo carácter para formar par
_PAREJAS_FUSION = {
    '+': '+', '-': '-',
    '=': '=', '!': '=',
    '<': '=', '>': '=',
    '&': '&', '|': '|',
}


# ─────────────────────────────────────────────────────────────────
#  PATRONES  (orden crítico)
# ─────────────────────────────────────────────────────────────────
_PATRONES = [
    ('ESPACIO',       r'[ \t]+'),
    ('NUEVA_LINEA',   r'\n'),
    # Comentarios — capturados ANTES que la '/' suelta
    ('COMENTARIO',    r'//[^\n]*|/\*.*?\*/|#[^\n]*'),
    # Cadenas
    ('CADENA_DOBLE',  r'"(?:[^"\n])*"'),
    ('CADENA_DOBLE_NC', r'"[^"\n]*'),        # sin cerrar
    ('CADENA_SIMPLE', r"'(?:[^'\n])*'"),
    ('CADENA_SIMPLE_NC', r"'[^'\n]*"),       # sin cerrar
    # Números  (REAL antes que ENTERO)
    ('NUMERO_REAL',   r'\d+\.\d+'),
    ('ERROR_REAL',    r'\d+\.'),             # 32.  sin dígitos = error
    ('NUMERO_ENTERO', r'\d+'),
    # Identificadores / palabras reservadas
    ('IDENTIFICADOR', r'[a-zA-Z_][a-zA-Z0-9_]*'),
    # Operadores dobles sin espacio (atajos directos antes de los simples)
    ('OP_MULTI',      r'\+\+|--|&&|\|\|'),
    # Operadores simples (candidatos a fusión multi-línea)
    ('OP_SIMPLE',     r'[+\-=!<>&|]'),
    # Otros operadores que NO participan en fusión
    ('OP_OTROS',      r'[*/% ^]'),
    # Símbolos
    ('SIMBOLO',       r'[(){}\[\],:;]'),
    # Cualquier otro → error
    ('ERROR',         r'.'),
]

_REGEX = re.compile(
    '|'.join(f'(?P<{name}>{pat})' for name, pat in _PATRONES),
    re.DOTALL   # para que /* */ multilínea funcione
)


# ─────────────────────────────────────────────────────────────────
#  ANALIZADOR LÉXICO
# ─────────────────────────────────────────────────────────────────

class AnalizadorLexico:

    def analizar(self, codigo: str) -> tuple[list[Token], list[ErrorLexico]]:
        tokens:  list[Token]       = []
        errores: list[ErrorLexico] = []
        pila_delim: list[tuple[str, int, int]] = []

        matches = list(_REGEX.finditer(codigo))
        n = len(matches)

        linea          = 1
        columna_inicio = 0   # posición en 'codigo' donde empieza la línea actual

        i = 0
        while i < n:
            m    = matches[i]
            kind = m.lastgroup
            val  = m.group()
            col  = m.start() - columna_inicio + 1

            # ── ESPACIO  (trimming) ───────────────────────────────────
            if kind == 'ESPACIO':
                i += 1
                continue

            # ── NUEVA LÍNEA ───────────────────────────────────────────
            if kind == 'NUEVA_LINEA':
                linea         += 1
                columna_inicio = m.end()
                i += 1
                continue

            # ── COMENTARIO ────────────────────────────────────────────
            if kind == 'COMENTARIO':
                # Contar saltos de línea dentro del comentario
                nl = val.count('\n')
                tokens.append(Token(TipoToken.COMENTARIO, val, linea, col))
                if nl:
                    linea         += nl
                    columna_inicio = m.start() + val.rfind('\n') + 1
                i += 1
                continue

            # ── CADENAS ───────────────────────────────────────────────
            if kind == 'CADENA_DOBLE':
                tokens.append(Token(TipoToken.CADENA_DOBLE, val, linea, col))
                i += 1; continue

            if kind == 'CADENA_DOBLE_NC':
                errores.append(ErrorLexico(val, linea, col,
                    f"Cadena sin cerrar — falta '\"' (iniciada col {col})"))
                i += 1; continue

            if kind == 'CADENA_SIMPLE':
                tokens.append(Token(TipoToken.CADENA_SIMPLE, val, linea, col))
                i += 1; continue

            if kind == 'CADENA_SIMPLE_NC':
                errores.append(ErrorLexico(val, linea, col,
                    f"Cadena de carácter sin cerrar — falta \"'\" (iniciada col {col})"))
                i += 1; continue

            # ── NÚMEROS ───────────────────────────────────────────────
            if kind == 'NUMERO_REAL':
                tokens.append(Token(TipoToken.NUMERO_REAL, val, linea, col))
                i += 1; continue

            if kind == 'ERROR_REAL':
                # p. ej. "32."  → el número tiene punto pero sin dígitos después
                errores.append(ErrorLexico(val, linea, col,
                    f"Número real mal formado '{val}' — falta dígito tras el punto"))
                i += 1; continue

            if kind == 'NUMERO_ENTERO':
                tokens.append(Token(TipoToken.NUMERO_ENTERO, val, linea, col))
                i += 1; continue

            # ── IDENTIFICADOR / PALABRA RESERVADA ─────────────────────
            if kind == 'IDENTIFICADOR':
                tipo = (TipoToken.RESERVADA
                        if val in PALABRAS_RESERVADAS
                        else TipoToken.IDENTIFICADOR)
                tokens.append(Token(tipo, val, linea, col))
                i += 1; continue

            # ── OPERADORES DOBLES SIN ESPACIO (++, --, &&, ||) ────────
            if kind == 'OP_MULTI':
                tokens.append(Token(_FUSION_TIPO[val], val, linea, col))
                i += 1; continue

            # ── OPERADORES SIMPLES — LÓGICA DE FUSIÓN MULTI-LÍNEA ─────
            # (tu algoritmo original, adaptado)
            if kind == 'OP_SIMPLE':
                if val in _PAREJAS_FUSION:
                    # Buscar el segundo carácter saltando ESPACIO y NUEVA_LINEA
                    segundo_esperado = _PAREJAS_FUSION[val]
                    j = i + 1
                    lineas_saltadas   = 0
                    temp_col_inicio   = columna_inicio
                    encontro_par      = False

                    while j < n:
                        nxt = matches[j]
                        nxt_kind = nxt.lastgroup
                        if nxt_kind == 'ESPACIO':
                            j += 1; continue
                        if nxt_kind == 'NUEVA_LINEA':
                            lineas_saltadas += 1
                            temp_col_inicio  = nxt.end()
                            j += 1; continue
                        # Primer token que no es blanco
                        if nxt.group() == segundo_esperado:
                            encontro_par = True
                        break

                    if encontro_par:
                        fusionado = val + segundo_esperado
                        tokens.append(Token(_FUSION_TIPO[fusionado],
                                            fusionado, linea, col))
                        linea          += lineas_saltadas
                        columna_inicio  = temp_col_inicio
                        i = j + 1
                        continue
                    # No encontró par → emitir como operador simple o error
                    tipo_solo = _OP_SIMPLE_TIPO.get(val)
                    if tipo_solo is not None:
                        tokens.append(Token(tipo_solo, val, linea, col))
                    else:
                        # '&' o '|' solos
                        errores.append(ErrorLexico(val, linea, col,
                            f"'{val}' solo no es válido — "
                            f"¿quiso escribir '{val}{val}'?"))
                    i += 1
                    continue

                # OP_SIMPLE sin entrada en _PAREJAS_FUSION (no debería ocurrir)
                tokens.append(Token(_OP_SIMPLE_TIPO.get(val, TipoToken.ERROR),
                                    val, linea, col))
                i += 1; continue

            # ── OTROS OPERADORES (* / % ^ ) ───────────────────────────
            if kind == 'OP_OTROS':
                mapa = {'*': TipoToken.OP_MULT, '/': TipoToken.OP_DIV,
                        '%': TipoToken.OP_MOD,  '^': TipoToken.OP_POT,
                        ' ': None}
                tipo = mapa.get(val)
                if tipo:
                    tokens.append(Token(tipo, val, linea, col))
                i += 1; continue

            # ── SÍMBOLOS  (con balance de paréntesis/llaves) ──────────
            if kind == 'SIMBOLO':
                tipo = _SIMBOLO_TIPO[val]
                tokens.append(Token(tipo, val, linea, col))

                if val in _PARES_APERTURA:
                    pila_delim.append((val, linea, col))
                elif val in _PARES_CIERRE:
                    esperado = _PARES_CIERRE[val]
                    if pila_delim and pila_delim[-1][0] == esperado:
                        pila_delim.pop()
                    elif pila_delim:
                        ap, alin, acol = pila_delim[-1]
                        errores.append(ErrorLexico(val, linea, col,
                            f"Cierre '{val}' no corresponde a '{ap}' "
                            f"(Lín:{alin}, Col:{acol})"))
                    else:
                        errores.append(ErrorLexico(val, linea, col,
                            f"Símbolo de cierre '{val}' sin apertura correspondiente"))
                i += 1; continue

            # ── ERROR ─────────────────────────────────────────────────
            if kind == 'ERROR':
                errores.append(ErrorLexico(val, linea, col,
                    f"Carácter no reconocido '{val}' (ASCII {ord(val)})"))
                i += 1; continue

            i += 1  # seguridad

        # Aperturas sin cerrar al EOF
        for ap, alin, acol in pila_delim:
            errores.append(ErrorLexico(ap, alin, acol,
                f"Símbolo de apertura '{ap}' sin cierre — llega al EOF"))

        errores.sort(key=lambda e: (e.linea, e.columna))
        return tokens, errores
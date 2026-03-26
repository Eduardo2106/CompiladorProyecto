"""
Analizador Léxico basado en el Autómata de Estado Finito (DFA)
Implementa todos los tokens especificados en la especificación del proyecto.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto


# ================= TIPOS DE TOKENS =================

class TipoToken(Enum):
    # Números
    NUMERO_ENTERO    = "Número Entero"
    NUMERO_REAL      = "Número Real"

    # Identificadores y palabras reservadas
    IDENTIFICADOR    = "Identificador"
    RESERVADA        = "Palabra Reservada"

    # Operadores aritméticos
    OP_SUMA          = "Op. Aritmético +"
    OP_RESTA         = "Op. Aritmético -"
    OP_MULT          = "Op. Aritmético *"
    OP_DIV           = "Op. Aritmético /"
    OP_MOD           = "Op. Aritmético %"
    OP_POT           = "Op. Aritmético ^"
    OP_INCR          = "Op. Aritmético ++"
    OP_DECR          = "Op. Aritmético --"

    # Operadores relacionales
    OP_MENOR         = "Op. Relacional <"
    OP_MAYOR         = "Op. Relacional >"
    OP_MENOR_IGUAL   = "Op. Relacional <="
    OP_MAYOR_IGUAL   = "Op. Relacional >="
    OP_DIFERENTE     = "Op. Relacional !="
    OP_IGUAL_IGUAL   = "Op. Relacional =="

    # Operadores lógicos
    OP_AND           = "Op. Lógico &&"
    OP_OR            = "Op. Lógico ||"
    OP_NOT           = "Op. Lógico !"

    # Asignación
    ASIGNACION       = "Asignación ="

    # Símbolos
    PARENTESIS_A     = "Símbolo ("
    PARENTESIS_C     = "Símbolo )"
    LLAVE_A          = "Símbolo {"
    LLAVE_C          = "Símbolo }"
    CORCHETE_A       = "Símbolo ["
    CORCHETE_C       = "Símbolo ]"
    COMA             = "Símbolo ,"
    PUNTO_COMA       = "Símbolo ;"
    DOS_PUNTOS       = "Símbolo :"

    # Cadenas
    CADENA_DOBLE     = "Cadena \"\""
    CADENA_SIMPLE    = "Cadena ''"

    # Comentarios
    COMENTARIO       = "Comentario"

    # Error
    ERROR            = "Error Léxico"


# Palabras reservadas del lenguaje
PALABRAS_RESERVADAS = {
    "if", "else", "end", "do", "while", "switch",
    "case", "int", "float", "main", "cin", "cout"
}

# Colores para cada tipo de token (para resaltado de sintaxis)
COLORES_TOKEN = {
    TipoToken.NUMERO_ENTERO:   "#4FC3F7",  # Azul claro
    TipoToken.NUMERO_REAL:     "#4FC3F7",  # Azul claro
    TipoToken.IDENTIFICADOR:   "#FFFFFF",  # Blanco
    TipoToken.RESERVADA:       "#CE93D8",  # Morado claro
    TipoToken.OP_SUMA:         "#FFCC02",  # Amarillo
    TipoToken.OP_RESTA:        "#FFCC02",
    TipoToken.OP_MULT:         "#FFCC02",
    TipoToken.OP_DIV:          "#FFCC02",
    TipoToken.OP_MOD:          "#FFCC02",
    TipoToken.OP_POT:          "#FFCC02",
    TipoToken.OP_INCR:         "#FFCC02",
    TipoToken.OP_DECR:         "#FFCC02",
    TipoToken.OP_MENOR:        "#80DEEA",  # Cian
    TipoToken.OP_MAYOR:        "#80DEEA",
    TipoToken.OP_MENOR_IGUAL:  "#80DEEA",
    TipoToken.OP_MAYOR_IGUAL:  "#80DEEA",
    TipoToken.OP_DIFERENTE:    "#80DEEA",
    TipoToken.OP_IGUAL_IGUAL:  "#80DEEA",
    TipoToken.OP_AND:          "#F48FB1",  # Rosa
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
    TipoToken.CADENA_DOBLE:    "#A5D6A7",  # Verde claro
    TipoToken.CADENA_SIMPLE:   "#A5D6A7",
    TipoToken.COMENTARIO:      "#757575",  # Gris
    TipoToken.ERROR:           "#EF5350",  # Rojo
}


@dataclass
class Token:
    tipo: TipoToken
    valor: str
    linea: int
    columna: int

    def __str__(self):
        return f"[{self.tipo.value}] '{self.valor}'  (Lín:{self.linea}, Col:{self.columna})"


@dataclass
class ErrorLexico:
    caracter: str
    linea: int
    columna: int

    def __str__(self):
        return f"Error Léxico: Carácter no reconocido '{self.caracter}'  (Lín:{self.linea}, Col:{self.columna})"


# ================= AUTÓMATA DFA (ANALIZADOR LÉXICO) =================

class AnalizadorLexico:
    """
    Implementación del DFA (Autómata Finito Determinista) descrito en el diagrama.
    Estados del autómata:
        INICIO → estado inicial
        NUMERO_ENTERO → dígitos consecutivos
        NUMERO_REAL_PUNTO → después del punto decimal
        NUMERO_REAL_DIG → dígitos de la parte decimal
        ID → identificador/palabra reservada
        COMENTARIO_LINEA → comentario de una línea (//)  → con /n retorna
        COMENTARIO_BLOQUE_* → comentario de bloque (/* ... */)
        CADENA_DOBLE → cadena entre comillas dobles
        CADENA_SIMPLE → cadena entre comillas simples
        RELACIONAL → operadores relacionales
        OP_AND1 → primer & encontrado
        OP_OR1 → primer | encontrado
        OP_NOT1 → ! encontrado (puede ser != )
        OP_INCR_DECR → + o - encontrado (puede ser ++ ó --)
    """

    def analizar(self, codigo: str) -> tuple[list[Token], list[ErrorLexico]]:
        tokens: list[Token] = []
        errores: list[ErrorLexico] = []

        pos = 0
        linea = 1
        col = 1
        n = len(codigo)

        def avanzar():
            nonlocal pos, linea, col
            c = codigo[pos]
            pos += 1
            if c == '\n':
                linea += 1
                col = 1
            else:
                col += 1
            return c

        def peek(offset=0):
            p = pos + offset
            return codigo[p] if p < n else ''

        while pos < n:
            ini_lin = linea
            ini_col = col
            c = avanzar()

            # ── Espacios en blanco ──────────────────────────────────────
            if c in ' \t\r\n':
                continue

            # ── Comentario de una línea: // ─────────────────────────────
            if c == '/' and peek() == '/':
                avanzar()  # consume segundo /
                valor = '//'
                while pos < n and peek() != '\n':
                    valor += avanzar()
                tokens.append(Token(TipoToken.COMENTARIO, valor, ini_lin, ini_col))
                continue

            # ── Comentario de bloque: /* ... */ ─────────────────────────
            if c == '/' and peek() == '*':
                avanzar()  # consume *
                valor = '/*'
                cerrado = False
                while pos < n:
                    ch = avanzar()
                    valor += ch
                    if ch == '*' and peek() == '/':
                        valor += avanzar()  # consume /
                        cerrado = True
                        break
                if not cerrado:
                    errores.append(ErrorLexico("comentario sin cerrar", ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.COMENTARIO, valor, ini_lin, ini_col))
                continue

            # ── Comentario de una línea con #  ──────────────────────────
            if c == '#':
                valor = '#'
                while pos < n and peek() != '\n':
                    valor += avanzar()
                tokens.append(Token(TipoToken.COMENTARIO, valor, ini_lin, ini_col))
                continue

            # ── Número Entero / Real ────────────────────────────────────
            if c.isdigit():
                valor = c
                while pos < n and peek().isdigit():
                    valor += avanzar()
                # ¿hay punto decimal?
                if peek() == '.' and (pos + 1 < n and codigo[pos + 1].isdigit()):
                    valor += avanzar()  # consume .
                    while pos < n and peek().isdigit():
                        valor += avanzar()
                    tokens.append(Token(TipoToken.NUMERO_REAL, valor, ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.NUMERO_ENTERO, valor, ini_lin, ini_col))
                continue

            # ── Identificador / Palabra Reservada ───────────────────────
            if c.isalpha() or c == '_':
                valor = c
                while pos < n and (peek().isalnum() or peek() == '_'):
                    valor += avanzar()
                tipo = TipoToken.RESERVADA if valor in PALABRAS_RESERVADAS else TipoToken.IDENTIFICADOR
                tokens.append(Token(tipo, valor, ini_lin, ini_col))
                continue

            # ── Cadena con comillas dobles ───────────────────────────────
            if c == '"':
                valor = '"'
                cerrada = False
                while pos < n:
                    ch = avanzar()
                    valor += ch
                    if ch == '"':
                        cerrada = True
                        break
                    if ch == '\n':
                        break
                if not cerrada:
                    errores.append(ErrorLexico("cadena sin cerrar", ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.CADENA_DOBLE, valor, ini_lin, ini_col))
                continue

            # ── Cadena con comilla simple ────────────────────────────────
            if c == "'":
                valor = "'"
                cerrada = False
                while pos < n:
                    ch = avanzar()
                    valor += ch
                    if ch == "'":
                        cerrada = True
                        break
                    if ch == '\n':
                        break
                if not cerrada:
                    errores.append(ErrorLexico("carácter sin cerrar", ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.CADENA_SIMPLE, valor, ini_lin, ini_col))
                continue

            # ── Operadores aritméticos ───────────────────────────────────
            if c == '+':
                if peek() == '+':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_INCR, '++', ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.OP_SUMA, '+', ini_lin, ini_col))
                continue

            if c == '-':
                if peek() == '-':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_DECR, '--', ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.OP_RESTA, '-', ini_lin, ini_col))
                continue

            if c == '*':
                tokens.append(Token(TipoToken.OP_MULT, '*', ini_lin, ini_col))
                continue

            if c == '/':
                tokens.append(Token(TipoToken.OP_DIV, '/', ini_lin, ini_col))
                continue

            if c == '%':
                tokens.append(Token(TipoToken.OP_MOD, '%', ini_lin, ini_col))
                continue

            if c == '^':
                tokens.append(Token(TipoToken.OP_POT, '^', ini_lin, ini_col))
                continue

            # ── Operadores relacionales ──────────────────────────────────
            if c == '<':
                if peek() == '=':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_MENOR_IGUAL, '<=', ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.OP_MENOR, '<', ini_lin, ini_col))
                continue

            if c == '>':
                if peek() == '=':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_MAYOR_IGUAL, '>=', ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.OP_MAYOR, '>', ini_lin, ini_col))
                continue

            if c == '!':
                if peek() == '=':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_DIFERENTE, '!=', ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.OP_NOT, '!', ini_lin, ini_col))
                continue

            if c == '=':
                if peek() == '=':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_IGUAL_IGUAL, '==', ini_lin, ini_col))
                else:
                    tokens.append(Token(TipoToken.ASIGNACION, '=', ini_lin, ini_col))
                continue

            # ── Operadores lógicos ───────────────────────────────────────
            if c == '&':
                if peek() == '&':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_AND, '&&', ini_lin, ini_col))
                else:
                    errores.append(ErrorLexico('&', ini_lin, ini_col))
                continue

            if c == '|':
                if peek() == '|':
                    avanzar()
                    tokens.append(Token(TipoToken.OP_OR, '||', ini_lin, ini_col))
                else:
                    errores.append(ErrorLexico('|', ini_lin, ini_col))
                continue

            # ── Símbolos ─────────────────────────────────────────────────
            simbolos = {
                '(': TipoToken.PARENTESIS_A,
                ')': TipoToken.PARENTESIS_C,
                '{': TipoToken.LLAVE_A,
                '}': TipoToken.LLAVE_C,
                '[': TipoToken.CORCHETE_A,
                ']': TipoToken.CORCHETE_C,
                ',': TipoToken.COMA,
                ';': TipoToken.PUNTO_COMA,
                ':': TipoToken.DOS_PUNTOS,
            }
            if c in simbolos:
                tokens.append(Token(simbolos[c], c, ini_lin, ini_col))
                continue

            # ── Carácter no reconocido ───────────────────────────────────
            errores.append(ErrorLexico(c, ini_lin, ini_col))

        return tokens, errores
"""
Analizador Sintáctico Descendente Recursivo — Fase 2
=====================================================
Gramática implementada:

    programa         → main { lista_declaracion }
    lista_declaracion→ declaracion+
    declaracion      → declaracion_variable | sentencia
    declaracion_variable → tipo identificador_lista ;
    identificador_lista  → id { , id }
    tipo             → int | float | real | bool
    sentencia        → asignacion | seleccion | iteracion
                     | repeticion | sent_in | sent_out
    asignacion       → id = sent_expresion
    sent_expresion   → expresion ; | ;
    seleccion        → if expresion then lista_sentencias
                         [ else lista_sentencias ] end
    iteracion        → while expresion { lista_sentencias } ;
    repeticion       → do lista_sentencias while expresion ;
                     | do lista_sentencias until ( expresion ) ;
    sent_in          → cin id ;
    sent_out         → cout salida ;
    salida           → cadena | expresion | cadena << expresion
                     | expresion << cadena
    expresion        → expresion_simple [ rel_op expresion_simple ]
    rel_op           → < | <= | > | >= | == | !=
    expresion_simple → termino { suma_op termino }
    suma_op          → + | - | ++ | --
    termino          → factor { mult_op factor }
    mult_op          → * | / | %
    factor           → componente { ^ componente }
    componente       → ( expresion ) | número | id | cadena
                     | op_logico componente
    op_logico        → && | || | !
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from lexer import Token, TipoToken


# ═══════════════════════════════════════════════════════════════════
#  NODOS DEL AST
# ═══════════════════════════════════════════════════════════════════

@dataclass
class NodoAST:
    """Nodo base del Árbol Sintáctico Abstracto."""
    tipo:   str
    valor:  str        = ""
    linea:  int        = 0
    columna:int        = 0
    hijos:  list       = field(default_factory=list)

    def agregar(self, hijo: "NodoAST") -> "NodoAST":
        if hijo is not None:
            self.hijos.append(hijo)
        return self

    def __repr__(self):
        return f"NodoAST({self.tipo!r}, {self.valor!r})"


# ═══════════════════════════════════════════════════════════════════
#  ERROR SINTÁCTICO
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ErrorSintactico:
    mensaje:  str
    linea:    int
    columna:  int
    tipo_err: str = "Error"     # "Error" | "Advertencia"

    def __str__(self):
        return f"[{self.tipo_err}] Lín {self.linea}, Col {self.columna}: {self.mensaje}"


# ═══════════════════════════════════════════════════════════════════
#  CONJUNTOS DE TIPOS ÚTILES
# ═══════════════════════════════════════════════════════════════════

_TIPOS       = {"int", "float", "real", "bool"}
_REL_OPS     = {TipoToken.OP_MENOR, TipoToken.OP_MENOR_IGUAL,
                TipoToken.OP_MAYOR, TipoToken.OP_MAYOR_IGUAL,
                TipoToken.OP_IGUAL_IGUAL, TipoToken.OP_DIFERENTE}
_SUMA_OPS    = {TipoToken.OP_SUMA, TipoToken.OP_RESTA,
                TipoToken.OP_INCR, TipoToken.OP_DECR}
_MULT_OPS    = {TipoToken.OP_MULT, TipoToken.OP_DIV, TipoToken.OP_MOD}
_LOG_OPS     = {TipoToken.OP_AND, TipoToken.OP_OR, TipoToken.OP_NOT}
_NUMEROS     = {TipoToken.NUMERO_ENTERO, TipoToken.NUMERO_REAL}
_CADENAS     = {TipoToken.CADENA_DOBLE, TipoToken.CADENA_SIMPLE}

# Tokens que pueden iniciar una sentencia
_INICIO_SENT = {
    "if", "while", "do", "cin", "cout",
}


# ═══════════════════════════════════════════════════════════════════
#  PARSER
# ═══════════════════════════════════════════════════════════════════

class Parser:
    """
    Analizador sintáctico descendente recursivo.

    Uso:
        parser = Parser(tokens)          # tokens sin comentarios ni errores
        ast, errores = parser.parsear()
    """

    def __init__(self, tokens: list[Token]):
        # Filtrar comentarios y tokens de error del léxico
        self._tokens: list[Token] = [
            t for t in tokens
            if t.tipo not in (TipoToken.COMENTARIO, TipoToken.ERROR,
                              TipoToken.ERROR_REAL)
        ]
        self._pos:    int               = 0
        self._errores: list[ErrorSintactico] = []

    # ──────────────────────────────────────────────────────────────
    #  API pública
    # ──────────────────────────────────────────────────────────────

    def parsear(self) -> tuple[Optional[NodoAST], list[ErrorSintactico]]:
        ast = self._programa()
        if not self._fin():
            tok = self._actual()
            self._error(f"Token inesperado '{tok.valor}' al final del programa",
                        tok.linea, tok.columna)
        return ast, self._errores

    # ──────────────────────────────────────────────────────────────
    #  Utilidades internas
    # ──────────────────────────────────────────────────────────────

    def _actual(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        # Token centinela EOF
        ultimo = self._tokens[-1] if self._tokens else Token(TipoToken.ERROR, "", 0, 0)
        return Token(TipoToken.ERROR, "EOF", ultimo.linea, ultimo.columna + 1)

    def _fin(self) -> bool:
        return self._pos >= len(self._tokens)

    def _avanzar(self) -> Token:
        tok = self._actual()
        self._pos += 1
        return tok

    def _es(self, *tipos: TipoToken) -> bool:
        return self._actual().tipo in tipos

    def _es_reservada(self, *palabras: str) -> bool:
        t = self._actual()
        return t.tipo == TipoToken.RESERVADA and t.valor in palabras

    def _consumir(self, tipo: TipoToken, descripcion: str = "") -> Optional[Token]:
        """Consume el token actual si coincide; si no, registra error y retorna None."""
        tok = self._actual()
        if tok.tipo == tipo:
            self._avanzar()
            return tok
        esperado = descripcion or tipo.value
        self._error(
            f"Se esperaba {esperado}, se encontró '{tok.valor}' ({tok.tipo.value})",
            tok.linea, tok.columna
        )
        return None

    def _consumir_reservada(self, palabra: str) -> Optional[Token]:
        tok = self._actual()
        if tok.tipo == TipoToken.RESERVADA and tok.valor == palabra:
            self._avanzar()
            return tok
        self._error(
            f"Se esperaba '{palabra}', se encontró '{tok.valor}' ({tok.tipo.value})",
            tok.linea, tok.columna
        )
        return None

    def _error(self, mensaje: str, linea: int, columna: int,
               tipo_err: str = "Error"):
        self._errores.append(ErrorSintactico(mensaje, linea, columna, tipo_err))

    def _sincronizar(self, *tokens_sync):
        """
        Recuperación de pánico: avanza hasta encontrar uno de los
        tokens de sincronización para intentar continuar el análisis.
        """
        while not self._fin():
            t = self._actual()
            if t.tipo in tokens_sync:
                return
            if t.tipo == TipoToken.RESERVADA and t.valor in (
                "end", "else", "while", "do", "if", "cin", "cout"
            ):
                return
            self._avanzar()

    # ──────────────────────────────────────────────────────────────
    #  GRAMÁTICA
    # ──────────────────────────────────────────────────────────────

    # programa → main { lista_declaracion }
    def _programa(self) -> NodoAST:
        nodo = NodoAST("Programa", "programa")
        tok_main = self._consumir_reservada("main")
        if tok_main:
            nodo.linea   = tok_main.linea
            nodo.columna = tok_main.columna
        self._consumir(TipoToken.LLAVE_A, "'{'")
        nodo.agregar(self._lista_declaracion())
        self._consumir(TipoToken.LLAVE_C, "'}'")
        return nodo

    # lista_declaracion → declaracion+
    def _lista_declaracion(self) -> NodoAST:
        nodo = NodoAST("ListaDeclaracion", "lista_decl")
        while not self._fin() and not self._es(TipoToken.LLAVE_C):
            decl = self._declaracion()
            if decl:
                nodo.agregar(decl)
            else:
                # Sincronizar ante token inesperado
                t = self._actual()
                if not self._fin() and not self._es(TipoToken.LLAVE_C):
                    self._error(f"Declaración o sentencia inválida: '{t.valor}'",
                                t.linea, t.columna)
                    self._avanzar()
        return nodo

    # declaracion → declaracion_variable | sentencia
    def _declaracion(self) -> Optional[NodoAST]:
        t = self._actual()
        # ¿Empieza con tipo? → declaración de variable
        if t.tipo == TipoToken.RESERVADA and t.valor in _TIPOS:
            return self._declaracion_variable()
        # ¿Empieza con sentencia conocida?
        return self._sentencia()

    # declaracion_variable → tipo identificador_lista ;
    def _declaracion_variable(self) -> NodoAST:
        tok_tipo = self._avanzar()          # consume int/float/real/bool
        nodo = NodoAST("DeclVariable", tok_tipo.valor,
                       tok_tipo.linea, tok_tipo.columna)
        nodo.agregar(self._identificador_lista())
        self._consumir(TipoToken.PUNTO_COMA, "';'")
        return nodo

    # identificador_lista → id { , id }
    def _identificador_lista(self) -> NodoAST:
        nodo = NodoAST("IdentificadorLista", "ids")
        tok = self._consumir(TipoToken.IDENTIFICADOR, "identificador")
        if tok:
            nodo.agregar(NodoAST("Identificador", tok.valor,
                                 tok.linea, tok.columna))
        while self._es(TipoToken.COMA):
            self._avanzar()
            tok = self._consumir(TipoToken.IDENTIFICADOR, "identificador")
            if tok:
                nodo.agregar(NodoAST("Identificador", tok.valor,
                                     tok.linea, tok.columna))
        return nodo

    # sentencia → asignacion | seleccion | iteracion | repeticion
    #           | sent_in | sent_out
    def _sentencia(self) -> Optional[NodoAST]:
        t = self._actual()

        if t.tipo == TipoToken.IDENTIFICADOR:
            return self._asignacion()

        if t.tipo == TipoToken.RESERVADA:
            if t.valor == "if":
                return self._seleccion()
            if t.valor == "while":
                return self._iteracion()
            if t.valor == "do":
                return self._repeticion()
            if t.valor == "cin":
                return self._sent_in()
            if t.valor == "cout":
                return self._sent_out()

        return None

    # asignacion → id = sent_expresion
    def _asignacion(self) -> NodoAST:
        tok_id = self._avanzar()
        nodo = NodoAST("Asignacion", "=", tok_id.linea, tok_id.columna)
        nodo.agregar(NodoAST("Identificador", tok_id.valor,
                             tok_id.linea, tok_id.columna))
        self._consumir(TipoToken.ASIGNACION, "'='")
        nodo.agregar(self._sent_expresion())
        return nodo

    # sent_expresion → expresion ; | ;
    def _sent_expresion(self) -> NodoAST:
        nodo = NodoAST("SentExpresion", "sent_expr")
        if self._es(TipoToken.PUNTO_COMA):
            self._avanzar()
            return nodo
        nodo.agregar(self._expresion())
        self._consumir(TipoToken.PUNTO_COMA, "';'")
        return nodo

    # seleccion → if expresion then lista_sent [else lista_sent] end
    def _seleccion(self) -> NodoAST:
        tok = self._avanzar()   # consume 'if'
        nodo = NodoAST("Seleccion", "if", tok.linea, tok.columna)
        nodo.agregar(self._expresion())
        self._consumir_reservada("then")

        rama_then = NodoAST("RamaThen", "then")
        while not self._fin() and not self._es_reservada("else", "end"):
            s = self._sentencia()
            if s:
                rama_then.agregar(s)
            else:
                t = self._actual()
                if not self._es_reservada("else", "end") and not self._fin():
                    self._error(f"Sentencia inválida en bloque then: '{t.valor}'",
                                t.linea, t.columna)
                    self._avanzar()
        nodo.agregar(rama_then)

        if self._es_reservada("else"):
            self._avanzar()
            rama_else = NodoAST("RamaElse", "else")
            while not self._fin() and not self._es_reservada("end"):
                s = self._sentencia()
                if s:
                    rama_else.agregar(s)
                else:
                    t = self._actual()
                    if not self._es_reservada("end") and not self._fin():
                        self._error(f"Sentencia inválida en bloque else: '{t.valor}'",
                                    t.linea, t.columna)
                        self._avanzar()
            nodo.agregar(rama_else)

        self._consumir_reservada("end")
        return nodo

    # iteracion → while expresion { lista_sent } ;
    def _iteracion(self) -> NodoAST:
        tok = self._avanzar()   # consume 'while'
        nodo = NodoAST("Iteracion", "while", tok.linea, tok.columna)
        nodo.agregar(self._expresion())

        self._consumir(TipoToken.LLAVE_A, "'{'")
        cuerpo = NodoAST("CuerpoWhile", "cuerpo")
        while not self._fin() and not self._es(TipoToken.LLAVE_C):
            s = self._sentencia()
            if s:
                cuerpo.agregar(s)
            else:
                t = self._actual()
                if not self._es(TipoToken.LLAVE_C) and not self._fin():
                    self._error(f"Sentencia inválida en while: '{t.valor}'",
                                t.linea, t.columna)
                    self._avanzar()
        self._consumir(TipoToken.LLAVE_C, "'}'")
        self._consumir(TipoToken.PUNTO_COMA, "';'")
        nodo.agregar(cuerpo)
        return nodo

    # repeticion → do lista_sent until ( expresion ) ;
    #            | do lista_sent while expresion ;
    # NOTA: si dentro del do hay un while(cond){ } ese es una iteracion
    # anidada, NO el cierre del do. El while de cierre NO lleva { }.
    def _repeticion(self) -> NodoAST:
        tok = self._avanzar()   # consume 'do'
        nodo = NodoAST("Repeticion", "do", tok.linea, tok.columna)

        cuerpo = NodoAST("CuerpoDo", "cuerpo")
        while not self._fin():
            # Condición de salida: 'until' siempre cierra el do
            if self._es_reservada("until"):
                break
            # 'while' cierra el do SOLO si NO va seguido de '(' + expr + ')' + '{'
            # es decir, si el while tiene bloque { } es una iteracion anidada
            if self._es_reservada("while"):
                # lookahead: ¿el while va seguido de expresion y luego '{' ?
                # Si sí → es iteracion anidada (while normal)
                # Si no → es el while de cierre del do
                pos_actual = self._pos
                # Avanzamos temporalmente para ver si hay '{' después de la expresión
                # Forma simple: si justo después del while viene '(' es ambiguo,
                # pero el while de cierre NUNCA lleva '{', así que si encontramos
                # '{' antes del ';' entonces es iteración anidada.
                es_anidado = self._while_tiene_bloque()
                if not es_anidado:
                    break   # es el while de cierre del do
                # Si es anidado, lo parseamos como iteración normal
            s = self._sentencia()
            if s:
                cuerpo.agregar(s)
            else:
                t = self._actual()
                if not self._es_reservada("while", "until") and not self._fin():
                    self._error(f"Sentencia inválida en do: '{t.valor}'",
                                t.linea, t.columna)
                    self._avanzar()
        nodo.agregar(cuerpo)

        if self._es_reservada("until"):
            self._avanzar()
            nodo.valor = "do-until"
            self._consumir(TipoToken.PARENTESIS_A, "'('")
            nodo.agregar(self._expresion())
            self._consumir(TipoToken.PARENTESIS_C, "')'")
        else:
            self._consumir_reservada("while")
            nodo.agregar(self._expresion())

        self._consumir(TipoToken.PUNTO_COMA, "';'")
        return nodo

    def _while_tiene_bloque(self) -> bool:
        """
        Lookahead desde la posición actual (que apunta a 'while'):
        avanza buscando si hay un '{' antes del próximo ';' al nivel
        de profundidad 0 de paréntesis.
        Retorna True si este while es una iteración con bloque { }.
        """
        j = self._pos + 1   # saltar el 'while'
        profundidad_paren = 0
        while j < len(self._tokens):
            t = self._tokens[j]
            if t.tipo == TipoToken.PARENTESIS_A:
                profundidad_paren += 1
            elif t.tipo == TipoToken.PARENTESIS_C:
                profundidad_paren -= 1
            elif t.tipo == TipoToken.LLAVE_A and profundidad_paren == 0:
                return True   # encontró '{' → es iteración anidada
            elif t.tipo == TipoToken.PUNTO_COMA and profundidad_paren == 0:
                return False  # encontró ';' antes de '{' → es cierre del do
            j += 1
        return False

    # sent_in → cin id ;
    def _sent_in(self) -> NodoAST:
        tok = self._avanzar()   # consume 'cin'
        nodo = NodoAST("EntradaCin", "cin", tok.linea, tok.columna)
        # soportar opcionalmente '>>'
        if self._es(TipoToken.OP_MAYOR):
            self._avanzar()
            if self._es(TipoToken.OP_MAYOR):
                self._avanzar()
        tok_id = self._consumir(TipoToken.IDENTIFICADOR, "identificador")
        if tok_id:
            nodo.agregar(NodoAST("Identificador", tok_id.valor,
                                 tok_id.linea, tok_id.columna))
        self._consumir(TipoToken.PUNTO_COMA, "';'")
        return nodo

    # sent_out → cout salida ;
    def _sent_out(self) -> NodoAST:
        tok = self._avanzar()   # consume 'cout'
        nodo = NodoAST("SalidaCout", "cout", tok.linea, tok.columna)
        # soportar opcionalmente '<<'
        if self._es(TipoToken.OP_MENOR):
            self._avanzar()
            if self._es(TipoToken.OP_MENOR):
                self._avanzar()
        nodo.agregar(self._salida())
        self._consumir(TipoToken.PUNTO_COMA, "';'")
        return nodo

    # salida → cadena | expresion | cadena << expresion | expresion << cadena
    def _salida(self) -> NodoAST:
        nodo = NodoAST("Salida", "salida")
        if self._actual().tipo in _CADENAS:
            tok_cad = self._avanzar()
            nodo.agregar(NodoAST("Cadena", tok_cad.valor,
                                 tok_cad.linea, tok_cad.columna))
            # cadena << expresion
            if self._es(TipoToken.OP_MENOR):
                self._avanzar()
                if self._es(TipoToken.OP_MENOR):
                    self._avanzar()
                nodo.agregar(self._expresion())
        else:
            nodo.agregar(self._expresion())
            # expresion << cadena
            if self._es(TipoToken.OP_MENOR):
                self._avanzar()
                if self._es(TipoToken.OP_MENOR):
                    self._avanzar()
                if self._actual().tipo in _CADENAS:
                    tok_cad = self._avanzar()
                    nodo.agregar(NodoAST("Cadena", tok_cad.valor,
                                         tok_cad.linea, tok_cad.columna))
        return nodo

    # expresion → expr_rel { (&&  || ) expr_rel }
    # expr_rel  → expresion_simple [ rel_op expresion_simple ]
    def _expresion(self) -> NodoAST:
        nodo = self._expr_rel()
        # Soportar && y || encadenados: 4>2 && b>0 || c==1
        while self._actual().tipo in _LOG_OPS and self._actual().tipo != TipoToken.OP_NOT:
            tok_op = self._avanzar()
            nuevo = NodoAST("ExpLogica", tok_op.valor,
                            tok_op.linea, tok_op.columna)
            nuevo.agregar(nodo)
            nuevo.agregar(self._expr_rel())
            nodo = nuevo
        return nodo

    def _expr_rel(self) -> NodoAST:
        izq = self._expresion_simple()
        if self._actual().tipo in _REL_OPS:
            tok_op = self._avanzar()
            nodo = NodoAST("Expresion", tok_op.valor,
                           tok_op.linea, tok_op.columna)
            nodo.agregar(izq)
            nodo.agregar(self._expresion_simple())
            return nodo
        return izq

    # expresion_simple → termino { suma_op termino }
    def _expresion_simple(self) -> NodoAST:
        nodo = self._termino()
        while self._actual().tipo in _SUMA_OPS:
            tok_op = self._avanzar()
            nuevo = NodoAST("ExpSimple", tok_op.valor,
                            tok_op.linea, tok_op.columna)
            nuevo.agregar(nodo)
            nuevo.agregar(self._termino())
            nodo = nuevo
        return nodo

    # termino → factor { mult_op factor }
    def _termino(self) -> NodoAST:
        nodo = self._factor()
        while self._actual().tipo in _MULT_OPS:
            tok_op = self._avanzar()
            nuevo = NodoAST("Termino", tok_op.valor,
                            tok_op.linea, tok_op.columna)
            nuevo.agregar(nodo)
            nuevo.agregar(self._factor())
            nodo = nuevo
        return nodo

    # factor → componente { ^ componente }
    def _factor(self) -> NodoAST:
        nodo = self._componente()
        while self._es(TipoToken.OP_POT):
            tok_op = self._avanzar()
            nuevo = NodoAST("Factor", tok_op.valor,
                            tok_op.linea, tok_op.columna)
            nuevo.agregar(nodo)
            nuevo.agregar(self._componente())
            nodo = nuevo
        return nodo

    # componente → ( expresion ) | número | id | cadena
    #            | op_logico componente
    def _componente(self) -> NodoAST:
        t = self._actual()

        # ( expresion )
        if t.tipo == TipoToken.PARENTESIS_A:
            self._avanzar()
            nodo = NodoAST("Grupo", "()", t.linea, t.columna)
            nodo.agregar(self._expresion())
            self._consumir(TipoToken.PARENTESIS_C, "')'")
            return nodo

        # número entero o real
        if t.tipo in _NUMEROS:
            self._avanzar()
            return NodoAST("Numero", t.valor, t.linea, t.columna)

        # cadena
        if t.tipo in _CADENAS:
            self._avanzar()
            return NodoAST("Cadena", t.valor, t.linea, t.columna)

        # identificador
        if t.tipo == TipoToken.IDENTIFICADOR:
            self._avanzar()
            return NodoAST("Identificador", t.valor, t.linea, t.columna)

        # operador lógico unario prefix (!componente)
        if t.tipo in _LOG_OPS:
            tok_op = self._avanzar()
            nodo = NodoAST("OpLogico", tok_op.valor,
                           tok_op.linea, tok_op.columna)
            nodo.agregar(self._componente())
            return nodo

        # Reservadas que pueden aparecer en expresiones (bool literals)
        if t.tipo == TipoToken.RESERVADA and t.valor in ("true", "false"):
            self._avanzar()
            return NodoAST("BoolLiteral", t.valor, t.linea, t.columna)

        # Error: nada reconocible
        self._error(
            f"Componente inválido: '{t.valor}' ({t.tipo.value})",
            t.linea, t.columna
        )
        # Avanzar para no quedar atascado
        self._avanzar()
        return NodoAST("Error", t.valor, t.linea, t.columna)
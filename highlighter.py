"""
Resaltador de sintaxis con soporte real para comentarios multilínea.

Usa el mecanismo de estado de bloque de Qt (previousBlockState /
setCurrentBlockState) para manejar comentarios /* ... */ que abarcan
varias líneas, algo que highlightBlock() por sí solo no puede hacer
porque Qt lo invoca una línea a la vez.

Estados:
    ESTADO_NORMAL     (0) — línea fuera de cualquier comentario multilínea.
    ESTADO_COMENTARIO (1) — línea que sigue dentro de un /* ... */ abierto.
"""

import re
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)
from lexer import AnalizadorLexico, TipoToken, COLORES_TOKEN

# ── Estados de bloque ─────────────────────────────────────────────────────────
ESTADO_NORMAL     = 0
ESTADO_COMENTARIO = 1   # dentro de /* ... */ que no ha cerrado aún

# Regex para detectar inicio y fin de comentario multilínea
_RE_INICIO_ML = re.compile(r'/\*')
_RE_FIN_ML    = re.compile(r'\*/')


class ResaltadorSintaxis(QSyntaxHighlighter):
    """
    Resaltador que:
      • Usa el AnalizadorLexico real para colorear tokens en líneas normales.
      • Maneja /* ... */ multilínea con el mecanismo de estado de Qt.
      • Pasa verificar_balance=False al lexer para evitar falsos errores
        por delimitadores que abren en una línea y cierran en otra.
    """

    def __init__(self, document):
        super().__init__(document)
        self._lexer = AnalizadorLexico()

        # Formato reutilizable para comentarios (cualquier tipo)
        self._fmt_comentario = QTextCharFormat()
        self._fmt_comentario.setForeground(QColor(COLORES_TOKEN[TipoToken.COMENTARIO]))
        self._fmt_comentario.setFontItalic(True)

    # ─────────────────────────────────────────────────────────────────────────
    #  highlightBlock — Qt llama este método por cada línea visible/modificada
    # ─────────────────────────────────────────────────────────────────────────

    def highlightBlock(self, text: str):
        prev_state = self.previousBlockState()

        # ── Caso 1: venimos de dentro de un /* ... */ ─────────────────────────
        if prev_state == ESTADO_COMENTARIO:
            fin = _RE_FIN_ML.search(text)
            if fin:
                # El comentario cierra en esta línea
                self.setFormat(0, fin.end(), self._fmt_comentario)
                self.setCurrentBlockState(ESTADO_NORMAL)
                # Colorear lo que hay después del */
                self._colorear_fragmento(text[fin.end():], offset=fin.end())
            else:
                # Toda la línea sigue siendo parte del comentario
                self.setFormat(0, len(text), self._fmt_comentario)
                self.setCurrentBlockState(ESTADO_COMENTARIO)
            return

        # ── Caso 2: línea normal — buscar si abre un /* ───────────────────────
        self.setCurrentBlockState(ESTADO_NORMAL)

        inicio_ml = _RE_INICIO_ML.search(text)
        if inicio_ml:
            # Colorear la parte previa al /* con el lexer
            self._colorear_fragmento(text[:inicio_ml.start()], offset=0)

            # ¿Cierra también en esta línea?
            fin_ml = _RE_FIN_ML.search(text, inicio_ml.end())
            if fin_ml:
                # Comentario completo en una sola línea: /* ... */
                self.setFormat(
                    inicio_ml.start(),
                    fin_ml.end() - inicio_ml.start(),
                    self._fmt_comentario
                )
                self.setCurrentBlockState(ESTADO_NORMAL)
                # Colorear lo que hay después del */
                self._colorear_fragmento(text[fin_ml.end():], offset=fin_ml.end())
            else:
                # Abre pero no cierra: el resto de la línea es comentario
                self.setFormat(
                    inicio_ml.start(),
                    len(text) - inicio_ml.start(),
                    self._fmt_comentario
                )
                self.setCurrentBlockState(ESTADO_COMENTARIO)
            return

        # ── Caso 3: línea completamente normal ───────────────────────────────
        self._colorear_fragmento(text, offset=0)

    # ─────────────────────────────────────────────────────────────────────────
    #  _colorear_fragmento — aplica colores a un segmento de línea
    # ─────────────────────────────────────────────────────────────────────────

    def _colorear_fragmento(self, text: str, offset: int):
        """
        Colorea `text` usando el lexer y aplica los formatos al documento
        sumando `offset` a cada posición (porque `text` puede ser un
        fragmento que empieza en medio de la línea real).

        Se llama con verificar_balance=False para que el lexer no reporte
        errores de delimitadores sin cerrar (eso solo tiene sentido al
        analizar el archivo completo).
        """
        if not text.strip():
            return

        tokens, errores = self._lexer.analizar(text, verificar_balance=False)

        for token in tokens:
            color_hex = COLORES_TOKEN.get(token.tipo, "#FFFFFF")
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))

            if token.tipo == TipoToken.RESERVADA:
                fmt.setFontWeight(QFont.Weight.Bold)
            elif token.tipo == TipoToken.COMENTARIO:
                # Comentarios de una línea (// y #) los maneja el lexer normal
                fmt.setFontItalic(True)

            # Localizar la posición real del token dentro del fragmento.
            # token.columna es 1-based, así que restamos 1 para obtener
            # el índice 0-based y buscamos desde ahí por si hay tokens
            # repetidos con el mismo valor.
            start_hint = token.columna - 1
            start = text.find(token.valor, start_hint)
            if start == -1:
                start = start_hint

            self.setFormat(offset + start, len(token.valor), fmt)

        # Subrayar errores léxicos dentro del fragmento
        for error in errores:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#EF5350"))
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            fmt.setUnderlineColor(QColor("#EF5350"))
            col = error.columna - 1
            self.setFormat(offset + col, 1, fmt)
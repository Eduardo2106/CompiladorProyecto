"""
Resaltador de sintaxis basado en el Analizador Léxico.
Aplica colores a los tokens en tiempo real conforme se escribe.
"""

from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont
)
from PyQt6.QtCore import QRegularExpression

from lexer import AnalizadorLexico, TipoToken, COLORES_TOKEN


class ResaltadorSintaxis(QSyntaxHighlighter):
    """
    Resaltador de sintaxis que usa el AnalizadorLexico real (DFA)
    para colorear el texto del editor en tiempo real.
    """

    def __init__(self, document):
        super().__init__(document)
        self._lexer = AnalizadorLexico()

    def highlightBlock(self, text: str):
        """
        Qt llama este método para cada línea visible.
        Usamos el lexer sobre toda la línea.
        """
        if not text.strip():
            return

        tokens, errores = self._lexer.analizar(text)

        for token in tokens:
            color_hex = COLORES_TOKEN.get(token.tipo, "#FFFFFF")
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))

            # Estilo especial para palabras reservadas
            if token.tipo == TipoToken.RESERVADA:
                fmt.setFontWeight(QFont.Weight.Bold)

            # Estilo especial para comentarios
            elif token.tipo == TipoToken.COMENTARIO:
                fmt.setFontItalic(True)

            # Buscar la posición real del token en la línea
            start = text.find(token.valor, token.columna - 1)
            if start == -1:
                start = token.columna - 1
            length = len(token.valor)
            self.setFormat(start, length, fmt)

        # Marcar errores léxicos en rojo con subrayado
        for error in errores:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#EF5350"))
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
            fmt.setUnderlineColor(QColor("#EF5350"))
            col = error.columna - 1
            self.setFormat(col, 1, fmt)
"""
Widget de visualización del AST — árbol colapsable estilo explorador.
Se integra como pestaña en el panel de resultados del IDE.
"""

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFrame, QAbstractItemView
)
from PyQt6.QtGui import QColor, QFont, QIcon, QBrush
from PyQt6.QtCore import Qt

from parser import NodoAST


# ── Paleta de colores por tipo de nodo ───────────────────────────────────────
_COLOR_NODO = {
    "Programa":          "#CE93D8",   # lila
    "ListaDeclaracion":  "#B0BEC5",   # gris azulado
    "DeclVariable":      "#80DEEA",   # cyan
    "IdentificadorLista":"#80DEEA",
    "Identificador":     "#FFFFFF",   # blanco
    "Asignacion":        "#FFCC02",   # amarillo
    "Seleccion":         "#F48FB1",   # rosa
    "RamaThen":          "#F48FB1",
    "RamaElse":          "#F48FB1",
    "Iteracion":         "#A5D6A7",   # verde
    "CuerpoWhile":       "#A5D6A7",
    "Repeticion":        "#A5D6A7",
    "CuerpoDo":          "#A5D6A7",
    "EntradaCin":        "#4FC3F7",   # azul claro
    "SalidaCout":        "#4FC3F7",
    "Salida":            "#4FC3F7",
    "Expresion":         "#FFB74D",   # naranja
    "ExpSimple":         "#FFB74D",
    "Termino":           "#FFB74D",
    "Factor":            "#FFB74D",
    "Grupo":             "#E0E0E0",
    "Numero":            "#4FC3F7",
    "Cadena":            "#A5D6A7",
    "BoolLiteral":       "#CE93D8",
    "OpLogico":          "#F48FB1",
    "SentExpresion":     "#E0E0E0",
    "Error":             "#EF5350",   # rojo
}

_DEFAULT_COLOR = "#CCCCCC"

# ── Iconos de texto por tipo de nodo ─────────────────────────────────────────
_ICONO_NODO = {
    "Programa":          "⬡",
    "ListaDeclaracion":  "▤",
    "DeclVariable":      "📦",
    "IdentificadorLista":"⋯",
    "Identificador":     "⬜",
    "Asignacion":        "←",
    "Seleccion":         "⋄",
    "RamaThen":          "✓",
    "RamaElse":          "✗",
    "Iteracion":         "↻",
    "CuerpoWhile":       "↻",
    "Repeticion":        "↺",
    "CuerpoDo":          "↺",
    "EntradaCin":        "⬇",
    "SalidaCout":        "⬆",
    "Salida":            "⬆",
    "Expresion":         "≡",
    "ExpSimple":         "±",
    "Termino":           "×",
    "Factor":            "^",
    "Grupo":             "( )",
    "Numero":            "#",
    "Cadena":            '"',
    "BoolLiteral":       "B",
    "OpLogico":          "&&",
    "SentExpresion":     "→",
    "Error":             "✖",
}


class ArbolAST(QWidget):
    """
    Widget que muestra el AST como árbol colapsable.
    Incluye botones de expandir todo / colapsar todo y
    un contador de nodos.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Barra de herramientas del árbol ──
        barra = QFrame()
        barra.setStyleSheet("background:#141414; border-bottom:1px solid #2a2a2a;")
        barra.setFixedHeight(34)
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(8, 2, 8, 2)

        self.lbl_info = QLabel("AST — sin análisis")
        self.lbl_info.setStyleSheet("color:#888; font-family:Consolas; font-size:10pt;")

        btn_style = """
            QPushButton {
                background:#1e1e1e; color:#aaa;
                border:1px solid #333; border-radius:3px;
                padding:2px 10px; font-family:Consolas; font-size:10pt;
            }
            QPushButton:hover { background:#2a2a2a; color:#fff; }
        """
        btn_expandir = QPushButton("Expandir todo")
        btn_colapsar = QPushButton("Colapsar todo")
        btn_expandir.setStyleSheet(btn_style)
        btn_colapsar.setStyleSheet(btn_style)
        btn_expandir.clicked.connect(lambda: self.tree.expandAll())
        btn_colapsar.clicked.connect(lambda: self.tree.collapseAll())

        barra_layout.addWidget(self.lbl_info)
        barra_layout.addStretch()
        barra_layout.addWidget(btn_expandir)
        barra_layout.addWidget(btn_colapsar)
        layout.addWidget(barra)

        # ── QTreeWidget ──
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFont(QFont("Consolas", 10))
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1a1a1a;
                color: #cccccc;
                border: none;
            }
            QTreeWidget::item {
                padding: 2px 4px;
                border-radius: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #2a4a6a;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background-color: #222222;
            }
            QTreeWidget::branch {
                background: transparent;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: none;
            }
            QTreeWidget::branch:closed:has-children {
                color: #4fc3f7;
            }
            QTreeWidget::branch:open:has-children {
                color: #4fc3f7;
            }
        """)
        layout.addWidget(self.tree)

    # ── API pública ──────────────────────────────────────────────────────────

    def cargar_ast(self, nodo_raiz: NodoAST):
        """Carga y muestra el AST en el árbol."""
        self.tree.clear()
        if nodo_raiz is None:
            self.lbl_info.setText("AST vacío")
            return

        contador = [0]
        item_raiz = self._construir_item(nodo_raiz, contador)
        self.tree.addTopLevelItem(item_raiz)
        self.tree.expandAll()          # expandido completo al cargar (requisito)
        self.tree.resizeColumnToContents(0)

        self.lbl_info.setText(f"AST — {contador[0]} nodos")

    def limpiar(self):
        self.tree.clear()
        self.lbl_info.setText("AST — sin análisis")

    # ── Construcción recursiva ────────────────────────────────────────────────

    def _construir_item(self, nodo: NodoAST,
                        contador: list) -> QTreeWidgetItem:
        contador[0] += 1

        icono  = _ICONO_NODO.get(nodo.tipo, "○")
        color  = _COLOR_NODO.get(nodo.tipo, _DEFAULT_COLOR)

        # Texto del nodo: icono + tipo + valor (si tiene)
        if nodo.valor and nodo.valor not in (nodo.tipo.lower(), ""):
            label = f"{icono}  {nodo.tipo}  ›  {nodo.valor}"
        else:
            label = f"{icono}  {nodo.tipo}"

        # Posición si está disponible
        if nodo.linea:
            label += f"   [L{nodo.linea}:{nodo.columna}]"

        item = QTreeWidgetItem([label])
        item.setForeground(0, QBrush(QColor(color)))

        # Nodos hoja en negrita si son identificadores/números/cadenas
        if nodo.tipo in ("Identificador", "Numero", "Cadena", "BoolLiteral"):
            font = QFont("Consolas", 10)
            font.setBold(True)
            item.setFont(0, font)

        # Nodos de error resaltados con fondo rojizo
        if nodo.tipo == "Error":
            item.setBackground(0, QBrush(QColor("#3a1a1a")))

        for hijo in nodo.hijos:
            item.addChild(self._construir_item(hijo, contador))

        return item
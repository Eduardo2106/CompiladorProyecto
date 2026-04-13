import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog,
    QTabWidget, QSplitter, QWidget, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QToolBar, QStatusBar, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PyQt6.QtGui import (
    QAction, QColor, QTextFormat, QPainter, QIcon, QFont,
    QTextCharFormat, QTextCursor
)
from PyQt6.QtCore import Qt, QRect, QSize, QTimer

from lexer import AnalizadorLexico, TipoToken, COLORES_TOKEN, Token, ErrorLexico
from highlighter import ResaltadorSintaxis


# ================= 1. COMPONENTES DE INTERFAZ (EDITOR) =================

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFont(QFont("Consolas", 11))
        self.setPlaceholderText("Escriba aquí...")

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                selection-background-color: #3a3a3a;
            }
        """)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 15 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#141414"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#ffffff"))
                painter.drawText(
                    0, top,
                    self.lineNumberArea.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            if block.isValid():
                bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


# ================= 2. TABLA DE TOKENS =================

class TablaTokens(QTableWidget):
    """Widget de tabla para mostrar los tokens encontrados (sin comentarios)."""

    COLUMNAS = ["#", "Token", "Tipo", "Línea", "Columna"]

    def __init__(self):
        super().__init__()
        self.setColumnCount(len(self.COLUMNAS))
        self.setHorizontalHeaderLabels(self.COLUMNAS)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                gridline-color: #2a2a2a;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #2a4a6a;
            }
            QTableWidget::item:alternate {
                background-color: #222222;
            }
            QHeaderView::section {
                background-color: #141414;
                color: #aaaaaa;
                padding: 4px;
                border: 1px solid #2a2a2a;
                font-weight: bold;
            }
        """)

    def cargar_tokens(self, tokens: list[Token]):
        self.setRowCount(0)
        for i, tok in enumerate(tokens):
            self.insertRow(i)
            color = QColor(COLORES_TOKEN.get(tok.tipo, "#FFFFFF"))

            items = [
                str(i + 1),
                tok.valor,
                tok.tipo.value,
                str(tok.linea),
                str(tok.columna),
            ]
            for j, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(color if j in (1, 2) else QColor("#aaaaaa"))
                self.setItem(i, j, item)


# ================= 3. TABLA DE ERRORES LÉXICOS =================

class TablaErrores(QTableWidget):
    """Widget de tabla para mostrar los errores léxicos."""

    COLUMNAS = ["#", "Carácter / Descripción", "Línea", "Columna"]

    def __init__(self):
        super().__init__()
        self.setColumnCount(len(self.COLUMNAS))
        self.setHorizontalHeaderLabels(self.COLUMNAS)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                gridline-color: #2a2a2a;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #4a2a2a;
            }
            QHeaderView::section {
                background-color: #141414;
                color: #aaaaaa;
                padding: 4px;
                border: 1px solid #2a2a2a;
                font-weight: bold;
            }
        """)

    def cargar_errores(self, errores: list[ErrorLexico]):
        self.setRowCount(0)
        for i, err in enumerate(errores):
            self.insertRow(i)
            items = [str(i + 1), err.caracter, str(err.linea), str(err.columna)]
            for j, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setForeground(QColor("#EF5350") if j == 1 else QColor("#aaaaaa"))
                self.setItem(i, j, item)


# ================= 4. VENTANA PRINCIPAL (IDE) =================

class CompiladorIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDE - Compilador  |  Analizador Léxico")
        self.setGeometry(100, 100, 1400, 850)
        self.archivo_actual = None
        self._lexer = AnalizadorLexico()

        # Timer para análisis automático con debounce
        self._timer_analisis = QTimer()
        self._timer_analisis.setSingleShot(True)
        self._timer_analisis.timeout.connect(self._ejecutar_analisis_lexico)

        self.init_ui()

    def init_ui(self):
        # ── Menús ────────────────────────────────────────────────────
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1a1a1a;
                color: #cccccc;
            }
            QMenuBar::item:selected { background-color: #2a2a2a; }
            QMenu { background-color: #1a1a1a; color: #cccccc; border: 1px solid #333; }
            QMenu::item:selected { background-color: #2a4a6a; }
        """)

        menu_archivo = menubar.addMenu("Archivo")
        self._add_action(menu_archivo, "Nuevo",        "Ctrl+N", self.nuevo_archivo)
        self._add_action(menu_archivo, "Abrir",        "Ctrl+O", self.abrir_archivo)
        self._add_action(menu_archivo, "Cerrar",       "",       self.cerrar_archivo)
        menu_archivo.addSeparator()
        self._add_action(menu_archivo, "Guardar",      "Ctrl+S", self.guardar_archivo)
        self._add_action(menu_archivo, "Guardar como", "",       self.guardar_como)
        menu_archivo.addSeparator()
        self._add_action(menu_archivo, "Salir",        "Ctrl+Q", self.close)

        menu_compilar = menubar.addMenu("Compilar")
        self._add_action(menu_compilar, "▶  Análisis Léxico",     "F5",  self._ejecutar_analisis_lexico)
        self._add_action(menu_compilar, "Análisis Sintáctico",    "F6",  lambda: None)
        self._add_action(menu_compilar, "Análisis Semántico",     "F7",  lambda: None)
        self._add_action(menu_compilar, "Código Intermedio",      "F8",  lambda: None)
        self._add_action(menu_compilar, "Ejecutar",               "F9",  lambda: None)

        # ── Toolbar ──────────────────────────────────────────────────
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #1a1a1a;
                border-bottom: 1px solid #2a2a2a;
                spacing: 4px;
                padding: 2px 4px;
            }
            QToolButton {
                color: #cccccc;
                background: transparent;
                border: none;
                padding: 4px 8px;
                font-size: 16px;
            }
            QToolButton:hover { background-color: #2a2a2a; border-radius: 4px; }
        """)
        self.addToolBar(toolbar)
        toolbar.addAction("📄  Nuevo",   self.nuevo_archivo)
        toolbar.addAction("📂  Abrir",   self.abrir_archivo)
        toolbar.addAction("💾  Guardar", self.guardar_archivo)
        toolbar.addAction("❌  Cerrar",  self.cerrar_archivo)
        toolbar.addSeparator()
        act_lex = QAction("▶ Léxico ", self)
        act_lex.setToolTip("Ejecutar análisis léxico")
        act_lex.triggered.connect(self._ejecutar_analisis_lexico)
        act_lex.setFont(QFont("Consolas", 10))
        toolbar.addAction(act_lex)

        # ── Layout principal ──────────────────────────────────────────
        splitter_v = QSplitter(Qt.Orientation.Vertical)
        splitter_h = QSplitter(Qt.Orientation.Horizontal)

        # Editor con resaltador
        self.editor = CodeEditor()
        self.editor.cursorPositionChanged.connect(self._actualizar_status)
        self.editor.textChanged.connect(self._on_texto_cambiado)
        self._highlighter = ResaltadorSintaxis(self.editor.document())
        splitter_h.addWidget(self.editor)

        # Panel derecho: pestañas de resultados
        self.tabs_res = QTabWidget()
        self.tabs_res.setStyleSheet(self._tab_style())

        # ── Pestaña Léxico: tabla de tokens ──
        self.tabla_tokens = TablaTokens()
        self.tabs_res.addTab(self.tabla_tokens, " Léxico")

        # Pestañas de fases futuras (placeholder)
        for nombre in ["Sintáctico", "Semántico", "Tabla Hash", "Cód. Intermedio"]:
            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setFont(QFont("Consolas", 10))
            txt.setStyleSheet("background:#1a1a1a; color:#666; border:none;")
            txt.setPlaceholderText(f"[{nombre} — próxima fase]")
            self.tabs_res.addTab(txt, nombre)

        splitter_h.addWidget(self.tabs_res)
        splitter_h.setSizes([700, 500])
        splitter_v.addWidget(splitter_h)

        # ── Panel inferior: errores ───────────────────────────────────
        self.tabs_err = QTabWidget()
        self.tabs_err.setStyleSheet(self._tab_style())

        self.tabla_errores_lex = TablaErrores()
        self.tabs_err.addTab(self.tabla_errores_lex, "⚠ Errores Léxicos")

        for nombre in ["Errores Sintácticos", "Errores Semánticos", "Consola / Ejecución"]:
            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setFont(QFont("Consolas", 10))
            txt.setStyleSheet("background:#1a1a1a; color:#666; border:none;")
            txt.setPlaceholderText(f"[{nombre} — próxima fase]")
            self.tabs_err.addTab(txt, nombre)

        splitter_v.addWidget(self.tabs_err)
        splitter_v.setSizes([580, 220])

        self.setCentralWidget(splitter_v)

        # ── Barra de estado ──────────────────────────────────────────
        self.status = QStatusBar()
        self.status.setStyleSheet("""
            QStatusBar {
                background-color: #0d47a1;
                color: #ffffff;
                font-family: Consolas;
                font-size: 10pt;
            }
        """)
        self.setStatusBar(self.status)

        self.lbl_cursor  = QLabel("Lín: 1/1   Col: 1")
        self.lbl_tokens  = QLabel("Tokens: 0")
        self.lbl_errores = QLabel("Errores: 0")
        self.lbl_archivo = QLabel("Sin archivo")

        for lbl in (self.lbl_cursor, self.lbl_tokens, self.lbl_errores, self.lbl_archivo):
            lbl.setStyleSheet("color:#ffffff; padding: 0 8px;")

        self.status.addWidget(self.lbl_cursor)
        self.status.addWidget(QLabel("|"))
        self.status.addWidget(self.lbl_tokens)
        self.status.addWidget(QLabel("|"))
        self.status.addWidget(self.lbl_errores)
        self.status.addPermanentWidget(self.lbl_archivo)

        # Estilo general de la app
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; }
            QSplitter::handle { background-color: #2a2a2a; }
        """)

    # ── Helpers ──────────────────────────────────────────────────────

    def _tab_style(self):
        return """
            QTabWidget::pane { border: none; background: #1a1a1a; }
            QTabBar::tab {
                background: #141414;
                color: #888888;
                padding: 6px 14px;
                border: none;
                border-right: 1px solid #2a2a2a;
            }
            QTabBar::tab:selected { background: #1a1a1a; color: #ffffff; border-bottom: 2px solid #4fc3f7; }
            QTabBar::tab:hover { background: #222222; color: #cccccc; }
        """

    def _add_action(self, menu, name, shortcut, func):
        action = QAction(name, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(func)
        menu.addAction(action)

    def _actualizar_status(self):
        cursor = self.editor.textCursor()
        linea  = cursor.blockNumber() + 1
        col    = cursor.columnNumber() + 1
        total  = self.editor.blockCount()
        self.lbl_cursor.setText(f"Lín: {linea}/{total}   Col: {col}")

    def _on_texto_cambiado(self):
        """Dispara análisis léxico automático 600 ms después de dejar de escribir."""
        self._timer_analisis.start(600)

    # ── Análisis Léxico ───────────────────────────────────────────────

    def _ejecutar_analisis_lexico(self):
        codigo = self.editor.toPlainText()
        if not codigo.strip():
            self.tabla_tokens.setRowCount(0)
            self.tabla_errores_lex.setRowCount(0)
            self.lbl_tokens.setText("Tokens: 0")
            self.lbl_errores.setText("Errores: 0")
            return

        # verificar_balance=True: análisis completo del archivo
        tokens, errores = self._lexer.analizar(codigo, verificar_balance=True)

        # Los comentarios se resaltan en el editor pero NO se muestran
        # en la tabla de tokens — solo interesan al programador como
        # documentación, no como unidades léxicas del lenguaje.
        tokens_visibles = [t for t in tokens if t.tipo != TipoToken.COMENTARIO]

        self.tabla_tokens.cargar_tokens(tokens_visibles)
        self.tabla_errores_lex.cargar_errores(errores)

        self.lbl_tokens.setText(f"Tokens: {len(tokens_visibles)}")
        color_err = "#EF5350" if errores else "#A5D6A7"
        self.lbl_errores.setStyleSheet(f"color:{color_err}; padding: 0 8px;")
        self.lbl_errores.setText(f"Errores: {len(errores)}")

        # Cambiar a pestaña de errores si hay errores
        if errores:
            self.tabs_err.setCurrentIndex(0)
        else:
            self.tabs_res.setCurrentIndex(0)

        self.status.showMessage(
            f"Análisis léxico completado — {len(tokens_visibles)} tokens, {len(errores)} errores",
            4000
        )

    # ── Gestión de archivos ───────────────────────────────────────────

    def nuevo_archivo(self):
        self.editor.clear()
        self.archivo_actual = None
        self.lbl_archivo.setText("Sin archivo")
        self.status.showMessage("Nuevo archivo creado", 3000)

    def abrir_archivo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Archivo de Código", "",
            "Archivos de código (*.txt *.c *.cpp *.py *.lang);;Todos (*)"
        )
        if path:
            with open(path, 'r', encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.archivo_actual = path
            self.lbl_archivo.setText(os.path.basename(path))
            self.status.showMessage(f"Abierto: {path}", 3000)

    def guardar_archivo(self):
        if self.archivo_actual:
            with open(self.archivo_actual, 'w', encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.status.showMessage(f"Guardado: {self.archivo_actual}", 3000)
        else:
            self.guardar_como()

    def guardar_como(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", "",
            "Archivos de código (*.txt *.c *.cpp *.lang);;Todos (*)"
        )
        if path:
            self.archivo_actual = path
            self.lbl_archivo.setText(os.path.basename(path))
            self.guardar_archivo()

    def cerrar_archivo(self):
        self.editor.clear()
        self.archivo_actual = None
        self.lbl_archivo.setText("Sin archivo")
        self.tabla_tokens.setRowCount(0)
        self.tabla_errores_lex.setRowCount(0)
        self.lbl_tokens.setText("Tokens: 0")
        self.lbl_errores.setText("Errores: 0")
        self.status.showMessage("Archivo cerrado", 3000)


# ================= ENTRY POINT =================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from PyQt6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#1a1a1a"))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#cccccc"))
    palette.setColor(QPalette.ColorRole.Base,            QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#222222"))
    palette.setColor(QPalette.ColorRole.Text,            QColor("#cccccc"))
    palette.setColor(QPalette.ColorRole.Button,          QColor("#2a2a2a"))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#cccccc"))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#2a4a6a"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    ventana = CompiladorIDE()
    ventana.show()
    sys.exit(app.exec())
import sys
import re
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog,
    QTabWidget, QSplitter, QWidget, QPlainTextEdit, 
    QVBoxLayout, QHBoxLayout, QToolBar, QStatusBar, QLabel
)
from PyQt6.QtGui import QAction, QColor, QTextFormat, QPainter, QIcon, QFont
from PyQt6.QtCore import Qt, QRect, QSize


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
                    0,
                    top,
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


# ================= 2. VENTANA PRINCIPAL (IDE) =================

class CompiladorIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDE - Compilador")
        self.setGeometry(100, 100, 1200, 800)
        self.archivo_actual = None
        self.init_ui()

    def init_ui(self):

        # --- MENÚS ---
        menubar = self.menuBar()
        menu_archivo = menubar.addMenu("Archivo")

        self.add_action(menu_archivo, "Nuevo", self.nuevo_archivo)
        self.add_action(menu_archivo, "Abrir", self.abrir_archivo)
        self.add_action(menu_archivo, "Cerrar", self.cerrar_archivo)  # ← NUEVO
        menu_archivo.addSeparator()
        self.add_action(menu_archivo, "Guardar", self.guardar_archivo)
        self.add_action(menu_archivo, "Guardar como", self.guardar_como)
        menu_archivo.addSeparator()
        self.add_action(menu_archivo, "Salir", self.close)

        menu_compilar = menubar.addMenu("Compilar")
        self.add_action(menu_compilar, "Análisis Léxico", lambda: None)
        self.add_action(menu_compilar, "Análisis Sintáctico", lambda: None)
        self.add_action(menu_compilar, "Análisis Semántico", lambda: None)
        self.add_action(menu_compilar, "Código Intermedio", lambda: None)
        self.add_action(menu_compilar, "Ejecutar", lambda: None)

        # --- TOOLBAR ---
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        toolbar.addAction("📄", self.nuevo_archivo)
        toolbar.addAction("📂", self.abrir_archivo)
        toolbar.addAction("💾", self.guardar_archivo)
        toolbar.addAction("❌", self.cerrar_archivo)

        # --- SPLITTERS ---
        splitter_principal_v = QSplitter(Qt.Orientation.Vertical)
        splitter_superior_h = QSplitter(Qt.Orientation.Horizontal)

        # Editor
        self.editor = CodeEditor()
        self.editor.cursorPositionChanged.connect(self.actualizar_status)
        splitter_superior_h.addWidget(self.editor)

        # Panel derecho
        self.tabs_res = QTabWidget()
        self.txt_lex = QTextEdit()
        self.txt_sin = QTextEdit()
        self.txt_sem = QTextEdit()
        self.txt_hash = QTextEdit()
        self.txt_int = QTextEdit()

        for t, n in [
            (self.txt_lex, "Léxico"),
            (self.txt_sin, "Sintáctico"),
            (self.txt_sem, "Semántico"),
            (self.txt_hash, "Tabla Hash"),
            (self.txt_int, "Cód. Intermedio"),
        ]:
            t.setReadOnly(True)
            t.setFont(QFont("Consolas", 10))
            self.tabs_res.addTab(t, n)

        splitter_superior_h.addWidget(self.tabs_res)
        splitter_principal_v.addWidget(splitter_superior_h)

        # Panel inferior
        self.tabs_err = QTabWidget()
        self.err_lex = QTextEdit()
        self.err_sin = QTextEdit()
        self.err_sem = QTextEdit()
        self.res_exe = QTextEdit()

        for t, n in [
            (self.err_lex, "Errores Léxicos"),
            (self.err_sin, "Errores Sintácticos"),
            (self.err_sem, "Errores Semánticos"),
            (self.res_exe, "Consola / Ejecución"),
        ]:
            t.setReadOnly(True)
            t.setFont(QFont("Consolas", 10))
            self.tabs_err.addTab(t, n)

        splitter_principal_v.addWidget(self.tabs_err)
        self.setCentralWidget(splitter_principal_v)

        # Barra de estado
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.lbl_cursor = QLabel("Lín: 1/1  Col: 1")
        self.status.addWidget(self.lbl_cursor)

    def add_action(self, menu, name, func):
        action = QAction(name, self)
        action.triggered.connect(func)
        menu.addAction(action)

    def actualizar_status(self):
        cursor = self.editor.textCursor()
        linea = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        total = self.editor.blockCount()
        self.lbl_cursor.setText(f"Lín: {linea}/{total}   Col: {col}")

    # ================= GESTIÓN DE ARCHIVOS =================

    def nuevo_archivo(self):
        self.editor.clear()
        self.archivo_actual = None
        self.status.showMessage("Nuevo archivo creado", 3000)

    def abrir_archivo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Archivo de Código")
        if path:
            with open(path, 'r', encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.archivo_actual = path
            self.status.showMessage(f"Abierto: {path}", 3000)

    def guardar_archivo(self):
        if self.archivo_actual:
            with open(self.archivo_actual, 'w', encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.status.showMessage(f"Guardado: {self.archivo_actual}", 3000)
        else:
            self.guardar_como()

    def guardar_como(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar como")
        if path:
            self.archivo_actual = path
            self.guardar_archivo()

    def cerrar_archivo(self):
        self.editor.clear()
        self.archivo_actual = None
        self.status.showMessage("Archivo cerrado", 3000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Windows")
    ex = CompiladorIDE()
    ex.show()
    sys.exit(app.exec())
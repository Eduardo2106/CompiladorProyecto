import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog,
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMessageBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt


class CompiladorIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compilador")
        self.setGeometry(100, 100, 1200, 700)
        self.archivo_actual = None
        self.init_ui()

    def init_ui(self):
        self.crear_menu()
        self.crear_editor_y_paneles()
        # self.aplicar_estilos()  // Aquí se podrían aplicar estilos personalizados, falta agregar la funcion.
    


    # ---------------- MENÚ ----------------
    def crear_menu(self):
        menubar = self.menuBar()

        # ----- Archivo -----
        menu_archivo = menubar.addMenu("File")

        nuevo = QAction("Nuevo", self)
        nuevo.triggered.connect(self.nuevo_archivo)

        abrir = QAction("Abrir", self)
        abrir.triggered.connect(self.abrir_archivo)

        guardar = QAction("Guardar", self)
        guardar.triggered.connect(self.guardar_archivo)

        guardar_como = QAction("Guardar como", self)
        guardar_como.triggered.connect(self.guardar_como)

        salir = QAction("Salir", self)
        salir.triggered.connect(self.close)

        menu_archivo.addActions([nuevo, abrir, guardar, guardar_como, salir])

        # ----- Compilar -----
        menu_compilar = menubar.addMenu("Compilar")

        lexico = QAction("Análisis Léxico", self)
        lexico.triggered.connect(lambda: self.ejecutar_fase("lexico"))

        sintactico = QAction("Análisis Sintáctico", self)
        sintactico.triggered.connect(lambda: self.ejecutar_fase("sintactico"))

        semantico = QAction("Análisis Semántico", self)
        semantico.triggered.connect(lambda: self.ejecutar_fase("semantico"))

        intermedio = QAction("Código Intermedio", self)
        intermedio.triggered.connect(lambda: self.ejecutar_fase("intermedio"))

        ejecutar = QAction("Ejecutar", self)
        ejecutar.triggered.connect(lambda: self.ejecutar_fase("ejecutar"))

        menu_compilar.addActions([
            lexico, sintactico, semantico, intermedio, ejecutar
        ])

    # ---------------- INTERFAZ ----------------
    def crear_editor_y_paneles(self):
        splitter_principal = QSplitter(Qt.Orientation.Vertical)

        # ----- Parte superior -----
        splitter_superior = QSplitter(Qt.Orientation.Horizontal)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Escriba aquí...")
        splitter_superior.addWidget(self.editor)

        self.tabs_resultados = QTabWidget()
        self.tab_lexico = QTextEdit()
        self.tab_sintactico = QTextEdit()
        self.tab_semantico = QTextEdit()
        self.tab_hash = QTextEdit()
        self.tab_intermedio = QTextEdit()

        for tab in [
            self.tab_lexico, self.tab_sintactico,
            self.tab_semantico, self.tab_hash,
            self.tab_intermedio
        ]:
            tab.setReadOnly(True)

        self.tabs_resultados.addTab(self.tab_lexico, "Léxico")
        self.tabs_resultados.addTab(self.tab_sintactico, "Sintáctico")
        self.tabs_resultados.addTab(self.tab_semantico, "Semántico")
        self.tabs_resultados.addTab(self.tab_hash, "Hash Table")
        self.tabs_resultados.addTab(self.tab_intermedio, "Código Intermedio")

        splitter_superior.addWidget(self.tabs_resultados)

        # ----- Parte inferior -----
        self.tabs_errores = QTabWidget()
        self.err_lex = QTextEdit()
        self.err_sin = QTextEdit()
        self.err_sem = QTextEdit()
        self.resultados = QTextEdit()

        for tab in [self.err_lex, self.err_sin, self.err_sem, self.resultados]:
            tab.setReadOnly(True)

        self.tabs_errores.addTab(self.err_lex, "Errores Léxicos")
        self.tabs_errores.addTab(self.err_sin, "Errores Sintácticos")
        self.tabs_errores.addTab(self.err_sem, "Errores Semánticos")
        self.tabs_errores.addTab(self.resultados, "Resultados")

        splitter_principal.addWidget(splitter_superior)
        splitter_principal.addWidget(self.tabs_errores)

        self.setCentralWidget(splitter_principal)

    # ---------------- ARCHIVOS ----------------
    def nuevo_archivo(self):
        self.editor.clear()
        self.archivo_actual = None

    def abrir_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir archivo", "", "Archivos de texto (*.txt *.src)"
        )
        if ruta:
            with open(ruta, "r", encoding="utf-8") as f:
                self.editor.setText(f.read())
            self.archivo_actual = ruta

    def guardar_archivo(self):
        if self.archivo_actual:
            with open(self.archivo_actual, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
        else:
            self.guardar_como()

    def guardar_como(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", "", "Archivos de texto (*.txt *.src)"
        )
        if ruta:
            self.archivo_actual = ruta
            self.guardar_archivo()

    # ---------------- COMPILACIÓN ----------------
    def ejecutar_fase(self, fase):
        """
        Aquí se llamará al compilador externo con subprocess.
        Por ahora se simula la salida.
        """
        self.limpiar_salidas()

        if fase == "lexico":
            self.tab_lexico.setText("Tokens generados...\nID, NUM, OP")
        elif fase == "sintactico":
            self.tab_sintactico.setText("Árbol sintáctico generado")
        elif fase == "semantico":
            self.tab_semantico.setText("Análisis semántico correcto")
        elif fase == "intermedio":
            self.tab_intermedio.setText("t1 = a + b\nprint t1")
        elif fase == "ejecutar":
            self.resultados.setText("Ejecución finalizada correctamente")

    def limpiar_salidas(self):
        self.tab_lexico.clear()
        self.tab_sintactico.clear()
        self.tab_semantico.clear()
        self.tab_hash.clear()
        self.tab_intermedio.clear()
        self.err_lex.clear()
        self.err_sin.clear()
        self.err_sem.clear()
        self.resultados.clear()


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = CompiladorIDE()
    ventana.show()
    sys.exit(app.exec())

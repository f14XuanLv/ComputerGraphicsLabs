from custom_mesh import CustomMesh
import os
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QSpinBox, QComboBox
from PyQt5.QtWidgets import QSizePolicy, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont
OBJECT_FOLDER = "Object"  # 定义Object文件夹路径

def print_mesh_face(mesh):
    for i, face in enumerate(mesh.faces):
        print(f"Face {i}: {face}")

class SubdivisionWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, mesh, subdivision_type, iterations):
        super().__init__()
        self.mesh = mesh
        self.subdivision_type = subdivision_type
        self.iterations = iterations

    def run(self):
        subdivided_mesh = self.mesh.copy()
        for _ in range(self.iterations):
            if self.subdivision_type == "Loop":
                subdivided_mesh = subdivided_mesh.subdivide_loop()
            elif self.subdivision_type == "Catmull-Clark":
                subdivided_mesh = subdivided_mesh.subdivide_catmull_clark()
        self.finished.emit(subdivided_mesh)

class MeshViewer(QtWidgets.QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.mesh = None
        self.original_mesh = None
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.zoom = -5.0 
        self.draw_mode = GL_TRIANGLES
        self.normals = None
        self.last_x, self.last_y = 0, 0
        self.subdivision_worker = None
        
        self.setup_ui()
        self.load_mesh_files()
        self.load_selected_obj()

    def calculate_normals(self):
        if self.mesh is None:
            return
        self.mesh.calculate_normals()  # 使用CustomMesh类的calculate_normals方法

    def setup_ui(self):
        def create_button(text, callback):
            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 自适应大小
            button.clicked.connect(callback)
            return button
        
        def create_white_label(text):
            label = QLabel(text)
            label.setStyleSheet("QLabel { color : white; }")
            return label

        # 设置主布局
        layout = QVBoxLayout()

        # 按钮布局
        button_layout = QHBoxLayout()
        buttons = [
            ("点模式", self.set_point_mode),
            ("线框模式", self.set_line_mode),
            ("面模式", self.set_face_mode)
        ]

        for text, callback in buttons:
            button_layout.addWidget(create_button(text, callback))

        layout.addLayout(button_layout)

        # 细分控制布局
        subdivision_layout = QHBoxLayout()

        self.subdivision_type = QComboBox()
        self.subdivision_type.addItems(["Loop", "Catmull-Clark"])
        self.subdivision_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.subdivision_iterations = QSpinBox()
        self.subdivision_iterations.setRange(0, 5)
        self.subdivision_iterations.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        subdivide_button = create_button("细分", self.subdivide_mesh)
        reset_button = create_button("重置网格", self.reset_mesh)

        subdivision_layout.addWidget(create_white_label("细分类型:"))
        subdivision_layout.addWidget(self.subdivision_type)
        subdivision_layout.addWidget(create_white_label("细分次数:"))
        subdivision_layout.addWidget(self.subdivision_iterations)
        subdivision_layout.addWidget(subdivide_button)
        subdivision_layout.addWidget(reset_button)

        layout.addLayout(subdivision_layout)

        # 加载OBJ文件的选择控件
        obj_selection_layout = QHBoxLayout()
        self.obj_file_selector = QComboBox()
        self.obj_file_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.obj_file_selector.currentIndexChanged.connect(self.load_selected_obj)

        obj_selection_layout.addWidget(create_white_label("选择OBJ文件:"))
        obj_selection_layout.addWidget(self.obj_file_selector)

        layout.addLayout(obj_selection_layout)

        # 说明文字
        layout.addWidget(create_white_label("使用鼠标拖动旋转，滚轮缩放"))

        # 设置布局的伸缩因子
        layout.addStretch(1)

        self.setLayout(layout)

    def resizeEvent(self, event):
        """在窗口大小变化时调整控件的字体大小。"""
        new_font_size = max(self.width() // 90, 10)  # 根据窗口宽度动态调整字体大小
        font = QFont("Arial", new_font_size)

        # 遍历所有子控件并设置字体大小
        for widget in self.findChildren((QPushButton, QLabel, QComboBox, QSpinBox)):
            widget.setFont(font)

        super().resizeEvent(event)

    def load_mesh_files(self):
        """加载Object文件夹中的.obj文件"""
        if os.path.exists(OBJECT_FOLDER):
            obj_files = [f for f in os.listdir(OBJECT_FOLDER) if f.endswith('.obj')]
            self.obj_file_selector.clear()
            self.obj_file_selector.addItems(obj_files)
        else:
            print(f"文件夹 {OBJECT_FOLDER} 不存在")

    def load_selected_obj(self):
        """根据选择加载OBJ文件"""
        selected_file = self.obj_file_selector.currentText()
        if selected_file:
            file_path = os.path.join(OBJECT_FOLDER, selected_file)
            self.mesh = CustomMesh.from_obj(file_path)
            self.original_mesh = self.mesh.copy()
            self.update()

    def draw_mesh(self):
        if self.mesh is not None:
            if self.draw_mode == GL_POINTS:
                glDisable(GL_LIGHTING)
                glColor3f(1.0, 1.0, 1.0)
                glPointSize(4.0)
                glBegin(GL_POINTS)
                for vertex in self.mesh.vertices:
                    glVertex3fv(vertex)
                glEnd()
            elif self.draw_mode == GL_LINES:
                glDisable(GL_LIGHTING)
                glColor3f(1.0, 1.0, 1.0)
                glLineWidth(1.0)
                glBegin(GL_LINES)
                for face in self.mesh.faces:
                    for i in range(len(face)):
                        v0 = self.mesh.vertices[face[i]]
                        v1 = self.mesh.vertices[face[(i + 1) % len(face)]]
                        glVertex3fv(v0)
                        glVertex3fv(v1)
                glEnd()
            else:
                self.setup_lighting()
                glBegin(GL_TRIANGLES) 
                for face in self.mesh.faces:
                    for i in range(len(face) - 2):
                        v0, v1, v2 = face[0], face[i+1], face[i+2]
                        glNormal3fv(self.mesh.normals[v0])
                        glVertex3fv(self.mesh.vertices[v0])
                        glNormal3fv(self.mesh.normals[v1])
                        glVertex3fv(self.mesh.vertices[v1])
                        glNormal3fv(self.mesh.normals[v2])
                        glVertex3fv(self.mesh.vertices[v2])
                glEnd()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 1, 100)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, self.zoom)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        self.setup_lighting()
        self.draw_mesh()

    def setup_lighting(self):
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        light_position = [1.0, 1.0, 1.0, 0.0]
        light_ambient = [0.2, 0.2, 0.2, 1.0]
        light_diffuse = [0.8, 0.8, 0.8, 1.0]
        light_specular = [1.0, 1.0, 1.0, 1.0]

        glLightfv(GL_LIGHT0, GL_POSITION, light_position)
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)

    def set_point_mode(self):
        self.draw_mode = GL_POINTS
        self.update()

    def set_line_mode(self):
        self.draw_mode = GL_LINES
        self.update()

    def set_face_mode(self):
        self.draw_mode = GL_TRIANGLES
        self.update()

    def subdivide_mesh(self):
        if self.mesh is None:
            return

        subdivision_type = self.subdivision_type.currentText()
        iterations = self.subdivision_iterations.value()

        # 判断是否是三角网格
        is_trimesh = self.mesh.judge_is_trimesh()

        if subdivision_type == "Loop" and not is_trimesh:
            # 弹出提示：Loop细分会强制转换为三角网格
            msg_box = QMessageBox()
            msg_box.setWindowTitle("警告")
            msg_box.setText("如果此时使用了Loop细分，网格将会被强制转化成三角网格。")
            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            result = msg_box.exec_()

            if result == QMessageBox.Cancel:
                return  # 用户取消，不进行细分

        elif subdivision_type == "Catmull-Clark" and is_trimesh:
            # 弹出提示：三角网格用Loop细分效果更好
            msg_box = QMessageBox()
            msg_box.setWindowTitle("提示")
            msg_box.setText("当前网格是三角网格，使用Loop细分效果更好。")
            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            result = msg_box.exec_()

            if result == QMessageBox.Cancel:
                return  # 用户取消，不进行细分

        # 如果用户选择继续，则执行细分
        self.subdivision_worker = SubdivisionWorker(self.mesh, subdivision_type, iterations)
        self.subdivision_worker.finished.connect(self.on_subdivision_finished)
        self.subdivision_worker.start()

    def on_subdivision_finished(self, subdivided_mesh):
        self.mesh = subdivided_mesh
        self.calculate_normals()
        self.update()

    def reset_mesh(self):
        self.mesh = self.original_mesh.copy()
        self.calculate_normals()
        self.update()

    def mousePressEvent(self, event):
        self.last_x, self.last_y = event.x(), event.y()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.last_x
        dy = event.y() - self.last_y

        self.rotation_x += dy * 0.2
        self.rotation_y += dx * 0.2

        self.last_x, self.last_y = event.x(), event.y()

        self.update()

    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() * 0.005
        self.update()

def main():
    app = QApplication([])
    viewer = MeshViewer()
    viewer.resize(1920, 1080)
    viewer.show()
    app.exec_()

if __name__ == "__main__":
    main()

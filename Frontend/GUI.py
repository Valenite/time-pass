from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QStackedWidget, QWidget, QLineEdit,
    QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy
)
from PyQt5.QtGui import QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont, QPixmap, QTextBlockFormat
from PyQt5.QtCore import Qt, QSize, QTimer
from dotenv import dotenv_values
import os
import sys

# --- environment & paths (kept the same variable names you used) ---
env_vars = dotenv_values(".env")
Assistantname = env_vars.get("AssistantName")
current_dir = os.getcwd()
old_chat_message = ""
TempDirPath = rf"{current_dir}\Frontend\Files"
GraphicsDirPath = rf"{current_dir}\Frontend\Graphics"

# --- utility functions (kept names & logic) ---
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    # preserve original punctuation logic but make robust
    if any(word + " " in new_query for word in question_words):
        if len(query_words) > 0 and query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if len(query_words) > 0 and query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()

def SetMicrophoneStatus(Command):
    os.makedirs(TempDirPath, exist_ok=True)
    with open(rf'{TempDirPath}\Mic.data', 'w', encoding='utf-8') as file:
        file.write(Command)

def GetMicrophoneStatus():
    try:
        with open(rf'{TempDirPath}\Mic.data', 'r', encoding='utf-8') as file:
            Status = file.read()
    except Exception:
        Status = ""
    return Status

def SetAssistantStatus(Status):
    os.makedirs(TempDirPath, exist_ok=True)
    with open(rf'{TempDirPath}\Status.data', 'w', encoding='utf-8') as file:
        file.write(Status)

def GetAssistantStatus():
    try:
        with open(rf'{TempDirPath}\Status.data', 'r', encoding='utf-8') as file:
            Status = file.read()
    except Exception:
        Status = ""
    return Status

def MicButtonInitialized():
    SetMicrophoneStatus("False")

def MicButtonClosed():
    SetMicrophoneStatus("True")

def GraphicsDirectoryPath(Filename):
    Path = rf'{GraphicsDirPath}\{Filename}'
    return Path

def TempDirectoryPath(Filename):
    Path = rf'{TempDirPath}\{Filename}'
    return Path

def ShowTextToScreen(Text):
    os.makedirs(TempDirPath, exist_ok=True)
    with open(rf'{TempDirPath}\Responses.data', "w", encoding='utf-8') as file:
        file.write(Text)

# --- UI components ---
class ChatSection(QWidget):
    def __init__(self):
        super(ChatSection, self).__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 40, 40, 100)
        layout.setSpacing(8)

        self.chat_text_edit = QTextEdit()
        self.chat_text_edit.setReadOnly(True)
        self.chat_text_edit.setTextInteractionFlags(Qt.NoTextInteraction)
        self.chat_text_edit.setFrameStyle(QFrame.NoFrame)
        self.chat_text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # default font & color
        font = QFont()
        font.setPointSize(13)
        self.chat_text_edit.setFont(font)
        text_color = QColor(Qt.blue)
        text_color_text = QTextCharFormat()
        text_color_text.setForeground(text_color)
        self.chat_text_edit.setCurrentCharFormat(text_color_text)

        layout.addWidget(self.chat_text_edit)

        # gif label (single instance, no duplicate adding)
        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none; background: transparent;")
        movie_path = GraphicsDirectoryPath('Jarvis.gif')
        if os.path.exists(movie_path):
            movie = QMovie(movie_path)
            # set a reasonable scaled size
            movie.setScaledSize(QSize(480, 270))
            self.gif_label.setMovie(movie)
            movie.start()
        else:
            self.gif_label.setText("")  # keep widget but empty if file missing

        self.gif_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        layout.addWidget(self.gif_label, alignment=Qt.AlignRight | Qt.AlignBottom)

        # status label (shows mic/assistant status)
        self.label = QLabel("")
        self.label.setStyleSheet("color: white; font-size:16px; margin-right: 10px; background: transparent;")
        self.label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.label)

        # timer: consolidated, safer interval (200ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loadMessages)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(200)

        # scrollbar styling
        self.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: black;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: white;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: black;
                height: 10px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def loadMessages(self):
        global old_chat_message
        try:
            with open(TempDirectoryPath('Responses.data'), "r", encoding='utf-8') as file:
                messages = file.read()
        except Exception:
            messages = ""

        if not messages:
            return

        if str(old_chat_message) == str(messages):
            return

        self.addMessage(message=messages, color='white')
        old_chat_message = messages

    def SpeechRecogText(self):
        try:
            with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as file:
                messages = file.read()
        except Exception:
            messages = ""
        self.label.setText(messages)

    # kept name and signature
    def load_icon(self, path, width=60, height=60):
        # safe icon loader (in case icon_label isn't present)
        if not hasattr(self, 'icon_label'):
            return
        pixmap = QPixmap(path)
        new_pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(new_pixmap)

    def toggle_icon(self, event=None):
        # preserved logic but ensure toggled attribute exists
        if not hasattr(self, 'toggled'):
            self.toggled = True

        if self.toggled:
            self.load_icon(GraphicsDirectoryPath('voice.png'), 60, 60)
            MicButtonInitialized()
        else:
            self.load_icon(GraphicsDirectoryPath('mic.png'), 60, 60)
            MicButtonClosed()

        self.toggled = not self.toggled

    def addMessage(self, message, color):
        cursor = self.chat_text_edit.textCursor()
        format = QTextCharFormat()
        formatm = QTextBlockFormat()
        formatm.setTopMargin(10)
        formatm.setLeftMargin(10)
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        cursor.setBlockFormat(formatm)
        cursor.insertText(message + "\n")
        self.chat_text_edit.setTextCursor(cursor)
        # auto-scroll to bottom:
        self.chat_text_edit.ensureCursorVisible()

class InitialScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # determine screen size more robustly
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
        else:
            screen_width = 1280
            screen_height = 720

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        gif_label = QLabel()
        movie_path = GraphicsDirectoryPath('Jarvis.gif')
        if os.path.exists(movie_path):
            movie = QMovie(movie_path)
            max_gif_height = int(screen_width / 16 * 9)
            movie.setScaledSize(QSize(screen_width, max_gif_height))
            gif_label.setMovie(movie)
            movie.start()
        gif_label.setAlignment(Qt.AlignCenter)
        gif_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.icon_label = QLabel()
        pixmap_path = GraphicsDirectoryPath('Mic_on.png')
        if os.path.exists(pixmap_path):
            pixmap = QPixmap(pixmap_path)
            new_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(new_pixmap)
        self.icon_label.setFixedSize(150, 150)
        self.icon_label.setAlignment(Qt.AlignCenter)

        # preserve toggle state name
        self.toggled = True
        self.toggle_icon()  # initialize icons & status
        self.icon_label.mousePressEvent = self.toggle_icon

        self.label = QLabel("")
        self.label.setStyleSheet("color: white; font-size:16px; margin-bottom:0; background: transparent;")
        self.label.setAlignment(Qt.AlignCenter)

        content_layout.addWidget(gif_label, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.label, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        content_layout.setContentsMargins(0, 0, 0, 150)
        self.setLayout(content_layout)

        # allow the widget to expand to screen but don't force fixed size (more flexible)
        self.setMinimumHeight(screen_height // 2)
        self.setMinimumWidth(screen_width // 2)
        self.setStyleSheet("background-color: black;")  # fixed syntax

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(200)

    def SpeechRecogText(self):
        try:
            with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as file:
                messages = file.read()
        except Exception:
            messages = ""
        self.label.setText(messages)

    def load_icon(self, path, width=60, height=60):
        pixmap = QPixmap(path) if os.path.exists(path) else QPixmap()
        new_pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(new_pixmap)

    def toggle_icon(self, event=None):
        if not hasattr(self, 'toggled'):
            self.toggled = True

        if self.toggled:
            self.load_icon(GraphicsDirectoryPath('Mic_on.png'), 60, 60)
            MicButtonInitialized()
        else:
            self.load_icon(GraphicsDirectoryPath('Mic_off.png'), 60, 60)
            MicButtonClosed()

        self.toggled = not self.toggled

class MessageScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
        else:
            screen_width = 1280
            screen_height = 720

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel("")  # placeholder (you used one before)
        layout.addWidget(label)
        chat_section = ChatSection()
        layout.addWidget(chat_section)
        self.setLayout(layout)
        self.setStyleSheet("background-color: black;")
        self.setMinimumSize(screen_width // 2, screen_height // 2)

class CustomTopBar(QWidget):
    def __init__(self, parent, stacked_widget):
        super().__init__(parent)
        self.initUI()
        self.current_screen = None
        self.stacked_widget = stacked_widget

    def initUI(self):
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setAlignment(Qt.AlignRight)

        # home button
        home_button = QPushButton()
        home_icon = QIcon(GraphicsDirectoryPath("Home.png")) if os.path.exists(GraphicsDirectoryPath("Home.png")) else QIcon()
        home_button.setIcon(home_icon)
        home_button.setText(" Home")
        home_button.setStyleSheet("""
            height: 40px;
            line-height: 40px;
            background-color: white;
            color: black;
            padding: 4px 8px;
            border-radius: 6px;
        """)

        # message button
        message_button = QPushButton()
        message_icon = QIcon(GraphicsDirectoryPath("Chats.png")) if os.path.exists(GraphicsDirectoryPath("Chats.png")) else QIcon()
        message_button.setIcon(message_icon)
        message_button.setText(" Chat")
        message_button.setStyleSheet("""
            height: 40px;
            line-height: 40px;
            background-color: white;
            color: black;
            padding: 4px 8px;
            border-radius: 6px;
        """)

        # window control buttons
        minimize_button = QPushButton()
        minimize_icon = QIcon(GraphicsDirectoryPath("Minimize2.png")) if os.path.exists(GraphicsDirectoryPath("Minimize2.png")) else QIcon()
        minimize_button.setIcon(minimize_icon)
        minimize_button.setStyleSheet("background-color: white; border-radius: 6px;")
        minimize_button.clicked.connect(self.minimizeWindow)

        self.maximize_button = QPushButton()
        self.maximize_icon = QIcon(GraphicsDirectoryPath("Maximize.png")) if os.path.exists(GraphicsDirectoryPath("Maximize.png")) else QIcon()
        self.restore_icon = QIcon(GraphicsDirectoryPath("Minimize.png")) if os.path.exists(GraphicsDirectoryPath("Minimize.png")) else self.maximize_icon
        self.maximize_button.setIcon(self.maximize_icon)
        self.maximize_button.setFlat(True)
        self.maximize_button.setStyleSheet("background-color: white; border-radius: 6px;")
        self.maximize_button.clicked.connect(self.maximizeWindow)

        close_button = QPushButton()
        close_icon = QIcon(GraphicsDirectoryPath('Close.png')) if os.path.exists(GraphicsDirectoryPath('Close.png')) else QIcon()
        close_button.setIcon(close_icon)
        close_button.setStyleSheet("background-color: white; border-radius: 6px;")
        close_button.clicked.connect(self.closeWindow)

        # title
        title_label = QLabel(f" {str(Assistantname).capitalize()} AI    ")
        title_label.setStyleSheet("color: black; font-size: 18px; background-color: white; padding: 6px; border-radius: 6px;")

        # wire buttons to the stacked widget (preserving previous behavior)
        home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        layout.addWidget(title_label)
        layout.addStretch(1)
        layout.addWidget(home_button)
        layout.addWidget(message_button)
        layout.addStretch(1)
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)

        # small separating line at the far right (kept but simpler)
        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setFrameShape(QFrame.HLine)
        line_frame.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line_frame)

        self.draggable = True
        self.offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        super().paintEvent(event)

    def minimizeWindow(self):
        self.parent().showMinimized()

    def maximizeWindow(self):
        if self.parent().isMaximized():
            self.parent().showNormal()
            self.maximize_button.setIcon(self.maximize_icon)
        else:
            self.parent().showMaximized()
            self.maximize_button.setIcon(self.restore_icon)

    def closeWindow(self):
        self.parent().close()

    def mousePressEvent(self, event):
        if self.draggable:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.draggable and self.offset:
            new_pos = event.globalPos() - self.offset
            self.parent().move(new_pos)

    # helper methods kept (you used them earlier)
    def showMessageScreen(self):
        if self.current_screen is not None:
            self.current_screen.hide()
        message_screen = MessageScreen(self)
        layout = self.parent().layout()
        if layout is not None:
            layout.addWidget(message_screen)
        self.current_screen = message_screen

    def showInitialScreen(self):
        if self.current_screen is not None:
            self.current_screen.hide()
        initial_screen = InitialScreen(self)
        layout = self.parent().layout()
        if layout is not None:
            layout.addWidget(initial_screen)
        self.current_screen = initial_screen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.initUI()

    def initUI(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
        else:
            screen_width = 1280
            screen_height = 720

        stacked_widget = QStackedWidget(self)
        initial_screen = InitialScreen()
        message_screen = MessageScreen()
        stacked_widget.addWidget(initial_screen)
        stacked_widget.addWidget(message_screen)

        # set geometry & styles
        self.setGeometry(0, 0, screen_width, screen_height)
        self.setStyleSheet("background-color: black;")

        top_bar = CustomTopBar(self, stacked_widget)
        self.setMenuWidget(top_bar)
        self.setCentralWidget(stacked_widget)

def GraphicalUserInterface():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    GraphicalUserInterface()

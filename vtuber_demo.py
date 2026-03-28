import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import os
import requests
import json
import uuid
import time
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QTextCursor, QFont, QKeyEvent, QPixmap
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSignal, QObject
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget


# ==============================================
# 【信号类：解决跨线程UI操作问题】
# ==============================================
class VideoGenerateSignal(QObject):
    video_success = pyqtSignal(str)
    status_update = pyqtSignal(str)
    btn_enable = pyqtSignal(bool)
    append_chat = pyqtSignal(str, str)


# ==============================================
# ================= 重要配置区 =================
# 【换电脑 / 换模型 只需要改这里！！！】
# ==============================================
class Config:
    # ================ 1. AI 对话密钥（换电脑/换账号必须改） ================
    AI_TOKEN = "sk-odjilxR4Xwu5QURq2GAt6gNhA7nzvs1yYTaGhOg2qDccs3Lk"
    AI_API_URL = "https://vg.v1api.cc/v1/chat/completions"
    AI_MODEL = "gpt-3.5-turbo"

    # ================ 2. 数字人原视频 ID（必须改） ================
    # 你用的哪个数字人视频，就填哪个
    AVATAR_VIDEO_ID = "20260325181702877.mp4"

    # ================ 3. 本地服务地址（一般不用改） ================
    TTS_API_URL = "http://localhost:18180/v1/invoke"
    VIDEO_SUBMIT_URL = "http://localhost:8383/easy/submit"
    VIDEO_QUERY_URL = "http://localhost:8383/easy/query"

    # ================ 4. 文件保存路径（换电脑 100% 必须改！） ================
    # 新电脑的 data 目录一定要对应！
    WINDOWS_BASE_DIR = "d:/duix_avatar_data/face2face"
    DOCKER_BASE_DIR = "/code/data"

    # ================ 5. 语音克隆参考音频（换声音必须改） ================
    REFERENCE_AUDIO_PATH = "/code/data/origin_audio/format_denoise_20260325181702877.wav"
    REFERENCE_TEXT = "123456789101112131415。"

    # ================ 6. 数字人头像图片（换电脑必须改） ================
    # 新电脑上的头像图片路径
    AVATAR_IMAGE_PATH = ""  # 例：d:/duix_avatar_data/avatar.jpg

    # ===================== 固定配置 =====================
    SAVE_SUB_DIR = "temp"


# ==============================================
# 【1】云端AI对话
# ==============================================
def ai_chat(question):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.AI_TOKEN}"
    }

    data = {
        "model": Config.AI_MODEL,  # 换模型要改
        "messages": [
            {"role": "system", "content": "你是一个友好的助手，回答问题请使用完整的长句，至少说2句话，不要使用短句。"},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
        "stream": False,
        "max_tokens": 500
    }

    session = requests.Session()
    try:
        for retry in range(3):
            try:
                response = session.post(Config.AI_API_URL, headers=headers, json=data, timeout=60)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except:
                time.sleep(2)
                continue
        return "【AI 服务异常】网络连接失败"
    except Exception as e:
        return f"【AI 服务异常】{str(e)[:80]}"


# ==============================================
# 【2】本地TTS语音合成
# ==============================================
def text_to_audio(text):
    try:
        payload = {
            "text": text,
            "chunk_length": 100,
            "format": "wav",
            "reference_text": Config.REFERENCE_TEXT,
            "reference_audio": Config.REFERENCE_AUDIO_PATH,
            "references": [],
            "reference_id": None,
            "seed": None,
            "is_norm": 1,
            "use_memory_cache": "off",
            "normalize": True,
            "streaming": False,
            "max_new_tokens": 1024,
            "top_p": 0.7,
            "repetition_penalty": 1.2,
            "temperature": 0.7
        }

        resp = requests.post(Config.TTS_API_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            audio_filename = f"{uuid.uuid4().hex}.wav"
            win_path = os.path.join(Config.WINDOWS_BASE_DIR, Config.SAVE_SUB_DIR, audio_filename)
            with open(win_path, "wb") as f:
                f.write(resp.content)
            return audio_filename
        return None
    except:
        return None


# ==============================================
# 【3】本地数字人视频合成
# ==============================================
def generate_avatar_video(audio_filename):
    task_code = uuid.uuid4().hex
    try:
        payload = {
            "audio_url": audio_filename,
            "video_url": Config.AVATAR_VIDEO_ID,
            "code": task_code,
            "chaofen": 0,
            "watermark_switch": 0,
            "pn": 1
        }
        requests.post(Config.VIDEO_SUBMIT_URL, json=payload, timeout=30)

        for _ in range(60):
            try:
                res = requests.get(f"{Config.VIDEO_QUERY_URL}?code={task_code}", timeout=10).json()
                data = res.get("data", {})
                if data.get("status") == 2:
                    vid = data.get("result")
                    if vid:
                        fname = os.path.basename(vid)
                        paths = [
                            os.path.join(Config.WINDOWS_BASE_DIR, Config.SAVE_SUB_DIR, fname),
                            os.path.join(Config.WINDOWS_BASE_DIR, "result", fname)
                        ]
                        for p in paths:
                            if os.path.exists(p) and os.path.getsize(p) > 1024:
                                return p
                time.sleep(3)
            except:
                time.sleep(3)
        return None
    except:
        return None


# ==============================================
# 输入框（回车发送）
# ==============================================
class ChatTextEdit(QTextEdit):
    def __init__(self, parent=None, send_callback=None):
        super().__init__(parent)
        self.send_callback = send_callback

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and not event.modifiers():
            self.send_callback()
            return
        super().keyPressEvent(event)


# ==============================================
# 主窗口
# ==============================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Microsoft YaHei", 12))
        self.setWindowTitle("✨ AI数字人视频对话")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet("background-color:#f5f5f5;")

        self.signal = VideoGenerateSignal()
        self.signal.video_success.connect(self.on_video_success)
        self.signal.status_update.connect(self.update_status)
        self.signal.btn_enable.connect(self.update_btn_state)
        self.signal.append_chat.connect(self.append_chat_safe)

        self.current_video_path = ""
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("🎯 AI对话 → 数字人对口型视频")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:bold;")
        layout.addWidget(title)

        # 视频/照片区域
        self.media_container = QWidget()
        self.media_container.setFixedSize(480, 640)
        self.media_container.setStyleSheet("background:#000; border-radius:12px;")
        media_layout = QVBoxLayout(self.media_container)
        media_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.media_container, alignment=Qt.AlignCenter)

        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("background:#000;")
        self.load_avatar_image()
        media_layout.addWidget(self.avatar_label)

        self.video_widget = QVideoWidget()
        self.video_widget.hide()
        self.media_player.setVideoOutput(self.video_widget)
        media_layout.addWidget(self.video_widget)

        # 播放控制
        ctrl_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setFixedSize(100,40)
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet("color:white; background:#2196f3; border-radius:8px;")
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        self.reset_btn = QPushButton("🔄 显示照片")
        self.reset_btn.setFixedSize(150,40)
        self.reset_btn.setEnabled(False)
        self.reset_btn.setStyleSheet("color:white; background:#ff9800; border-radius:8px;")
        self.reset_btn.clicked.connect(self.show_avatar_image)
        ctrl_layout.addWidget(self.reset_btn)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        self.status_label = QLabel("✅ 就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#2196f3;")
        layout.addWidget(self.status_label)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("border-radius:15px; padding:15px; background:white;")
        layout.addWidget(self.chat, stretch=1)

        self.input_box = ChatTextEdit(send_callback=self.send_msg)
        self.input_box.setPlaceholderText("输入消息，回车发送")
        self.input_box.setFixedHeight(100)
        layout.addWidget(self.input_box)

        self.btn = QPushButton("🚀 发送并生成视频")
        self.btn.setFixedHeight(50)
        self.btn.setStyleSheet("background:#2196f3; color:white; border-radius:12px; font-size:15px;")
        self.btn.clicked.connect(self.send_msg)
        layout.addWidget(self.btn)

        self.media_player.stateChanged.connect(self.update_play_btn)

    def load_avatar_image(self):
        if Config.AVATAR_IMAGE_PATH and os.path.exists(Config.AVATAR_IMAGE_PATH):
            pix = QPixmap(Config.AVATAR_IMAGE_PATH).scaled(480,640,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            self.avatar_label.setPixmap(pix)
        else:
            self.avatar_label.setText("请配置头像路径")

    def show_avatar_image(self):
        self.media_player.stop()
        self.video_widget.hide()
        self.avatar_label.show()
        self.play_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

    def show_video_ui(self):
        self.avatar_label.hide()
        self.video_widget.show()
        self.play_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)

    def append_chat(self, role, txt):
        txt = txt.replace("\n","<br>")
        if role == "user":
            html = f"<div style='text-align:right;margin:8px'><span style='background:#2196f3;color:white;padding:10px 15px;border-radius:18px'>我：{txt}</span></div>"
        else:
            html = f"<div style='text-align:left;margin:8px'><span style='background:#eee;padding:10px 15px;border-radius:18px'>AI：{txt}</span></div>"
        self.chat.append(html)
        self.chat.moveCursor(QTextCursor.End)

    def append_chat_safe(self, r, t):
        self.append_chat(r,t)

    def send_msg(self):
        t = self.input_box.toPlainText().strip()
        if not t: return
        self.btn.setEnabled(False)
        self.input_box.clear()
        self.append_chat("user",t)
        from threading import Thread
        Thread(target=self.run_task, args=(t,), daemon=True).start()

    def run_task(self, text):
        self.signal.status_update.emit("🔄 AI思考中...")
        reply = ai_chat(text)
        self.signal.append_chat.emit("ai", reply)
        self.signal.status_update.emit("🔄 生成语音...")
        af = text_to_audio(reply)
        if not af:
            self.signal.status_update.emit("❌ 语音失败")
            self.signal.btn_enable.emit(True)
            return
        self.signal.status_update.emit("🔄 生成视频...")
        vp = generate_avatar_video(af)
        if vp:
            self.current_video_path = vp
            self.signal.video_success.emit(vp)
            self.signal.status_update.emit("✅ 完成！")
        else:
            self.signal.status_update.emit("❌ 视频失败")
        self.signal.btn_enable.emit(True)

    def on_video_success(self, p):
        self.show_video_ui()
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(p)))
        self.media_player.play()

    def toggle_play(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_play_btn(self, s):
        self.play_btn.setText("⏸️ 暂停" if s == QMediaPlayer.PlayingState else "▶️ 播放")

    def update_status(self, t):
        self.status_label.setText(t)

    def update_btn_state(self, e):
        self.btn.setEnabled(e)

    def closeEvent(self, e):
        self.media_player.stop()
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
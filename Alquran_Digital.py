import sys
import requests
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QComboBox,
                             QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont

# --- Worker untuk Tugas Latar Belakang (Networking) ---
class Worker(QObject):
    surah_list_ready = pyqtSignal(list)
    verse_data_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    @pyqtSlot()
    def fetch_surah_list(self):
        try:
            response = requests.get("https://api.quran.com/api/v4/chapters?language=id", timeout=10)
            response.raise_for_status()
            data = response.json().get('chapters', [])
            surah_list = [(s['id'], f"{s['id']}. {s['name_simple']}", s['verses_count']) for s in data]
            self.surah_list_ready.emit(surah_list)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Gagal mengambil daftar surat: {e}")

    @pyqtSlot(int, int)
    def fetch_verse_data(self, surah_id, ayah_number):
        url = (f"https://api.quran.com/api/v4/verses/by_key/{surah_id}:{ayah_number}"
               f"?language=id&translations=33&words=true&fields=text_uthmani,juz_number")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get('verse', {})
            self.verse_data_ready.emit(data)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Gagal memuat ayat: {e}")

# --- Kelas Utama Aplikasi ---
class QuranApp(QMainWindow):
    request_fetch_verse = pyqtSignal(int, int)
    CONFIG_FILE = "quran_config.json"

    def __init__(self):
        super().__init__()
        
        self.surah_list = []
        self.load_last_read()
        
        self.setWindowTitle("Al-Qur'an Digital")
        self.setGeometry(100, 100, 800, 700)
        self.setMinimumSize(650, 600)
        
        self.setup_styles()
        self.setup_ui()
        self.setup_worker_thread()

    def setup_styles(self):
        """Menerapkan tema warna dan style pada aplikasi."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QLabel {
                color: #333;
            }
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                selection-background-color: #1abc9c;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a085;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            #SaveButton {
                background-color: #3498db; /* Warna biru untuk tombol simpan */
            }
            #SaveButton:hover {
                background-color: #2980b9;
            }
            #ContentFrame {
                background-color: white;
                border-radius: 8px;
            }
            #InfoLabel {
                color: #16a085;
                font-weight: bold;
            }
            #ArabicLabel {
                color: #2c3e50;
            }
            #LatinLabel {
                color: #555;
            }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        font_arabic = QFont("Times New Roman", 28, QFont.Bold)
        font_latin = QFont("Segoe UI", 11); font_latin.setItalic(True)
        font_terjemahan = QFont("Segoe UI", 12)
        font_info = QFont("Segoe UI", 14)

        top_layout = QHBoxLayout()
        self.surah_combo = QComboBox()
        top_layout.addWidget(QLabel("Surat:"))
        top_layout.addWidget(self.surah_combo, 1)
        
        content_frame = QFrame()
        content_frame.setObjectName("ContentFrame")
        content_frame.setFrameShape(QFrame.StyledPanel)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(25, 25, 25, 25)

        self.info_label = QLabel("Selamat Datang!"); self.info_label.setObjectName("InfoLabel")
        self.info_label.setFont(font_info)
        
        self.arabic_label = QLabel("..."); self.arabic_label.setObjectName("ArabicLabel")
        self.arabic_label.setFont(font_arabic); self.arabic_label.setAlignment(Qt.AlignRight); 
        self.arabic_label.setWordWrap(True)
        
        self.latin_label = QLabel("..."); self.latin_label.setObjectName("LatinLabel")
        self.latin_label.setFont(font_latin); self.latin_label.setAlignment(Qt.AlignLeft); 
        self.latin_label.setWordWrap(True)

        separator = QFrame(); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken)

        self.translation_label = QLabel("...")
        self.translation_label.setFont(font_terjemahan); self.translation_label.setAlignment(Qt.AlignLeft);
        self.translation_label.setWordWrap(True)

        content_layout.addWidget(self.info_label, 0, Qt.AlignCenter)
        content_layout.addWidget(self.arabic_label)
        content_layout.addWidget(self.latin_label)
        content_layout.addWidget(separator)
        content_layout.addWidget(self.translation_label)
        content_layout.addStretch()

        # --- TOMBOL SIMPAN DITAMBAHKAN DI SINI ---
        bottom_layout = QHBoxLayout()
        self.prev_button = QPushButton("<< Sebelumnya")
        self.save_button = QPushButton("Simpan Tanda")
        self.save_button.setObjectName("SaveButton") # ID untuk styling
        self.next_button = QPushButton("Berikutnya >>")
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.prev_button)
        bottom_layout.addWidget(self.save_button) # Menambahkan tombol ke layout
        bottom_layout.addWidget(self.next_button)
        bottom_layout.addStretch()

        main_layout.addLayout(top_layout)
        main_layout.addWidget(content_frame, 1)
        main_layout.addLayout(bottom_layout)

        self.surah_combo.currentIndexChanged.connect(self.on_surah_selected)
        self.prev_button.clicked.connect(self.previous_ayah)
        self.next_button.clicked.connect(self.next_ayah)
        self.save_button.clicked.connect(self.save_current_position) # Menghubungkan tombol simpan

    def setup_worker_thread(self):
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.worker.surah_list_ready.connect(self.update_surah_combobox)
        self.worker.verse_data_ready.connect(self.update_ui_with_verse_data)
        self.worker.error.connect(self.show_error_message)
        self.request_fetch_verse.connect(self.worker.fetch_verse_data)
        self.thread.started.connect(self.worker.fetch_surah_list)
        self.thread.start()

    def load_last_read(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.current_surah_id = config.get('surah', 1)
                    self.current_ayah_number = config.get('ayah', 1)
                    return
        except (IOError, json.JSONDecodeError):
            pass
        self.current_surah_id = 1
        self.current_ayah_number = 1

    def save_last_read_to_file(self):
        """Fungsi inti untuk menyimpan data ke file."""
        config = {'surah': self.current_surah_id, 'ayah': self.current_ayah_number}
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            return True
        except IOError:
            return False
            
    @pyqtSlot()
    def save_current_position(self):
        """Slot untuk tombol simpan, memberikan notifikasi ke pengguna."""
        if self.save_last_read_to_file():
            QMessageBox.information(self, "Disimpan", f"Posisi terakhir Anda (QS. {self.current_surah_id}:{self.current_ayah_number}) telah disimpan.")
        else:
            QMessageBox.warning(self, "Gagal", "Tidak dapat menyimpan posisi terakhir.")

    @pyqtSlot(list)
    def update_surah_combobox(self, surah_list):
        self.surah_list = surah_list
        self.surah_combo.blockSignals(True)
        self.surah_combo.clear()
        self.surah_combo.addItems([s[1] for s in self.surah_list])
        
        target_index = next((i for i, surah in enumerate(self.surah_list) if surah[0] == self.current_surah_id), 0)
        self.surah_combo.setCurrentIndex(target_index)
        self.surah_combo.blockSignals(False)

        self.verse_count = self.surah_list[target_index][2]
        self.request_fetch_verse.emit(self.current_surah_id, self.current_ayah_number)
    
    @pyqtSlot(dict)
    def update_ui_with_verse_data(self, verse_data):
        teks_arab = verse_data.get('text_uthmani', 'Gagal memuat teks Arab.')
        words_list = verse_data.get('words', [])
        transliteration_parts = [word.get('transliteration', {}).get('text', '') for word in words_list]
        teks_latin = ' '.join(filter(None, transliteration_parts)) or "Transliterasi tidak tersedia."
        translations = verse_data.get('translations', [])
        teks_terjemahan = translations[0].get('text', 'Terjemahan tidak tersedia') if translations else 'Terjemahan tidak tersedia'
        cleaned_translation = teks_terjemahan.replace('<p>', '').replace('</p>', '').replace('<br>', '\n')
        juz_number = verse_data.get('juz_number', '')

        surah_name, _ = self.surah_list[self.surah_combo.currentIndex()][1].split('. ')
        info_text = f"QS. {surah_name} [{self.current_surah_id}:{self.current_ayah_number}]  •  Juz {juz_number}"
        self.info_label.setText(info_text)
        self.arabic_label.setText(teks_arab)
        self.latin_label.setText(teks_latin)
        self.translation_label.setText(cleaned_translation)
        
        self.prev_button.setEnabled(self.current_ayah_number > 1)
        self.next_button.setEnabled(self.current_ayah_number < self.verse_count)
    
    @pyqtSlot(int)
    def on_surah_selected(self, index):
        if not self.surah_list or index < 0: return
        self.current_surah_id, _, self.verse_count = self.surah_list[index]
        self.current_ayah_number = 1
        self.request_fetch_verse.emit(self.current_surah_id, self.current_ayah_number)
        
    def next_ayah(self):
        if self.current_ayah_number < self.verse_count:
            self.current_ayah_number += 1
            self.request_fetch_verse.emit(self.current_surah_id, self.current_ayah_number)

    def previous_ayah(self):
        if self.current_ayah_number > 1:
            self.current_ayah_number -= 1
            self.request_fetch_verse.emit(self.current_surah_id, self.current_ayah_number)
    
    @pyqtSlot(str)
    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def closeEvent(self, event):
        """Hanya menghentikan thread, tidak ada lagi simpan otomatis."""
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)

# --- Blok Eksekusi Utama ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QuranApp()
    window.show()
    sys.exit(app.exec_())

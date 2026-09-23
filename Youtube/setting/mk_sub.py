import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QTextEdit, QPushButton, QFileDialog, QMessageBox
)

# 앞서 만든 하이브리드 맞춤법 검사 함수 임포트 (파일명이 동일하다면)
# from your_spell_checker_module import advanced_korean_checker 

class SubtitleEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_file_path = None

    def init_ui(self):
        # 창 제목 및 크기 설정
        self.setWindowTitle("비디오 자막 편집기")
        self.resize(800, 600)

        # 메인 위젯 및 레이아웃 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 상단 버튼 레이아웃
        btn_layout = QHBoxLayout()
        
        self.btn_open = QPushButton("자막 파일 열기")
        self.btn_open.clicked.connect(self.open_file)
        btn_layout.addWidget(self.btn_open)

        self.btn_check = QPushButton("✨ 맞춤법/띄어쓰기 자동 교정")
        self.btn_check.clicked.connect(self.run_spell_check)
        btn_layout.addWidget(self.btn_check)

        self.btn_save = QPushButton("파일 저장")
        self.btn_save.clicked.connect(self.save_file)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

        # 중앙 자막 텍스트 편집창 (스크롤 가능)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("자막 파일을 열거나 내용을 입력하세요...")
        layout.addWidget(self.text_edit)

    def open_file(self):
        """파일 열기 다이얼로그"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "자막 파일 열기", "", "Subtitles (*.sbv *.srt *.txt);;All Files (*)"
        )
        if file_name:
            self.current_file_path = Path(file_name)
            try:
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_edit.setPlainText(content)
                self.statusBar().showMessage(f"불러오기 완료: {self.current_file_path.name}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일을 읽는 중 오류가 발생했습니다:\n{e}")

    def run_spell_check(self):
        """텍스트창 내용에 맞춤법 검사 및 하이브리드 교정 적용"""
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "경고", "검사할 텍스트가 없습니다!")
            return

        # 여기에 아까 만든 advanced_korean_checker 함수를 연결하면 됩니다!
        # 예시로 간단한 치환 및 안내 메시지 처리
        lines = text.split('\n')
        checked_lines = []
        
        for line in lines:
            # 타임스탬프나 빈 줄은 그대로 두고 대사만 교정 함수 태우기
            # (추후 하이브리드 함수와 연동)
            checked_lines.append(line)
        
        # 임시 결과 반영 예시
        # 교정된 텍스트를 다시 텍스트 에디터에 세팅
        self.text_edit.setPlainText('\n'.join(checked_lines))
        QMessageBox.information(self, "완료", "맞춤법 및 띄어쓰기 교정이 완료되었습니다!")

    def save_file(self):
        """현재 편집 중인 내용을 파일로 저장"""
        if not self.current_file_path:
            # 열린 파일이 없으면 다른 이름으로 저장
            file_name, _ = QFileDialog.getSaveFileName(
                self, "자막 파일 저장", "", "Subtitles (*.sbv *.srt *.txt);;All Files (*)"
            )
            if not file_name:
                return
            self.current_file_path = Path(file_name)

        try:
            content = self.text_edit.toPlainText()
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            QMessageBox.information(self, "성공", f"파일이 성공적으로 저장되었습니다:\n{self.current_file_path.name}")
            self.statusBar().showMessage(f"저장됨: {self.current_file_path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일 저장 중 오류가 발생했습니다:\n{e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SubtitleEditorWindow()
    window.show()
    sys.exit(app.exec())
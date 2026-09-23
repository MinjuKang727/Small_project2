import os
import sys
import ctypes
import shutil
import winreg
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Checkbutton, IntVar

def is_admin():
    """Windows 관리자 권한 여부 확인 함수"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class FontInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TTF/OTF 폰트 윈도우 자동 설치 프로그램")
        self.root.geometry("720x720")
        self.root.minsize(650, 620)
        self.root.configure(bg="#f8fafc") # 모던 슬레이트 배경 톤 적용

        # 메인 컨테이너 레이아웃
        main_frame = tk.Frame(root, bg="#f8fafc")
        main_frame.pack(fill="both", expand=True, padx=24, pady=24)

        # 상단 타이틀 및 설명
        title_label = tk.Label(main_frame, text="✨ TTF & OTF 폰트 윈도우 자동 설치기", font=("Segoe UI", 16, "bold"), bg="#f8fafc", fg="#0f172a")
        title_label.pack(anchor="w", pady=(0, 4))

        sub_label = tk.Label(main_frame, text="폴더 내 폰트 및 압축 파일을 탐색하여 윈도우에 자동 설치합니다. (정리 옵션 지원)", font=("Segoe UI", 9), bg="#f8fafc", fg="#64748b")
        sub_label.pack(anchor="w", pady=(0, 16))

        # 입력 및 옵션 설정용 카드 박스
        card_frame = tk.Frame(main_frame, bg="#ffffff", bd=1, relief="solid")
        card_frame.config(highlightbackground="#e2e8f0", highlightthickness=1)
        card_frame.pack(fill="x", pady=(0, 16), ipady=16, ipadx=16)

        lbl_path = tk.Label(card_frame, text="폰트 폴더 경로", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#334155")
        lbl_path.pack(anchor="w", padx=16, pady=(12, 6))

        path_inner_frame = tk.Frame(card_frame, bg="#ffffff")
        path_inner_frame.pack(fill="x", padx=16)

        self.path_entry = tk.Entry(path_inner_frame, font=("Consolas", 10), bg="#f8fafc", fg="#1e293b", relief="solid", bd=1, highlightbackground="#cbd5e1", highlightcolor="#4f46e5")
        self.path_entry.pack(side="left", expand=True, fill="x", ipady=8, padx=(0, 10))

        btn_browse = tk.Button(path_inner_frame, text="폴더 선택", command=self.select_folder, bg="#e2e8f0", fg="#1e293b", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", padx=16, pady=7)
        btn_browse.pack(side="right")

        # 체크박스 옵션 영역
        options_frame = tk.Frame(card_frame, bg="#ffffff")
        options_frame.pack(fill="x", padx=16, pady=(14, 0))

        self.extract_var = IntVar(value=1) # 압축 해제 여부 (기본: 켜짐)
        self.delete_zip_var = IntVar(value=0) # 압축된 원본 파일 삭제 여부
        self.delete_extracted_var = IntVar(value=1) # 압축 해제된 폴더 삭제 여부
        self.delete_all_var = IntVar(value=0) # 작업 완료 후 폴더 내 모든 파일 삭제 여부

        chk_style = {"font": ("Segoe UI", 9), "bg": "#ffffff", "fg": "#475569", "activebackground": "#ffffff", "cursor": "hand2", "anchor": "w"}
        chk_style_red = {"font": ("Segoe UI", 9), "bg": "#ffffff", "fg": "#dc2626", "activebackground": "#ffffff", "cursor": "hand2", "anchor": "w"}

        Checkbutton(options_frame, text="📁 폴더 내 압축 파일(ZIP) 자동 해제 후 설치", variable=self.extract_var, **chk_style).pack(fill="x", pady=2)
        Checkbutton(options_frame, text="🗑️ 압축 해제된 원본 압축 파일(.zip) 삭제", variable=self.delete_zip_var, **chk_style).pack(fill="x", pady=2)
        Checkbutton(options_frame, text="🧹 작업 완료 후 임시로 생성된 압축 해제 폴더 삭제", variable=self.delete_extracted_var, **chk_style).pack(fill="x", pady=2)
        Checkbutton(options_frame, text="🔥 작업 완료 후 선택한 폴더 내의 모든 파일/폴더 삭제", variable=self.delete_all_var, **chk_style_red).pack(fill="x", pady=2)

        # 설치 실행 버튼 (인디고 포인트 컬러)
        btn_install = tk.Button(card_frame, text="🚀 윈도우에 폰트 자동 설치 시작 (.ttf, .otf)", command=self.install_fonts, bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", activebackground="#4338ca", activeforeground="#ffffff", pady=10)
        btn_install.pack(fill="x", padx=16, pady=(16, 4))

        # 하단 로그 출력 영역
        lbl_log = tk.Label(main_frame, text="📌 진행 상황 및 결과 로그", font=("Segoe UI", 10, "bold"), bg="#f8fafc", fg="#334155")
        lbl_log.pack(anchor="w", pady=(8, 6))

        self.log_box = scrolledtext.ScrolledText(main_frame, font=("Consolas", 9), bg="#ffffff", fg="#1e293b", relief="solid", bd=1, highlightbackground="#e2e8f0")
        self.log_box.pack(expand=True, fill="both", pady=(0, 0))

    def select_folder(self):
        """폴더 선택 다이얼로그 호출"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder_selected)

    def install_fonts(self):
        """폰트 탐색, 중복 검사, 시스템 설치 및 정리 작업을 수행하는 핵심 메서드"""
        if not is_admin():
            messagebox.showerror("권한 오류", "Windows 시스템에 폰트를 설치하려면\n반드시 '관리자 권한'으로 프로그램을 실행해야 합니다!\n\n(우클릭 후 '관리자 권한으로 실행'을 선택해 주세요)")
            return

        folder_path = self.path_entry.get().strip()
        if not folder_path or not Path(folder_path).exists():
            messagebox.showwarning("경로 오류", "유효한 폴더 경로를 선택해주세요.")
            return

        source_path = Path(folder_path)

        self.log_box.delete("1.0", tk.END)
        self.log_box.insert(tk.END, f"🔍 작업 폴더 스캔 중: {source_path}\n\n")
        self.root.update()

        created_extracted_dirs = [] # 생성된 임시 해제 폴더 추적용 리스트

        # 1. 압축 파일 자동 해제 기능
        if self.extract_var.get() == 1:
            zip_files = list(source_path.glob("**/*.zip"))
            if zip_files:
                self.log_box.insert(tk.END, f"📦 총 {len(zip_files)}개의 압축 파일 발견. 해제를 시작합니다...\n")
                self.root.update()

                for zip_path in zip_files:
                    try:
                        extract_to = zip_path.parent / f"extracted_{zip_path.stem}"
                        extract_to.mkdir(exist_ok=True)
                        created_extracted_dirs.append(extract_to)

                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_to)
                        
                        self.log_box.insert(tk.END, f"  └ [해제 완료] {zip_path.name}\n")
                        self.root.update()

                        # 압축된 원본 파일 삭제 옵션이 켜져있다면 삭제
                        if self.delete_zip_var.get() == 1:
                            zip_path.unlink()
                            self.log_box.insert(tk.END, f"  └ [압축 파일 삭제됨] {zip_path.name}\n")
                            self.root.update()
                    except Exception as e:
                        self.log_box.insert(tk.END, f"  └ [해제 실패] {zip_path.name} ({e})\n")
                        self.root.update()
                self.log_box.insert(tk.END, "\n")

        # 2. 하위 폴더까지 .ttf, .otf 파일 재귀적 탐색
        font_files = []
        for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            font_files.extend(source_path.glob(f"**/{ext}"))
        font_files = list(set(font_files)) # 중복 제거
        
        if not font_files:
            messagebox.showinfo("알림", "선택한 폴더 및 하위 폴더에 사용 가능한 .ttf 또는 .otf 파일이 없습니다.")
            return

        self.log_box.insert(tk.END, f"🔍 총 {len(font_files)}개의 폰트 파일 발견. 중복 검사 및 설치를 시작합니다...\n\n")
        self.root.update()

        fonts_dir = Path(os.environ['WINDIR']) / 'Fonts'
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        
        installed_count = 0
        skipped_count = 0

        # 3. 레지스트리에서 이미 등록된 폰트 목록 미리 수집 (중복 검사용)
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ)
            registered_fonts = []
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(reg_key, i)
                    registered_fonts.append((name.lower(), value.lower()))
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(reg_key)
        except Exception:
            registered_fonts = []

        # 4. 각 폰트 파일별 설치 및 중복 패스 로직 처리
        for font_file in font_files:
            try:
                dest_path = fonts_dir / font_file.name
                ext = font_file.suffix.lower()
                font_type_label = "OpenType" if ext == ".otf" else "TrueType"
                font_title = f"{font_file.stem} ({font_type_label})".lower()
                file_name_lower = font_file.name.lower()

                is_already_installed = False
                if dest_path.exists():
                    is_already_installed = True
                else:
                    for reg_name, reg_val in registered_fonts:
                        if font_title in reg_name or file_name_lower in reg_val:
                            is_already_installed = True
                            break

                if is_already_installed:
                    self.log_box.insert(tk.END, f"⏭️ [이미 설치됨 - PASS] {font_file.name}\n")
                    self.root.update()
                    skipped_count += 1
                    continue

                shutil.copy(font_file, dest_path)
                
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, f"{font_file.stem} ({font_type_label})", 0, winreg.REG_SZ, font_file.name)
                
                ctypes.windll.gdi32.AddFontResourceW(str(dest_path))
                
                self.log_box.insert(tk.END, f"✅ [설치 완료] {font_file.name}\n")
                self.root.update()
                installed_count += 1
            except Exception as e:
                self.log_box.insert(tk.END, f"❌ [설치 실패] {font_file.name} ({e})\n")
                self.root.update()

        # 5. 윈도우 시스템 전체에 폰트 변경 브로드캐스트 전송
        if installed_count > 0:
            ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 2, 1000, None)

        # 6. 후속 정리 작업 (체크박스 옵션별 처리)
        self.log_box.insert(tk.END, "\n🧹 후속 정리 작업을 진행 중입니다...\n")
        self.root.update()

        # 압축 해제된 임시 폴더 삭제 옵션
        if self.delete_extracted_var.get() == 1:
            for ext_dir in created_extracted_dirs:
                if ext_dir.exists():
                    try:
                        shutil.rmtree(ext_dir)
                        self.log_box.insert(tk.END, f"  └ [임시 폴더 삭제됨] {ext_dir.name}\n")
                    except Exception as e:
                        self.log_box.insert(tk.END, f"  └ [임시 폴더 삭제 실패] {ext_dir.name} ({e})\n")
            self.root.update()

        # 작업 완료 후 선택한 폴더 내의 모든 파일/폴더 삭제 옵션
        if self.delete_all_var.get() == 1:
            try:
                for item in source_path.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                self.log_box.insert(tk.END, f"  🔥 [전체 삭제 완료] 선택한 폴더 내부의 모든 파일이 삭제되었습니다.\n")
            except Exception as e:
                self.log_box.insert(tk.END, f"  ❌ [전체 삭제 실패] ({e})\n")
            self.root.update()

        result_msg = f"\n✨ 설치 완료: {installed_count}개  |  ⏭️ 이미 설치됨: {skipped_count}개"
        self.log_box.insert(tk.END, f"{result_msg}\n")
        messagebox.showinfo("설치 작업 완료", f"총 {installed_count}개의 새로운 폰트가 설치되었습니다!")

if __name__ == "__main__":
    root = tk.Tk()
    app = FontInstallerApp(root)
    root.mainloop()
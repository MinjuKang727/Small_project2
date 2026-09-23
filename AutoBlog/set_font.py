import os
import sys
import ctypes
import shutil
import winreg
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def is_admin():
    """관리자 권한 확인 함수"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class FontInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TTF/OTF 폰트 윈도우 자동 설치 프로그램")
        self.root.geometry("720x580")
        self.root.minsize(650, 520)
        self.root.configure(bg="#f8fafc")

        # 메인 프레임
        main_frame = tk.Frame(root, bg="#f8fafc")
        main_frame.pack(fill="both", expand=True, padx=24, pady=24)

        # 타이틀 영역
        title_label = tk.Label(
            main_frame, 
            text="✨ TTF & OTF 폰트 윈도우 자동 설치기", 
            font=("Segoe UI", 16, "bold"), 
            bg="#f8fafc", 
            fg="#0f172a"
        )
        title_label.pack(anchor="w", pady=(0, 4))

        sub_label = tk.Label(
            main_frame, 
            text="폴더 내의 TTF, OTF 폰트를 하위 폴더까지 모두 탐색하여 윈도우에 자동으로 설치합니다. (중복 자동 패스)", 
            font=("Segoe UI", 9), 
            bg="#f8fafc", 
            fg="#64748b"
        )
        sub_label.pack(anchor="w", pady=(0, 20))

        # 카드 박스 영역
        card_frame = tk.Frame(main_frame, bg="#ffffff", bd=1, relief="solid")
        card_frame.config(highlightbackground="#e2e8f0", highlightthickness=1)
        card_frame.pack(fill="x", pady=(0, 16), ipady=16, ipadx=16)

        lbl_path = tk.Label(card_frame, text="폰트 폴더 경로", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#334155")
        lbl_path.pack(anchor="w", padx=16, pady=(12, 6))

        path_inner_frame = tk.Frame(card_frame, bg="#ffffff")
        path_inner_frame.pack(fill="x", padx=16)

        self.path_entry = tk.Entry(
            path_inner_frame, 
            font=("Consolas", 10), 
            bg="#f8fafc", 
            fg="#1e293b", 
            relief="solid", 
            bd=1,
            highlightbackground="#cbd5e1",
            highlightcolor="#4f46e5"
        )
        self.path_entry.pack(side="left", expand=True, fill="x", ipady=8, padx=(0, 10))

        btn_browse = tk.Button(
            path_inner_frame, 
            text="폴더 선택", 
            command=self.select_folder, 
            bg="#e2e8f0", 
            fg="#1e293b", 
            font=("Segoe UI", 9, "bold"), 
            relief="flat", 
            cursor="hand2",
            padx=16,
            pady=7
        )
        btn_browse.pack(side="right")

        # 실행 버튼
        btn_install = tk.Button(
            card_frame, 
            text="🚀 윈도우에 폰트 자동 설치 시작 (.ttf, .otf)", 
            command=self.install_fonts, 
            bg="#4f46e5", 
            fg="#ffffff", 
            font=("Segoe UI", 11, "bold"), 
            relief="flat", 
            cursor="hand2",
            activebackground="#4338ca",
            activeforeground="#ffffff",
            pady=10
        )
        btn_install.pack(fill="x", padx=16, pady=(16, 4))

        # 로그 출력 영역
        lbl_log = tk.Label(main_frame, text="📌 진행 상황 및 결과 로그", font=("Segoe UI", 10, "bold"), bg="#f8fafc", fg="#334155")
        lbl_log.pack(anchor="w", pady=(8, 6))

        self.log_box = scrolledtext.ScrolledText(
            main_frame, 
            font=("Consolas", 9), 
            bg="#ffffff", 
            fg="#1e293b", 
            relief="solid", 
            bd=1,
            highlightbackground="#e2e8f0"
        )
        self.log_box.pack(expand=True, fill="both", pady=(0, 0))

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder_selected)

    def install_fonts(self):
        if not is_admin():
            messagebox.showerror("권한 오류", "Windows 시스템에 폰트를 설치하려면\n반드시 '관리자 권한'으로 프로그램을 실행해야 합니다!\n\n(프로그램을 닫고 우클릭 후 '관리자 권한으로 실행'을 선택해 주세요)")
            return

        folder_path = self.path_entry.get().strip()
        if not folder_path or not Path(folder_path).exists():
            messagebox.showwarning("경로 오류", "유효한 폴더 경로를 선택해주세요.")
            return

        source_path = Path(folder_path)
        
        # 📌 .ttf와 .otf 파일 모두 탐색하도록 수정
        font_files = []
        for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            font_files.extend(source_path.glob(f"**/{ext}"))
        
        # 중복 경로 제거 (대소문자 차이 등으로 중복 수집 방지)
        font_files = list(set(font_files))
        
        if not font_files:
            messagebox.showinfo("알림", "선택한 폴더 및 하위 폴더에 .ttf 또는 .otf 파일이 없습니다.")
            return

        self.log_box.delete("1.0", tk.END)
        self.log_box.insert(tk.END, f"🔍 총 {len(font_files)}개의 폰트 파일(.ttf, .otf) 발견. 검사 및 설치를 시작합니다...\n\n")
        self.root.update()

        fonts_dir = Path(os.environ['WINDIR']) / 'Fonts'
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        
        installed_count = 0
        skipped_count = 0

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

        for font_file in font_files:
            try:
                dest_path = fonts_dir / font_file.name
                
                # 확장자에 따른 레지스트리 표기 방식 구분 (OTF는 OpenType, TTF는 TrueType)
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

        if installed_count > 0:
            ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 2, 1000, None)
        
        result_msg = f"\n✨ 설치 완료: {installed_count}개  |  ⏭️ 이미 설치되어 건너뜀(Pass): {skipped_count}개"
        self.log_box.insert(tk.END, f"{result_msg}\n")
        messagebox.showinfo("설치 작업 완료", f"총 {installed_count}개의 새로운 폰트가 설치되었습니다!")

if __name__ == "__main__":
    root = tk.Tk()
    app = FontInstallerApp(root)
    root.mainloop()
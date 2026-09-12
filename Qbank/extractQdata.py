import os, io, json, re, threading, pickle, gc, time, base64
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel, Label, Button, Canvas, Scrollbar, ttk
from PIL import Image, ImageTk
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pdf2image import convert_from_path
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db as firebase_db

# .env 로드
load_dotenv()
GH_TOKEN = os.getenv("GH_TOKEN")
GH_REPO = os.getenv("GH_REPO")
GH_BRANCH = os.getenv("GH_BRANCH", "main")

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleQuizExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("방송대 기출 추출 v5.6 (지문 정밀 편집)")
        self.root.geometry("900x800")
        
        self.current_photo = None 
        self.thumbnail_photos = [] 
        self.poppler_path = r'C:\Users\minju\Programming\Small_Project\Qbank\poppler-24.08.0\Library\bin' 

        self.btn_select = tk.Button(root, text="PDF 파일 선택 및 분석 시작", command=self.start_thread, 
                                    width=40, height=2, bg="#4285F4", fg="white", font=("맑은 고딕", 10, "bold"))
        self.btn_select.pack(pady=20)

        self.log_area = scrolledtext.ScrolledText(root, width=110, height=40, bg="#1e1e1e", fg="#ffffff", font=("Consolas", 10))
        self.log_area.pack(pady=10, padx=10)

        self.init_firebase()

    def log(self, message):
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    # --- 서비스 로직 ---
    def get_drive_service(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token: creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token: pickle.dump(creds, token)
        return build('drive', 'v3', credentials=creds)

    def ocr_image_bytes(self, img_bytes):
        try:
            service = self.get_drive_service()
            temp_ocr_p = f"temp_ocr_{int(time.time())}.png"
            with open(temp_ocr_p, "wb") as f: f.write(img_bytes)
            media = MediaFileUpload(temp_ocr_p, mimetype='image/png')
            file_metadata = {'name': 'ocr_processing', 'mimeType': 'application/vnd.google-apps.document'}
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = file.get('id')
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, service.files().export_media(fileId=file_id, mimeType='text/plain'))
            done = False
            while not done: _, done = downloader.next_chunk()
            extracted_text = fh.getvalue().decode('utf-8').strip()
            service.files().delete(fileId=file_id).execute()
            if os.path.exists(temp_ocr_p): os.remove(temp_ocr_p)
            return extracted_text
        except Exception as e:
            self.log(f"❌ OCR 에러: {e}")
            return None

    def start_thread(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF 파일", "*.pdf")])
        if files: threading.Thread(target=self.main_process, args=(files,), daemon=True).start()

    def main_process(self, files):
        service = self.get_drive_service()
        for f_path in files:
            temp_images = []
            self.log(f"🎬 분석 시작: {os.path.basename(f_path)}")
            try:
                pages = convert_from_path(f_path, 300, poppler_path=self.poppler_path)
                for i, page in enumerate(pages):
                    p = f"temp_{int(time.time())}_{i}.png"
                    page.save(p, "PNG")
                    temp_images.append(p)
                
                u_in = self.select_pages_and_info(temp_images)
                if not u_in or u_in.get("cancel"): continue

                full_text = ""
                for idx in u_in["indices"]:
                    img_p = temp_images[idx]
                    self.log(f"⏳ [{idx+1}p] 전체 OCR 처리 중...")
                    media = MediaFileUpload(img_p, mimetype='image/png')
                    file_id = service.files().create(body={'name': 'ocr_t', 'mimeType': 'application/vnd.google-apps.document'}, media_body=media, fields='id').execute().get('id')
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, service.files().export_media(fileId=file_id, mimeType='text/plain'))
                    done = False
                    while not done: _, done = downloader.next_chunk()
                    full_text += fh.getvalue().decode('utf-8').strip() + "\n"
                    service.files().delete(fileId=file_id).execute()

                qs = self.parse_answer_only(full_text) if u_in.get("mode") == "ans" else self.parse_text(full_text)
                result = self.review_and_edit_data(u_in["subject"], u_in["year"], u_in["type"], qs, temp_images, u_in["indices"])
                
                if result["confirm"]:
                    self.merge_quiz_data(u_in["subject"], u_in["year"], u_in["type"], result["data"])
                    self.log(f"✅ 모든 작업 완료 및 저장됨")
            except Exception as e: self.log(f"❌ 오류: {e}")
            finally: self.cleanup(temp_images)
        messagebox.showinfo("완료", "처리가 끝났습니다.")

    # --- 편집기 UI ---
    def review_and_edit_data(self, subject, year, test_type, quiz_list, image_paths, selected_indices):
        final = {"confirm": False, "data": quiz_list}
        win = Toplevel(self.root); win.title(f"편집: {subject}"); win.state('zoomed')
        
        self.img_list = [image_paths[i] for i in selected_indices]
        self.curr_idx = 0; self.zoom_scale = 0.6; self.temp_img_bytes = None; self.rect = None

        paned = tk.PanedWindow(win, orient=tk.HORIZONTAL, bg="#444"); paned.pack(fill="both", expand=True)
        
        # 왼쪽 뷰어
        l_f = tk.Frame(paned, bg="#333")
        tool = tk.Frame(l_f, bg="#222"); tool.pack(fill="x")
        Button(tool, text="◀ 이전", command=lambda: self.move_page(-1)).pack(side="left", padx=5)
        self.lbl_page = Label(tool, text="", bg="#222", fg="white"); self.lbl_page.pack(side="left", padx=10)
        Button(tool, text="다음 ▶", command=lambda: self.move_page(1)).pack(side="left", padx=5)
        self.canvas = Canvas(l_f, bg="#333", cursor="cross"); self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_crop_start); self.canvas.bind("<B1-Motion>", self.on_crop_move); self.canvas.bind("<ButtonRelease-1>", self.on_crop_end)
        self.canvas.bind("<MouseWheel>", self.on_zoom); self.canvas.bind("<ButtonPress-3>", self.on_drag_start); self.canvas.bind("<B3-Motion>", self.on_drag_move)
        paned.add(l_f)

        # 오른쪽 에디터
        r_f = tk.Frame(paned); paned.add(r_f)
        
        # 기능부 (이미지/정답)
        func1 = tk.Frame(r_f, bg="#f8f9fa", pady=5); func1.pack(fill="x")
        tk.Label(func1, text="대상 ID:").pack(side="left", padx=5)
        e_tid = tk.Entry(func1, width=5); e_tid.pack(side="left", padx=5)
        
        # 기능부 (공통지문 핵심!)
        func2 = tk.Frame(r_f, bg="#e9ecef", pady=5); func2.pack(fill="x")
        tk.Label(func2, text="공통지문(수정가능):").pack(side="top", anchor="w", padx=5)
        e_ctx = tk.Text(func2, height=4, width=50); e_ctx.pack(side="top", fill="x", padx=5, pady=2)
        
        range_frame = tk.Frame(func2, bg="#e9ecef")
        range_frame.pack(side="top", fill="x", padx=5)
        tk.Label(range_frame, text="적용 범위(예:1-5):").pack(side="left")
        e_rng = tk.Entry(range_frame, width=10); e_rng.pack(side="left", padx=5)

        # 텍스트 영역
        edit_frame = tk.Frame(r_f); edit_frame.pack(fill="both", expand=True)
        line_canvas = tk.Canvas(edit_frame, width=40, bg="#e0e0e0", highlightthickness=0); line_canvas.pack(side="left", fill="y")
        area = tk.Text(edit_frame, font=("Consolas", 10), undo=True, wrap="none"); area.pack(side="left", fill="both", expand=True)
        v_scroll = tk.Scrollbar(edit_frame, command=area.yview); v_scroll.pack(side="right", fill="y")
        area.config(yscrollcommand=v_scroll.set)
        area.insert(tk.END, json.dumps(quiz_list, ensure_ascii=False, indent=4))

        # 로컬 함수들
        def update_line_numbers(event=None):
            line_canvas.delete("all")
            i = area.index("@0,0")
            while True:
                dline = area.dlineinfo(i)
                if dline is None: break
                y = dline[1]; linenum = str(i).split(".")[0]
                line_canvas.create_text(35, y, anchor="ne", text=linenum, fill="#666", font=("Consolas", 10))
                i = area.index(f"{i}+1line")

        area.bind("<KeyRelease>", update_line_numbers); area.bind("<MouseWheel>", update_line_numbers); area.bind("<Configure>", update_line_numbers)

        def get_current_json():
            try: return json.loads(area.get(1.0, tk.END).strip())
            except Exception as e: messagebox.showerror("JSON 오류", str(e)); return None

        def update_area(data):
            area.delete(1.0, tk.END); area.insert(tk.END, json.dumps(data, ensure_ascii=False, indent=4))
            win.after(10, update_line_numbers)

        # 액션: OCR 텍스트 추출 (드래그 영역 -> 텍스트창)
        def action_extract_ocr():
            if not self.temp_img_bytes: return messagebox.showwarning("알림", "영역을 먼저 드래그하세요.")
            self.log("⏳ 지문 영역 OCR 추출 중...")
            text = self.ocr_image_bytes(self.temp_img_bytes)
            if text:
                e_ctx.delete(1.0, tk.END); e_ctx.insert(tk.END, text)
                self.log("✅ OCR 추출 완료. 내용을 확인하고 '적용'을 누르세요.")

        # 액션: 지문 적용 (텍스트창 -> JSON 데이터)
        def action_apply_to_json():
            ctx_text = e_ctx.get(1.0, tk.END).strip()
            rng_text = e_rng.get().strip()
            if not ctx_text or not rng_text: return messagebox.showwarning("알림", "지문 내용과 범위를 확인하세요.")
            try:
                start, end = map(int, rng_text.split('-'))
                target_ids = [str(i) for i in range(start, end + 1)]
                data = get_current_json()
                if not data: return
                for item in data:
                    if str(item.get('id')) in target_ids: item['context'] = ctx_text
                update_area(data)
                self.log(f"📝 {rng_text} 범위에 지문 적용 완료")
            except: messagebox.showerror("오류", "범위 형식 오류 (예: 1-5)")

        def action_capture_gh():
            tid = e_tid.get().strip()
            if not tid or not self.temp_img_bytes: return messagebox.showwarning("알림", "ID 입력 및 드래그 필수")
            url = self.upload_to_github(self.temp_img_bytes, subject, year, test_type, tid)
            if url:
                data = get_current_json()
                for item in data:
                    if str(item.get('id')) == tid: item['image_url'] = url; break
                update_area(data); self.log(f"✅ {tid}번 이미지 업로드 완료")

        # 버튼 배치
        Button(func1, text="📸 캡처&GH업로드", command=action_capture_gh, bg="#3498db", fg="white").pack(side="left", padx=5)
        
        # 지문 처리 버튼들
        Button(range_frame, text="1. 🔍 OCR 텍스트 추출", command=action_extract_ocr, bg="#f39c12", fg="white", font=("맑은 고딕", 9, "bold")).pack(side="left", padx=10)
        Button(range_frame, text="2. 💾 JSON 데이터에 적용", command=action_apply_to_json, bg="#e67e22", fg="white", font=("맑은 고딕", 9, "bold")).pack(side="left")

        def save_final():
            data = get_current_json()
            if data: final["data"] = data; final["confirm"] = True; win.destroy()

        Button(win, text="💾 최종 저장 (Firebase 동기화)", command=save_final, bg="#2ecc71", height=2, font=("맑은 고딕", 11, "bold")).pack(fill="x")
        
        win.after(100, update_line_numbers); self.update_viewer(); win.grab_set(); self.root.wait_window(win)
        return final

    # --- 유틸리티 (이전과 동일) ---
    def select_pages_and_info(self, image_paths):
        res = {"indices": [], "subject": "", "year": "2024", "type": "", "mode": "quiz", "cancel": True}
        dialog = Toplevel(self.root); dialog.title("정보 입력"); dialog.geometry("950x850")
        f_top = tk.Frame(dialog, pady=10); f_top.pack(fill="x")
        tk.Label(f_top, text="과목:").pack(side="left", padx=5)
        e_sub = tk.Entry(f_top, width=15); e_sub.pack(side="left", padx=5)
        tk.Label(f_top, text="연도:").pack(side="left", padx=5)
        e_yr = tk.Entry(f_top, width=8); e_yr.insert(0, "2024"); e_yr.pack(side="left", padx=5)
        cb = ttk.Combobox(f_top, values=["1학기 중간", "1학기 기말", "2학기 중간", "2학기 기말", "출석 대체", "하계 계절수업", "동계 계절수업"]); cb.set("1학기 기말"); cb.pack(side="left", padx=5)
        m_var = tk.StringVar(value="quiz")
        tk.Radiobutton(f_top, text="문제", variable=m_var, value="quiz").pack(side="left")
        tk.Radiobutton(f_top, text="정답", variable=m_var, value="ans").pack(side="left")
        def go():
            if not e_sub.get(): return messagebox.showwarning("누락", "과목명 입력 필수")
            res.update({"indices": [i for i, v in enumerate(vars) if v.get()], "subject": e_sub.get(), "year": e_yr.get(), "type": cb.get(), "mode": m_var.get(), "cancel": False})
            dialog.destroy()
        tk.Button(f_top, text="시작", command=go, bg="#28a745", fg="white", width=10).pack(side="right", padx=10)
        canvas = Canvas(dialog); scroll_f = tk.Frame(canvas); sb = Scrollbar(dialog, command=canvas.yview); canvas.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True); canvas.create_window((0,0), window=scroll_f, anchor="nw")
        scroll_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.thumbnail_photos = []; vars = []
        for i, p in enumerate(image_paths):
            f = tk.Frame(scroll_f, bd=1, relief="sunken"); f.grid(row=i//3, column=i%3, padx=5, pady=5)
            with Image.open(p) as raw:
                raw.thumbnail((200, 250)); photo = ImageTk.PhotoImage(raw)
                self.thumbnail_photos.append(photo); Label(f, image=photo).pack()
            v = tk.BooleanVar(value=True); tk.Checkbutton(f, text=f"{i+1}p", variable=v).pack(); vars.append(v)
        dialog.grab_set(); self.root.wait_window(dialog)
        return res

    def upload_to_github(self, img_bytes, subject, year, test_type, tid):
        safe_subject = re.sub(r'[\\/:*?"<>| ]', '_', subject)
        safe_type = re.sub(r'[\\/:*?"<>| ]', '_', test_type)
        full_path = f"Qbank/images/{safe_subject}_{year}_{safe_type}/{tid}.png"
        url = f"https://api.github.com/repos/{GH_REPO}/contents/{full_path}"
        headers = {"Authorization": f"token {GH_TOKEN}"}
        sha = None
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200: sha = res.json().get("sha")
        except: pass
        data = {"message": f"Upload {tid}", "content": base64.b64encode(img_bytes).decode("utf-8"), "branch": GH_BRANCH}
        if sha: data["sha"] = sha
        res = requests.put(url, headers=headers, json=data)
        return f"https://raw.githubusercontent.com/{GH_REPO}/{GH_BRANCH}/{full_path}" if res.status_code in [200, 201] else None

    def update_viewer(self):
        with Image.open(self.img_list[self.curr_idx]) as img:
            nw, nh = int(img.width * self.zoom_scale), int(img.height * self.zoom_scale)
            resized = img.resize((nw, nh), Image.LANCZOS); self.current_photo = ImageTk.PhotoImage(resized)
            self.canvas.delete("all"); self.canvas.create_image(0, 0, anchor="nw", image=self.current_photo)
            self.canvas.config(scrollregion=(0, 0, nw, nh))
            self.lbl_page.config(text=f"{self.curr_idx+1}/{len(self.img_list)} ({int(self.zoom_scale*100)}%)")

    def on_zoom(self, e):
        self.zoom_scale *= 1.1 if e.delta > 0 else 0.9
        self.zoom_scale = max(0.2, min(self.zoom_scale, 3.0)); self.update_viewer()
    def on_drag_start(self, e): self.canvas.scan_mark(e.x, e.y)
    def on_drag_move(self, e): self.canvas.scan_dragto(e.x, e.y, gain=1)
    def on_crop_start(self, e):
        self.start_x, self.start_y = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)
    def on_crop_move(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, self.canvas.canvasx(e.x), self.canvas.canvasy(e.y))
    def on_crop_end(self, e):
        ex, ey = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        x1, y1, x2, y2 = min(self.start_x, ex)/self.zoom_scale, min(self.start_y, ey)/self.zoom_scale, max(self.start_x, ex)/self.zoom_scale, max(self.start_y, ey)/self.zoom_scale
        with Image.open(self.img_list[self.curr_idx]) as img:
            buf = io.BytesIO(); img.crop((x1, y1, x2, y2)).save(buf, format="PNG"); self.temp_img_bytes = buf.getvalue()

    def move_page(self, d):
        if 0 <= self.curr_idx + d < len(self.img_list): self.curr_idx += d; self.update_viewer()

    def parse_text(self, t):
        res = []
        for c in re.split(r'\n\s*(?=\d{1,2}\.)', t):
            if not c.strip(): continue
            score_m = re.search(r"\((\d+\.?\d*)점\)", c)
            score = float(score_m.group(1)) if score_m else 0
            match = re.match(r'^(\d{1,2})\.\s*(.*)', c.strip(), re.DOTALL)
            if match:
                q_id, body = match.group(1), match.group(2)
                opts = re.findall(r'(?<=\s)[1-4]\s+([^\n1-4]+)', " " + body)
                res.append({"type":"quiz","id":q_id,"question":re.split(r'\s[1-4]\s', body)[0].strip(),"options":[o.strip() for o in opts[:4]],"answer":None,"score":score,"image_url":""})
        return res

    def parse_answer_only(self, text):
        found = re.findall(r'[1-4]', re.sub(r'\d+~\d+', '', text))
        return [{"id": str(i + 1), "answer": val} for i, val in enumerate(found)]

    def init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred, {'databaseURL': 'https://qbank-f4821-default-rtdb.asia-southeast1.firebasedatabase.app/'})
            self.log("📡 Firebase Admin SDK 초기화 성공")
        except Exception as e: self.log(f"❌ Firebase 초기화 실패: {e}")

    def merge_quiz_data(self, s, y, t, q):
        local_db = {}
        if os.path.exists('quiz_db.json'):
            with open('quiz_db.json', 'r', encoding='utf-8') as f:
                try: local_db = json.load(f)
                except: pass
        local_db.setdefault(s, {}).setdefault(y, {})[t] = q
        with open('quiz_db.json', 'w', encoding='utf-8') as f:
            json.dump(local_db, f, ensure_ascii=False, indent=4)
        try: 
            firebase_db.reference('quizzes').set(local_db)
            self.log("📡 Firebase 동기화 성공")
        except Exception as e: self.log(f"📡 Firebase 에러: {e}")

    def cleanup(self, l):
        self.current_photo = None; self.thumbnail_photos = []
        for p in l:
            try:
                if os.path.exists(p): os.remove(p)
            except: pass
        self.log("🧹 임시 파일 정리 완료")

if __name__ == "__main__":
    root = tk.Tk(); app = GoogleQuizExtractor(root); root.mainloop()
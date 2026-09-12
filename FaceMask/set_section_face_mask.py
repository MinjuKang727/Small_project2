import cv2
import numpy as np
import sys
import os
import glob
import random
import mediapipe as mp
from tqdm import tqdm

base_path = os.path.dirname(os.path.abspath(__file__))

# 1. 마스크 폴더 로드
mask_folder_path = r"C:\Users\KJY\Documents\Programming\FaceMask\mask"
mask_files = glob.glob(os.path.join(mask_folder_path, "*.*"))
mask_list = []
mask_filenames = []

for file_path in mask_files:
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            mask_list.append(img)
            mask_filenames.append(os.path.basename(file_path))

if not mask_list:
    print("Error: 폴더에 불러올 수 있는 이미지가 없습니다.")
    sys.exit(1)

# --- [핵심] 알파벳이 적힌 마스크 그리드 미리보기 이미지 생성 ---
thumb_size = 200
thumbs = []
alphabet_mapping = {}  # 알파벳 키 코드와 이미지 인덱스 매핑

for idx, img in enumerate(mask_list):
    if idx >= 26:
        break  # 최대 26개 (A~Z) 제한
    
    char_code = ord('A') + idx  # 'A'는 65
    char_str = chr(char_code)
    
    alphabet_mapping[char_code] = idx
    alphabet_mapping[char_code + 32] = idx  # 소문자(a~z)도 함께 매핑

    if img.shape[2] == 4:
        b, g, r, a = cv2.split(img)
        alpha = a / 255.0
        bg = np.ones_like(b, dtype=np.float32) * 255
        for c, channel in enumerate([b, g, r]):
            channel = channel * alpha + bg * (1 - alpha)
        thumb = cv2.merge([channel.astype(np.uint8) for channel in [b, g, r]])
    else:
        thumb = img.copy()

    thumb = cv2.resize(thumb, (thumb_size, thumb_size))
    
    # 이미지 위에 알파벳 박스 및 글씨 그리기 (노란색 글씨)
    cv2.rectangle(thumb, (5, 5), (55, 45), (0, 0, 0), -1)
    cv2.putText(thumb, char_str, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)
    
    thumbs.append(thumb)

cols = 4
rows = (len(thumbs) + cols - 1) // cols
while len(thumbs) < rows * cols:
    blank = np.ones((thumb_size, thumb_size, 3), dtype=np.uint8) * 255
    thumbs.append(blank)

row_images = []
for r in range(rows):
    row_img = np.hstack(thumbs[r * cols:(r + 1) * cols])
    row_images.append(row_img)

grid_img = np.vstack(row_images)
# -------------------------------------------------------------

# 2. 동영상 열기
video_path = r"C:\Users\KJY\Documents\Programming\FaceMask\video\20260818_212209.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps

print(f"\n[동영상 정보] 총 길이: {duration:.2f}초 (FPS: {fps})")
print("=" * 50)
print(" [조작법 안내]")
print(" • SPACEBAR : 재생 / 일시정지")
print(" • D 또는 → : 앞으로 1초 빨리감기")
print(" • A 또는 ← : 뒤로 1초 되감기")
print(" • S 키     : 현재 시간을 '시작 시간'으로 지정")
print(" • E 키     : 현재 시간을 '종료 시간'으로 지정 및 알파벳 선택창 띄우기")
print(" • ESC 키   : 구간 설정 완료 및 최종 렌더링 시작")
print("=" * 50)

print("동영상 프레임을 메모리에 로드하는 중...")
frames = []
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frames.append(frame)
cap.release()

window_name = "Video Timeline Editor"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 540, 960)

current_frame_idx = 0
is_playing = False
rules = []

temp_start_sec = None

while True:
    frame = frames[current_frame_idx].copy()
    current_sec = current_frame_idx / fps

    status_text = f"Time: {current_sec:.2f}s / {duration:.2f}s | Frame: {current_frame_idx}/{total_frames}"
    if temp_start_sec is not None:
        status_text += f" | [Start Set: {temp_start_sec:.2f}s]"
    
    cv2.putText(frame, status_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imshow(window_name, frame)

    wait_time = int(1000 / fps) if is_playing else 0
    key = cv2.waitKey(wait_time) & 0xFF

    if key == 27:  # ESC (구간 설정 완료)
        print("\n구간 설정이 완료되었습니다!")
        break
    elif key == ord(' '):  # SPACE
        is_playing = not is_playing
    elif key == ord('d') or key == 83:  # D / Right
        current_frame_idx = min(total_frames - 1, current_frame_idx + int(fps))
        is_playing = False
    elif key == ord('a') or key == 81:  # A / Left
        current_frame_idx = max(0, current_frame_idx - int(fps))
        is_playing = False
    elif key == ord('s') or key == ord('S'):  # S (시작 시간)
        temp_start_sec = round(current_sec, 2)
        print(f">> 시작 시간 설정됨: {temp_start_sec}초")
    elif key == ord('e') or key == ord('E'):  # E (종료 시간 및 알파벳 선택)
        if temp_start_sec is None:
            print(">> 경고: 먼저 'S'를 눌러 시작 시간을 설정해주세요!")
            continue
        
        temp_end_sec = round(current_sec, 2)
        if temp_end_sec <= temp_start_sec:
            print(">> 경고: 종료 시간은 시작 시간보다 뒤여야 합니다.")
            continue

        print(f"\n>> 구간 설정 완료: {temp_start_sec}초 ~ {temp_end_sec}초")
        print("-> 알파벳 미리보기 창이 떴습니다. 원하는 이미지의 알파벳 키(A, B, C...)를 누르세요!")

        # --- [핵심] 알파벳 선택 미리보기 창 띄우기 ---
        preview_window_name = "Select Mask by Alphabet (A, B, C...)"
        cv2.namedWindow(preview_window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(preview_window_name, grid_img)
        
        selected_img_idx = None
        while True:
            # 미리보기 창에서 키 입력 대기
            preview_key = cv2.waitKey(0)
            
            if preview_key in alphabet_mapping:
                selected_img_idx = alphabet_mapping[preview_key]
                char_chosen = chr(preview_key if preview_key < 97 else preview_key - 32).upper()
                print(f"-> '{char_chosen}' 키가 눌렸습니다! '{mask_filenames[selected_img_idx]}' 선택됨.")
                break
            elif preview_key == 27:  # 미리보기 창에서 ESC 누르면 취소
                print("-> 선택이 취소되었습니다.")
                break
            else:
                print("-> 올바른 마스크 알파벳 키(A, B, C...)를 눌러주세요!")

        # 선택이 끝나면 미리보기 창 닫기
        cv2.destroyWindow(preview_window_name)

        if selected_img_idx is not None:
            rules.append({
                "start": temp_start_sec,
                "end": temp_end_sec,
                "img_idx": selected_img_idx
            })
            print(f"-> 구간 규칙 추가 완료! ({temp_start_sec}s ~ {temp_end_sec}s -> {mask_filenames[selected_img_idx]})")
        
        temp_start_sec = None
        is_playing = False

cv2.destroyWindow(window_name)

if not rules:
    print("\n지정된 구간 규칙이 없습니다. 전체 영상을 랜덤 모드로 렌더링합니다.")
    use_default_random = True
else:
    use_default_random = False
    print(f"\n총 {len(rules)}개의 구간 규칙이 적용됩니다. 렌더링을 시작합니다...")

# 3. 최종 렌더링 시작
output_path = os.path.join(base_path, "output_video_custom.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

mp_face_detection = mp.solutions.face_detection

print("백그라운드에서 최종 영상을 합성 중입니다...")

with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
    with tqdm(total=total_frames, desc="Rendering", unit="frame") as pbar:
        for f_idx, frame in enumerate(frames):
            current_sec = f_idx / fps
            
            chosen_img = None
            if use_default_random:
                chosen_img = random.choice(mask_list)
            else:
                matched = False
                for rule in rules:
                    if rule["start"] <= current_sec <= rule["end"]:
                        chosen_img = mask_list[rule["img_idx"]]
                        matched = True
                        break
                if not matched:
                    chosen_img = random.choice(mask_list)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)

            if results.detections:
                for detection in results.detections:
                    box = detection.location_data.relative_bounding_box
                    x_rel, y_rel, w_rel, h_rel = box.xmin, box.ymin, box.width, box.height

                    scale_factor = 1.6 
                    new_w = w_rel * scale_factor
                    new_h = h_rel * scale_factor
                    new_x = x_rel - (new_w - w_rel) / 2
                    new_y = y_rel - (new_h - h_rel) * 0.7

                    x = int(new_x * width)
                    y = int(new_y * height)
                    w = int(new_w * width)
                    h = int(new_h * height)

                    x = max(0, x)
                    y = max(0, y)
                    if x + w > width: w = width - x
                    if y + h > height: h = height - y

                    if w <= 0 or h <= 0:
                        continue

                    try:
                        resized_overlay = cv2.resize(chosen_img, (w, h))
                    except cv2.error:
                        continue

                    if resized_overlay.shape[2] == 4:
                        overlay_rgb = resized_overlay[:, :, :3]
                        mask = resized_overlay[:, :, 3] / 255.0
                    else:
                        overlay_rgb = resized_overlay
                        mask = np.ones((h, w), dtype=np.float32)

                    roi = frame[y:y+h, x:x+w]
                    if roi.shape[0] == h and roi.shape[1] == w:
                        for c in range(3):
                            roi[:, :, c] = (1 - mask) * roi[:, :, c] + mask * overlay_rgb[:, :, c]
                        frame[y:y+h, x:x+w] = roi

            out.write(frame)
            pbar.update(1)

cap.release()
out.release()
print(f"\n모든 편집 및 렌더링 작업이 완료되었습니다! 저장된 파일: {output_path}")
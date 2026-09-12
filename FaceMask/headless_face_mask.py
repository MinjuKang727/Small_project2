# 다중 얼굴 인식 및 이미지로 모자이크
import cv2
import numpy as np
import sys
import os
import glob
import random
import mediapipe as mp
from tqdm import tqdm

base_path = os.path.dirname(os.path.abspath(__file__))
# 파일 경로 설정
video_filename = "20260901_211509"
video_path = os.path.join(base_path, "video", f"{video_filename}.mp4")

# 저장 경로 자동 생성 (원본과 같은 폴더에 저장)
output_path = os.path.join(base_path, "save", f"{video_filename}_headless.mp4")

# 1. 마스크 폴더 로드 (미리보기 창 없이 텍스트로만 리스트 출력)
mask_folder_path = os.path.join(base_path, "mask")
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
    print("Error: 폴더에 불러올 수 있는 이미지가 없습니다.", base_path, video_path, output_path, mask_folder_path)
    sys.exit(1)

# --- 2. 이미지들을 하나로 합쳐서 알파벳과 함께 한눈에 미리보기 만들기 ---
print("\n모든 마스크 이미지를 하나의 창에 미리 띄웁니다...")

thumb_size = 200
thumbs = []
alphabet_mapping = {}  # 알파벳 키와 이미지 인덱스를 연결할 딕셔너리

for idx, img in enumerate(mask_list):
    # 사용할 수 있는 알파벳 순서대로 할당 (A, B, C, D ... Z, 최대 26개)
    if idx >= 26:
        break  # 이미지가 26개를 넘어가면 일단 제한
    
    char_code = ord('A') + idx  # 대문자 ASCII 코드 시작 ('A'는 65)
    char_str = chr(char_code)   # 'A', 'B', 'C' ...
    
    # 키 코드와 이미지 인덱스 매핑 저장 (대문자와 소문자 둘 다 등록)
    alphabet_mapping[char_code] = idx
    alphabet_mapping[char_code + 32] = idx  # 소문자(a, b, c...)도 함께 매핑

    # 알파 채널 제거하고 BGR로 변환 (미리보기용)
    if img.shape[2] == 4:
        b, g, r, a = cv2.split(img)
        alpha = a / 255.0
        bg = np.ones_like(b, dtype=np.float32) * 255
        for c, channel in enumerate([b, g, r]):
            channel = channel * alpha + bg * (1 - alpha)
        thumb = cv2.merge([channel.astype(np.uint8) for channel in [b, g, r]])
    else:
        thumb = img.copy()

    # 크기 조절
    thumb = cv2.resize(thumb, (thumb_size, thumb_size))
    
    # --- [수정] 이미지 위에 번호 대신 알파벳 박스 그리기 ---
    cv2.rectangle(thumb, (5, 5), (55, 45), (0, 0, 0), -1)
    cv2.putText(thumb, char_str, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA) # 노란색 글씨
    
    thumbs.append(thumb)

# 행/열 배치 및 그리드 생성 (이전과 동일)
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

# 미리보기 창 띄우기
preview_window = "All Masks Preview (Press A, B, C... to select)"
cv2.namedWindow(preview_window, cv2.WINDOW_NORMAL)
cv2.imshow(preview_window, grid_img)

print("미리보기 창에서 이미지를 확인하고, 원하는 이미지의 알파벳 키(A, B, C...)를 누르세요! (랜덤 선택:ESC)")

# --- 3. 알파벳 키 입력 대기 및 즉시 선택 ---
overlay_img = None
mode_choice = "1"  # 기본은 랜덤으로 설정해두고 올바른 키가 눌리면 2번으로 변경

while True:
    key_code = cv2.waitKey(0)  # 키 입력 대기
    
    # 사용자가 누른 키가 우리가 매핑해둔 알파벳(A~Z)에 포함되는지 확인
    if key_code in alphabet_mapping:
        img_idx = alphabet_mapping[key_code]
        overlay_img = mask_list[img_idx]
        chosen_filename = mask_filenames[img_idx]
        char_chosen = chr(key_code if key_code < 97 else key_code - 32).upper()
        
        print(f"'{char_chosen}' 키를 눌렀습니다! '{chosen_filename}' 이미지로 지정되었습니다.")
        mode_choice = "2"
        break
    elif key_code == 27:  # ESC를 누르면 랜덤 모드로 탈출
        print("ESC가 눌렸습니다. 랜덤 모드로 진행합니다.")
        mode_choice = "1"
        break
    else:
        print("올바른 마스크 알파벳 키를 눌러주세요! (예: A, B, C...)")

cv2.destroyWindow(preview_window)

# 2. 동영상 준비
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) # 전체 프레임 수

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

mp_face_detection = mp.solutions.face_detection

print("\n백그라운드에서 동영상 처리를 시작합니다 (화면 출력 없음)...")

frame_count = 0
with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
    with tqdm(total=total_frames, desc="Processing Video", unit="frame") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)

            h_frame, w_frame, _ = frame.shape

            if results.detections:
                for i, detection in enumerate(results.detections):
                    box = detection.location_data.relative_bounding_box
                    x_rel, y_rel, w_rel, h_rel = box.xmin, box.ymin, box.width, box.height

                    # 얼굴 전체 덮기 스케일 조정
                    scale_factor = 1.6 
                    new_w = w_rel * scale_factor
                    new_h = h_rel * scale_factor
                    new_x = x_rel - (new_w - w_rel) / 2
                    new_y = y_rel - (new_h - h_rel) * 0.7

                    x = int(new_x * w_frame)
                    y = int(new_y * h_frame)
                    w = int(new_w * w_frame)
                    h = int(new_h * h_frame)

                    x = max(0, x)
                    y = max(0, y)
                    if x + w > w_frame: w = w_frame - x
                    if y + h > h_frame: h = h_frame - y

                    if w <= 0 or h <= 0:
                        continue

                    try:
                        resized_overlay = cv2.resize(overlay_img, (w, h))
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

            # 화면에 띄우는 cv2.imshow 생략하고 바로 저장!
            out.write(frame)
            pbar.update(1)

cap.release()
out.release()

print(f"\n모든 작업이 완료되었습니다! 저장된 파일: {output_path}")
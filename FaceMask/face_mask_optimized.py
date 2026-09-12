# 이미지 크기 조절이 너무 자주되면 화면 보기가 불편한 점을 개선한 코드

import cv2
import numpy as np
import sys
import os
import glob
import random
import mediapipe as mp
from tqdm import tqdm

base_path = os.path.dirname(os.path.abspath(__file__))

video_path = r"C:\Users\KJY\Documents\Programming\FaceMask\video\20260808_113918.mp4"
output_path = os.path.join(base_path, "20260808_113918_optimized.mp4") # 결과물이 덮어씌워지지 않게 이름 변경

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

# --- 2. 이미지 미리보기 및 선택 ---
print("\n모든 마스크 이미지를 하나의 창에 미리 띄웁니다...")

thumb_size = 200
thumbs = []
alphabet_mapping = {} 

for idx, img in enumerate(mask_list):
    if idx >= 26:
        break 
    
    char_code = ord('A') + idx 
    char_str = chr(char_code) 
    
    alphabet_mapping[char_code] = idx
    alphabet_mapping[char_code + 32] = idx 

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

preview_window = "All Masks Preview (Press A, B, C... to select)"
cv2.namedWindow(preview_window, cv2.WINDOW_NORMAL)
cv2.imshow(preview_window, grid_img)

print("미리보기 창에서 이미지를 확인하고, 원하는 이미지의 알파벳 키를 누르세요! (랜덤 선택:ESC)")

overlay_img = None
while True:
    key_code = cv2.waitKey(0) 
    if key_code in alphabet_mapping:
        img_idx = alphabet_mapping[key_code]
        overlay_img = mask_list[img_idx]
        chosen_filename = mask_filenames[img_idx]
        char_chosen = chr(key_code if key_code < 97 else key_code - 32).upper()
        print(f"'{char_chosen}' 키를 눌렀습니다! '{chosen_filename}' 이미지로 지정되었습니다.")
        break
    elif key_code == 27: 
        print("ESC가 눌렸습니다. 첫 번째 이미지를 기본으로 진행합니다.")
        overlay_img = mask_list[0]
        break
    else:
        print("올바른 마스크 알파벳 키를 눌러주세요! (예: A, B, C...)")

cv2.destroyWindow(preview_window)

# 3. 동영상 준비
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

mp_face_detection = mp.solutions.face_detection

print("\n백그라운드에서 동영상 처리를 시작합니다 (크기 변화 안정화 적용)...")

# --- [추가] 얼굴 떨림 방지를 위한 이전 프레임 정보 기억용 딕셔너리 ---
# 다중 인식을 대비해 얼굴 인덱스별로 이전 크기/위치를 저장합니다.
prev_boxes = {}

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
                current_frame_boxes = {}
                
                for i, detection in enumerate(results.detections):
                    box = detection.location_data.relative_bounding_box
                    x_rel, y_rel, w_rel, h_rel = box.xmin, box.ymin, box.width, box.height

                    scale_factor = 1.6 
                    new_w = w_rel * scale_factor
                    new_h = h_rel * scale_factor
                    new_x = x_rel - (new_w - w_rel) / 2
                    new_y = y_rel - (new_h - h_rel) * 0.7

                    x = int(new_x * w_frame)
                    y = int(new_y * h_frame)
                    w = int(new_w * w_frame)
                    h = int(new_h * h_frame)

                    # --- [핵심 수정] 미세한 크기/위치 변화 무시 (스무딩 및 임계값 적용) ---
                    # 만약 이전 프레임에 기록된 얼굴 정보가 있다면 비교합니다.
                    if i in prev_boxes:
                        prev_x, prev_y, prev_w, prev_h = prev_boxes[i]
                        
                        # 변화량(픽셀 차이) 계산
                        diff_w = abs(w - prev_w)
                        diff_h = abs(h - prev_h)
                        
                        # 변화가 15픽셀 미만이라면, 이전 크기와 위치를 그대로 사용하여 떨림 방지
                        threshold = 15 
                        if diff_w < threshold and diff_h < threshold:
                            x, y, w, h = prev_x, prev_y, prev_w, prev_h
                        else:
                            # 변화가 크더라도 부드럽게(Lerp 방식) 반영하려면 아래와 같이 가중치를 줄 수도 있습니다.
                            # 여기서는 급격한 튀는 현상을 막기 위해 0.6 비율로 서서히 변하게 조정합니다.
                            w = int(prev_w * 0.4 + w * 0.6)
                            h = int(prev_h * 0.4 + h * 0.6)
                            x = int(prev_x * 0.4 + x * 0.6)
                            y = int(prev_y * 0.4 + y * 0.6)

                    # 현재 프레임의 최종 좌표를 저장해 둡니다.
                    current_frame_boxes[i] = (x, y, w, h)

                    # 화면 밖 보정
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
                
                # 다음 프레임을 위해 현재 위치 저장
                prev_boxes = current_frame_boxes
            else:
                # 얼굴이 감지되지 않으면 이전 박스 기록 초기화
                prev_boxes = {}

            out.write(frame)
            pbar.update(1)

cap.release()
out.release()

print(f"\n안정화 작업이 완료되었습니다! 저장된 파일: {output_path}")
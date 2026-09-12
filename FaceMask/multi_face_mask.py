# 얼굴 다중 인식 및 서로 다른 이미지로 모자이크 프로그램
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

for file_path in mask_files:
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            mask_list.append(img)

if not mask_list:
    print("Error: 폴더에 불러올 수 있는 이미지가 없습니다.")
    sys.exit(1)

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
print("구간 설정 없이 전체 영상에 대해 다중 얼굴 인식 및 중복 없는 랜덤 마스킹을 시작합니다...")

print("동영상 프레임을 메모리에 로드하는 중...")
frames = []
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frames.append(frame)
cap.release()

# 3. 최종 렌더링 시작 (프레임별로 얼굴마다 중복 없는 랜덤 이미지 매칭)
output_path = os.path.join(base_path, "output_video_random_unique.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

mp_face_detection = mp.solutions.face_detection

with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
    with tqdm(total=total_frames, desc="Rendering", unit="frame") as pbar:
        for f_idx, frame in enumerate(frames):
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)

            if results.detections:
                num_faces = len(results.detections)
                
                # 얼굴 수만큼 마스크 리스트에서 중복 없이 랜덤 선택
                # (만약 보유한 마스크 수보다 감지된 얼굴 수가 더 많다면, 부족한 만큼은 리스트 안에서 다시 허용)
                if num_faces <= len(mask_list):
                    chosen_masks = random.sample(mask_list, num_faces)
                else:
                    chosen_masks = random.choices(mask_list, k=num_faces)

                for i, detection in enumerate(results.detections):
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

                    chosen_img = chosen_masks[i]

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

out.release()
print(f"\n모든 작업이 완료되었습니다! 저장된 파일: {output_path}")
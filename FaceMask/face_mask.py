#다중 얼굴 인식 + 얼굴 전체 마스크

import cv2
import numpy as np
import sys
import os
import glob
import mediapipe as mp
import random # (선택사항) 얼굴마다 랜덤 이미지를 위해 필요

# 현재 파일이 있는 폴더 경로
base_path = os.path.dirname(os.path.abspath(__file__))
video_path = r"C:\Users\KJY\Documents\Programming\FaceMask\video\20260818_212209.mp4"
# 1. 마스크 이미지가 들어있는 폴더 경로
mask_folder_path = r"C:\Users\KJY\Documents\Programming\FaceMask\mask"

# 폴더 안의 이미지 파일들을 리스트로 관리
mask_files = glob.glob(os.path.join(mask_folder_path, "*.*"))
mask_list = []
mask_filenames = []

print(f"폴더에서 마스크 이미지를 찾는 중: {mask_folder_path}")

for file_path in mask_files:
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            mask_list.append(img)
            mask_filenames.append(os.path.basename(file_path))
            print(f"로드 성공: {os.path.basename(file_path)}")

if not mask_list:
    print("Error: 폴더에 불러올 수 있는 이미지가 없습니다.")
    sys.exit(1)

# # --- 2. 이미지들을 하나로 합쳐서 번호와 함께 한눈에 미리보기 만들기 ---
# print("\n모든 마스크 이미지를 하나의 창에 미리 띄웁니다...")

# # 미리보기용 이미지 크기 통일 (예: 200x200 픽셀)
# thumb_size = 200
# thumbs = []

# for idx, img in enumerate(mask_list):
#     # 알파 채널 제거하고 BGR로 변환 (미리보기용)
#     if img.shape[2] == 4:
#         # 투명 배경을 흰색으로 채우기
#         b, g, r, a = cv2.split(img)
#         alpha = a / 255.0
#         bg = np.ones_like(b, dtype=np.float32) * 255
#         for c, channel in enumerate([b, g, r]):
#             channel = channel * alpha + bg * (1 - alpha)
#         thumb = cv2.merge([channel.astype(np.uint8) for channel in [b, g, r]])
#     else:
#         thumb = img.copy()

#     # 크기 조절
#     thumb = cv2.resize(thumb, (thumb_size, thumb_size))
    
#     # 이미지 위에 번호 적기 (검은색 배경 박스 + 흰색 글씨)
#     cv2.rectangle(thumb, (5, 5), (55, 45), (0, 0, 0), -1)
#     cv2.putText(thumb, str(idx + 1), (12, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    
#     thumbs.append(thumb)

# # 한 행에 최대 4개씩 배치하여 큰 격자(Grid) 이미지 만들기
# cols = 4
# rows = (len(thumbs) + cols - 1) // cols

# # 빈 자리는 흰색 이미지로 채우기
# while len(thumbs) < rows * cols:
#     blank = np.ones((thumb_size, thumb_size, 3), dtype=np.uint8) * 255
#     thumbs.append(blank)

# # 행 단위로 합치기
# row_images = []
# for r in range(rows):
#     row_img = np.hstack(thumbs[r * cols:(r + 1) * cols])
#     row_images.append(row_img)

# # 최종 전체 미리보기 판 완성
# grid_img = np.vstack(row_images)

# # 미리보기 창 띄우기
# preview_window = "All Masks Preview (Press any key to continue)"
# cv2.namedWindow(preview_window, cv2.WINDOW_NORMAL)
# cv2.imshow(preview_window, grid_img)
# print("미리보기 창에서 번호를 확인하세요! 키보드 아무 키나 누르면 다음 단계로 넘어갑니다.")
# cv2.waitKey(0)
# cv2.destroyWindow(preview_window)

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


# # --- 3. 모드 선택 (랜덤 vs 특정 번호 지정) ---
# print("\n--- 마스크 적용 방식 선택 ---")
# print("1. 랜덤 모드 (폴더 내 이미지를 랜덤으로 적용)")
# print("2. 특정 이미지 지정 모드 (위 미리보기에서 본 번호 입력)")

# mode_choice = input("원하는 방식의 번호를 입력하세요 (기본값: 1번 랜덤): ").strip()
# overlay_img = None

# if mode_choice == "2":
#     try:
#         img_idx_input = input(f"사용할 이미지의 번호를 입력하세요 (1 ~ {len(mask_list)}): ").strip()
#         img_idx = int(img_idx_input) - 1
        
#         if 0 <= img_idx < len(mask_list):
#             overlay_img = mask_list[img_idx]
#             print(f"'{mask_filenames[img_idx]}' (번호: {img_idx + 1}) 이미지로 고정되었습니다.")
#         else:
#             print("잘못된 번호입니다. 기본 랜덤 모드로 전환합니다.")
#             mode_choice = "1"
#     except ValueError:
#         print("잘못된 입력입니다. 기본 랜덤 모드로 전환합니다.")
#         mode_choice = "1"
# else:
#     overlay_img = random.choice(mask_list)
#     print("랜덤 모드로 설정되었습니다.")

# 동영상 파일 열기
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

# 동영상 저장 설정
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

output_path = os.path.join(base_path, "output_video_special.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# MediaPipe 초기화
mp_face_detection = mp.solutions.face_detection

# 창 크기 조절 설정
PORTRAIT_SIZE = (540, 960)   # 세로 모드 (가로, 세로)
LANDSCAPE_SIZE = (960, 540)  # 가로 모드 (가로, 세로)

print(f"원본 동영상 해상도 -> 가로: {width}, 세로: {height}")
print("--- 재생 창 모드 선택 ---")
print("1. 세로 모드 (540 x 960)")
print("2. 가로 모드 (960 x 540)")

choice = input("원하는 모드 번호를 입력하세요 (기본값: 1번 세로 모드): ").strip()

if choice == "2":
    window_width, window_height = LANDSCAPE_SIZE
    print("가로 모드로 설정되었습니다.")
else:
    window_width, window_height = PORTRAIT_SIZE
    print("세로 모드로 설정되었습니다.")

# 창 생성 및 적용
window_name = "Multi-Face Overlay"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, window_width, window_height)

print("다중 얼굴 마스킹 처리를 시작합니다...")

# model_selection=1: 근거리(2m 이내), 0: 원거리(5m 이내)
with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        h_frame, w_frame, _ = frame.shape

        if results.detections:
            # --- [수정] 감지된 얼굴 각각에 대해 처리 ---
            for i, detection in enumerate(results.detections):
                box = detection.location_data.relative_bounding_box
                
                # 기본 얼굴 박스 위치 (정규화된 좌표)
                x_rel = box.xmin
                y_rel = box.ymin
                w_rel = box.width
                h_rel = box.height

                # --- [핵심 수정] 얼굴 전체를 덮기 위한 크기 및 위치 조정 ---
                # 배율 설정 (1.0 = 얼굴 크기 딱 맞음, 1.6 = 얼굴보다 1.6배 크게)
                scale_factor = 1.6 
                
                # 확대된 새로운 너비/높이
                new_w = w_rel * scale_factor
                new_h = h_rel * scale_factor

                # 확대된 만큼 중심점을 기준으로 위치 이동 (얼굴 위쪽 이마까지 덮기 위해 y를 더 많이 이동)
                new_x = x_rel - (new_w - w_rel) / 2
                new_y = y_rel - (new_h - h_rel) * 0.7  # 위쪽으로 더 많이 이동

                # 최종 픽셀 좌표 계산
                x = int(new_x * w_frame)
                y = int(new_y * h_frame)
                w = int(new_w * w_frame)
                h = int(new_h * h_frame)

                # 화면 밖으로 나간 부분 보정
                x = max(0, x)
                y = max(0, y)
                if x + w > w_frame: w = w_frame - x
                if y + h > h_frame: h = h_frame - y

                if w <= 0 or h <= 0:
                    continue

                # 마스크 크기 조정
                try:
                    resized_overlay = cv2.resize(overlay_img, (w, h))
                except cv2.error:
                    continue # 크기 조정 실패 시 건너뜀

                # 알파 채널 합성 (기존과 동일)
                if resized_overlay.shape[2] == 4:
                    overlay_rgb = resized_overlay[:, :, :3]
                    mask = resized_overlay[:, :, 3] / 255.0
                else:
                    overlay_rgb = resized_overlay
                    mask = np.ones((h, w), dtype=np.float32)

                # 이미지 합성 (기존과 동일)
                roi = frame[y:y+h, x:x+w]
                if roi.shape[0] == h and roi.shape[1] == w:
                    for c in range(3):
                        roi[:, :, c] = (1 - mask) * roi[:, :, c] + mask * overlay_rgb[:, :, c]
                    frame[y:y+h, x:x+w] = roi

        out.write(frame)
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC 누르면 종료
            break

cap.release()
out.release()
cv2.destroyAllWindows()

print(f"작업 완료! 저장된 파일 경로: {output_path}")
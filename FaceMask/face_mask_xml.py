# haarcascade.xml 연습 코드

import cv2
import numpy as np
import sys
import os

# 현재 파일(face_mask.py)이 있는 폴더를 기준으로 절대 경로를 생성
base_path = os.path.dirname(os.path.abspath(__file__))
cascPath = os.path.join(base_path, "haarcascade_xml", "haarcascade_frontalface_default.xml")

# 확실한 절대 경로로 불러오기
face_cascade = cv2.CascadeClassifier(cascPath)

# 확인용 (잘 불러왔는지 체크)
if face_cascade.empty():
    print("에러: XML 파일을 불러올 수 없습니다. 경로를 확인하세요.")
    print("현재 시도한 경로:", cascPath)
    sys.exit(1)
else:
    print("성공: XML 파일 로드 완료!")

# 덮어씌울 이미지 로드 (예: PNG, 투명 배경 가능)
overlay_path = "C:/Users/KJY/Documents/Programming/FaceMask/mask/free-icon-happy-2171990.png"
if not os.path.exists(overlay_path):
    print(f"Error: '{overlay_path}' 파일이 없습니다.")
    sys.exit(1)

overlay_img = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)  # 알파 채널 포함

# 동영상 파일 또는 웹캠 열기
video_path = "C:/Users/KJY/Documents/Programming/FaceMask/video/20260818_212209.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

# --- [추가] 동영상 저장을 위한 설정 ---
fps = cap.get(cv2.CAP_PROP_FPS)                      # 원본 동영상의 초당 프레임 수(FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))         # 동영상 가로 크기
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))       # 동영상 세로 크기

output_path = os.path.join(base_path, "output_video.mp4") # 저장될 파일 이름
fourcc = cv2.VideoWriter_fourcc(*'mp4v')             # 코덱 설정 (mp4 형식)
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
# ----------------------------------------

print("동영상 처리 및 저장을 시작합니다...")

while True:
    ret, frame = cap.read()
    if not ret:
        break  # 동영상 끝

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 얼굴 탐지
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(50, 50))

    for (x, y, w, h) in faces:
        # 덮어씌울 이미지 크기 조정
        resized_overlay = cv2.resize(overlay_img, (w, h))

        # 알파 채널 분리
        if resized_overlay.shape[2] == 4:
            overlay_rgb = resized_overlay[:, :, :3]
            mask = resized_overlay[:, :, 3] / 255.0
        else:
            overlay_rgb = resized_overlay
            mask = np.ones((h, w), dtype=np.float32)

        # 얼굴 위치에 이미지 합성
        roi = frame[y:y+h, x:x+w]
        if roi.shape[0] == h and roi.shape[1] == w:
            for c in range(3):
                roi[:, :, c] = (1 - mask) * roi[:, :, c] + mask * overlay_rgb[:, :, c]

            frame[y:y+h, x:x+w] = roi

    # --- [추가] 합성된 프레임을 결과 파일에 기록 ---
    out.write(frame)

    cv2.imshow("Face Overlay", frame)

    # ESC 키 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

# 자원 해제 및 마무리
cap.release()
out.release()  # 중요: VideoWriter도 꼭 닫아주어야 파일이 정상 저장됩니다!
cv2.destroyAllWindows()

print(f"작업 완료! 저장된 파일 경로: {output_path}")
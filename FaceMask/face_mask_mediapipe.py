# 화면에 영상을 띄워 얼굴 인식 및 이미지로 모자이크 프로그램
import cv2
import numpy as np
import sys
import os
import mediapipe as mp

# 현재 파일이 있는 폴더 경로
base_path = os.path.dirname(os.path.abspath(__file__))

# 1. 덮어씌울 이미지(마스크) 로드
overlay_path = "C:/Users/KJY/Documents/Programming/FaceMask/mask/free-icon-happy-2171990.png"
if not os.path.exists(overlay_path):
    print(f"Error: '{overlay_path}' 파일이 없습니다.")
    sys.exit(1)

overlay_img = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)  # 알파 채널 포함

# 2. 동영상 파일 또는 웹캠 열기
video_path = os.path.join(base_path, "video", "20260818_212209.mp4")
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

# 동영상 저장을 위한 설정
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

output_path = os.path.join(base_path, "output_video_mediapipe.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# 3. MediaPipe 얼굴 감지기 초기화
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

print("MediaPipe로 동영상 처리 및 저장을 시작합니다...")

# min_detection_confidence: 얼굴 감지 신뢰도 (0.0 ~ 1.0, 높을수록 엄격)
with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # MediaPipe는 RGB 이미지를 사용하므로 변환
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        h_frame, w_frame, _ = frame.shape

        if results.detections:
            for detection in results.detections:
                # MediaPipe가 계산한 얼굴 bounding box 위치 가져오기 (비율 값으로 나옴)
                box = detection.location_data.relative_bounding_box
                
                # 픽셀 단위 좌표로 변환
                x = int(box.xmin * w_frame)
                y = int(box.ymin * h_frame)
                w = int(box.width * w_frame)
                h = int(box.height * h_frame)

                # 화면 밖으로 좌표가 나가는 것 방지
                x = max(0, x)
                y = max(0, y)
                if x + w > w_frame: w = w_frame - x
                if y + h > h_frame: h = h_frame - y

                if w <= 0 or h <= 0:
                    continue

                # 마스크 크기 조정 (마스크가 얼굴보다 작거나 크면 비율을 조절할 수도 있습니다)
                resized_overlay = cv2.resize(overlay_img, (w, h))

                # 알파 채널(투명도) 분리
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

        # 결과 프레임 저장 및 화면 출력
        out.write(frame)
        cv2.imshow("MediaPipe Face Overlay", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC 키로 종료
            break

cap.release()
out.release()
cv2.destroyAllWindows()

print(f"작업 완료! 저장된 파일 경로: {output_path}")
# 얼굴 인식 위치 및 타임 기록 프로그램

import cv2
import os
import sys
import mediapipe as mp
import json

base_path = os.path.dirname(os.path.abspath(__file__))
video_path = r"C:\Users\KJY\Documents\Programming\FaceMask\video\20260818_212209.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

mp_face_detection = mp.solutions.face_detection

face_timeline = [] # 시간대별 얼굴 정보를 담을 리스트
frame_idx = 0

print("동영상에서 시간대별 얼굴 위치를 분석 중입니다...")

with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time_sec = frame_idx / fps # 현재 시간(초) 계산
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        frame_faces = []
        if results.detections:
            for detection in results.detections:
                box = detection.location_data.relative_bounding_box
                x_rel, y_rel, w_rel, h_rel = box.xmin, box.ymin, box.width, box.height

                # 얼굴 전체 덮기 스케일 조정 (이전에 쓰던 방식 그대로 적용)
                scale_factor = 1.6 
                new_w = w_rel * scale_factor
                new_h = h_rel * scale_factor
                new_x = x_rel - (new_w - w_rel) / 2
                new_y = y_rel - (new_h - h_rel) * 0.7

                x = int(new_x * width)
                y = int(new_y * height)
                w = int(new_w * width)
                h = int(new_h * height)

                # 발견된 얼굴의 계산된 절대 픽셀 좌표 저장
                frame_faces.append({"x": x, "y": y, "w": w, "h": h})

        # 해당 프레임에 얼굴이 있었다면 타임라인에 기록
        if frame_faces:
            face_timeline.append({
                "frame": frame_idx,
                "time_sec": round(current_time_sec, 2),
                "faces": frame_faces
            })

        frame_idx += 1

cap.release()

# 결과를 JSON 파일로 저장해두면 나중에 언제든 불러와서 쓸 수 있습니다!
json_output_path = os.path.join(base_path, "face_timeline.json")
with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(face_timeline, f, indent=4, ensure_ascii=False)

print(f"분석 완료! 총 {len(face_timeline)}개의 프레임에서 얼굴이 감지되었습니다.")
print(f"위치 데이터 저장 파일: {json_output_path}")
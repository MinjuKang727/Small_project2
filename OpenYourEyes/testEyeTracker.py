import cv2
import numpy as np
import time

try:
    from mediapipe.python.solutions import face_mesh as mp_face_mesh
    print("✅ 통합 감지 모드 로드 성공!")
except ImportError:
    import mediapipe.solutions.face_mesh as mp_face_mesh

# --- 설정값 ---
EAR_THRESHOLD = 0.20       # 눈 감김 기준
PITCH_THRESHOLD = 15.0     # 고개 숙임 기준 (각도가 클수록 많이 숙인 것)
CLOSED_FRAMES_LIMIT = 25   # 연속 감지 프레임 (30fps 기준 약 0.8초)

# 눈 및 얼굴 중심 좌표 인덱스
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
FACE_OVAL = [10, 152, 234, 454] # 이마, 턱, 왼쪽 끝, 오른쪽 끝

def get_ear(landmarks, eye_indices, w, h):
    pts = [np.array([landmarks[i].x * w, landmarks[i].y * h]) for i in eye_indices]
    v1 = np.linalg.norm(pts[1] - pts[5])
    v2 = np.linalg.norm(pts[2] - pts[4])
    h_dist = np.linalg.norm(pts[0] - pts[3])
    return (v1 + v2) / (2.0 * h_dist)

# 간단한 Pitch(상하 각도) 계산 함수
def get_head_pitch(landmarks, w, h):
    top = landmarks[10].y * h    # 이마 끝
    bottom = landmarks[152].y * h # 턱 끝
    nose = landmarks[1].y * h     # 코 끝
    
    # 얼굴 전체 길이 대비 코의 위치 비율로 각도 추정
    face_height = bottom - top
    relative_nose_pos = (nose - top) / face_height
    
    # 평상시 정면을 볼 때 비율(약 0.5~0.6)을 기준으로 차이 계산
    # 수치가 커질수록 고개가 아래로 숙여진 상태
    pitch_score = (relative_nose_pos - 0.55) * 100 
    return pitch_score

face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
cap = cv2.VideoCapture(0)
drowsy_counter = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)

    if res.multi_face_landmarks:
        for lm in res.multi_face_landmarks:
            ear = (get_ear(lm.landmark, LEFT_EYE, w, h) + get_ear(lm.landmark, RIGHT_EYE, w, h)) / 2.0
            pitch = get_head_pitch(lm.landmark, w, h)

            # --- 졸음 판정 로직 ---
            # 눈을 감았거나(EAR 낮음) 고개를 숙였을 때(Pitch 높음) 카운트 증가
            if ear < EAR_THRESHOLD or pitch > PITCH_THRESHOLD:
                drowsy_counter += 1
            else:
                drowsy_counter = 0

            # 경고 출력
            status_color = (0, 255, 0)
            if drowsy_counter >= CLOSED_FRAMES_LIMIT:
                status_color = (0, 0, 255)
                cv2.putText(frame, "!!! WAKE UP !!!", (w//4, h//2), cv2.FONT_HERSHEY_DUPLEX, 2, status_color, 3)

            # 데이터 화면 표시
            cv2.putText(frame, f"EAR: {ear:.2f} | Pitch: {pitch:.1f}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    cv2.imshow('Drowsiness Detection (Eye + Head)', frame)
    if cv2.waitKey(1) & 0xFF == 49: break # 1번 종료

cap.release()
cv2.destroyAllWindows()
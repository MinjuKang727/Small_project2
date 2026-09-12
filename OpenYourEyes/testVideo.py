import cv2
import os

# 저장 폴더 생성 (폴더가 없으면 에러 방지)
output_dir = './image/'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라를 찾을 수 없습니다.")
    exit()

fps = 30.0
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
codec = cv2.VideoWriter_fourcc(*'XVID') # avi 표준 코덱
out = cv2.VideoWriter(os.path.join(output_dir, 'cctv01.avi'), codec, fps, (w, h))

record = False

print("프로그램 작동 중... [2]: 녹화 시작, [1]: 종료")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 화면 표시 (이게 .py 파일에서의 'display' 역할을 합니다)
    cv2.imshow('Eye Tracking Monitor', frame)

    if record:
        # 화면에 녹화 중임을 표시 (빨간 점)
        cv2.circle(frame, (10, 10), 10, (0, 0, 255), -1)
        out.write(frame)

    key = cv2.waitKey(1) & 0xFF # 대기 시간을 1ms로 줄여 반응속도 향상

    if key == 50: # 숫자 2
        print("녹화 시작")
        record = True
    elif key == 49: # 숫자 1
        print("프로그램 종료")
        break

cap.release()
out.release()
cv2.destroyAllWindows()
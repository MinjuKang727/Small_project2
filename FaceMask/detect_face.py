#haarcascade로 웹캠 얼굴 인식 연습 코드
import cv2

# Haar Cascade Classifier 파일 경로 설정
cascPath = "./haarcascade_xml/haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)

# 동영상 캡처 객체 생성 (0은 기본 카메라)
video_capture = cv2.VideoCapture(0)

while True:
    # 비디오 프레임 읽기
    ret, frame = video_capture.read()
    
    # 프레임을 그레이스케일로 변환
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 얼굴 감지
    faces = faceCascade.detectMultiScale(gray, 1.1, 4)
    
    # 감지된 얼굴에 사각형 그리기
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

    # 결과 프레임 보여주기
    cv2.imshow('Video', frame)
    
    # 'q' 키를 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 리소스 해제
video_capture.release()
cv2.destroyAllWindows()
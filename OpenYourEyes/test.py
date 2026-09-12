import cv2
import mediapipe as mp

# 기존 방식: mp_face_mesh = mp.solutions.face_mesh
# 변경 방식 (직접 참조):
try:
    from mediapipe.python.solutions import face_mesh as mp_face_mesh
    from mediapipe.python.solutions import drawing_utils as mp_drawing
    print("✅ Solutions를 직접 참조하여 로드했습니다.")
except ImportError:
    # 위 방식도 안될 경우 마지막 수단
    import mediapipe.solutions.face_mesh as mp_face_mesh
    print("✅ 하위 경로에서 직접 로드했습니다.")

# 이후 코드에서는 mp_face_mesh를 그대로 사용하면 됩니다.
face_mesh_instance = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
import cv2
import numpy as np
import sys
import os
import glob
import json
import mediapipe as mp
from tqdm import tqdm

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

base_path = os.path.dirname(os.path.abspath(__file__))

# 파일 경로 설정
video_path = r"C:\Users\KJY\Documents\Programming\FaceMask\video\20260729_195000.mp4"
# 비디오 디렉토리와 파일명 추출
video_dir = os.path.dirname(video_path)
video_filename = os.path.splitext(os.path.basename(video_path))[0]

# 저장 경로 자동 생성 (원본과 같은 폴더에 저장)
output_path = os.path.join(video_dir, f"{video_filename}_edit.mp4")
json_path = os.path.join(video_dir, f"{video_filename}_annotations.json")

# 화면 크기 설정
vertical = (1280, 720)
horizontal = (720, 1280)
MAX_DISPLAY_WIDTH, MAX_DISPLAY_HEIGHT = vertical

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

# --- 2. 이미지 미리보기 및 알파벳 선택 창 ---
print("\n모든 마스크 이미지를 하나의 창에 미리 띄웁니다...")

thumb_size = 200
thumbs = []
alphabet_mapping = {} 

for idx, img in enumerate(mask_list):
    if idx >= 26: break 
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

row_images = [np.hstack(thumbs[r * cols:(r + 1) * cols]) for r in range(rows)]
grid_img = np.vstack(row_images)

preview_window = "All Masks Preview (Press A, B, C... to select)"
cv2.namedWindow(preview_window, cv2.WINDOW_NORMAL)
cv2.imshow(preview_window, grid_img)

print("미리보기 창에서 이미지를 확인하고, 원하는 이미지의 알파벳 키를 누르세요! (랜덤/첫 번째 선택: ESC)")

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

# 3. 동영상 기본 정보 준비
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: 동영상을 열 수 없습니다.")
    sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# --- 화면 비율에 맞춘 디스플레이 축소 비율 계산 ---
scale_w = MAX_DISPLAY_WIDTH / width
scale_h = MAX_DISPLAY_HEIGHT / height
display_scale = min(scale_w, scale_h, 1.0)

disp_width = int(width * display_scale)
disp_height = int(height * display_scale)
print(f"원본 영상 크기: {width}x{height} -> 화면 표시 크기: {disp_width}x{disp_height} (비율: {display_scale:.2f})")

# --- [4단계] 기존 저장된 JSON 데이터 로드 또는 자동 감지 실행 ---
annotations = {}
saved_last_frame = 0

if os.path.exists(json_path):
    print(f"\n기존에 저장된 작업 파일('{json_path}')을 발견했습니다!")
    ans = input("이어서 편집하시겠습니까? (Y/N, 기본값 Y): ").strip().lower()
    if ans != 'n':
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "_last_frame" in data:
                    saved_last_frame = data["_last_frame"]
                    del data["_last_frame"]
                annotations = data
            print(f"이전 작업 불러오기 성공! (마지막 작업 프레임: {saved_last_frame})")
        except Exception as e:
            print(f"파일을 읽는 중 오류가 발생했습니다 ({e}). 새로 감지합니다.")
            annotations = {}

if not annotations:
    print("\n[1단계] 저장된 파일이 없거나 새로 시작합니다. 다중 얼굴 자동 감지 중...")
    mp_face_detection = mp.solutions.face_detection

    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        with tqdm(total=total_frames, desc="Auto Detecting Multiple Faces", unit="frame") as pbar:
            f_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret: break

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_frame)

                frame_boxes = []
                if results.detections:
                    for detection in results.detections:
                        box = detection.location_data.relative_bounding_box
                        x_rel, y_rel, w_rel, h_rel = box.xmin, box.ymin, box.width, box.height

                        scale_factor = 1.6 
                        new_w = w_rel * scale_factor
                        new_h = h_rel * scale_factor
                        new_x = x_rel - (new_w - w_rel) / 2
                        new_y = y_rel - (new_h - h_rel) * 0.7  

                        px = float(int(new_x * width))
                        py = float(int(new_y * height))
                        pw = float(int(new_w * width))
                        ph = float(int(new_h * height))

                        cx = max(0, px)
                        cy = max(0, py)
                        cw = pw
                        ch = ph
                        if cx + cw > width: cw = width - cx
                        if cy + ch > height: ch = height - cy

                        if cw > 0 and ch > 0:
                            frame_boxes.append([cx, cy, cw, ch])

                if frame_boxes:
                    annotations[str(f_idx)] = frame_boxes

                pbar.update(1)
                f_idx += 1
    print("자동 다중 감지 좌표 생성 완료!")

cap.release()

# --- [5단계] 인터랙티브 수동 검수 및 수정 GUI 프로그램 ---
print("\n" + "="*50)
print(" [수동 검수 및 수정 모드 안내] ")
print(" - [SPACEBAR]: 앞으로 재생 / 일시정지")
print(" - [Z 키]: 뒤로 감기(역재생) / 일시정지")
print(" - [N / B]: 다음 프레임 / 이전 프레임 이동")
print(" - [> / .]: 재생/되감기 속도 증가 (빨리감기)")
print(" - [< / ,]: 재생/되감기 속도 감소")
print(" - [박스 클릭]: 사각형 단일 선택")
print(" - [Ctrl + 클릭]: 사각형 다중 선택 / 해제")
print(" - [빈 곳 드래그]: 원하는 크기대로 자유롭게 사각형 지정 -> [A]로 추가")
print(" - [F 키]: 선택된 모든 사각형을 다음 프레임에 1개 복사")
print(" - [Shift + F 키]: 선택된 모든 사각형 구간 복사 시작 ([Enter]로 완료)")
print(" - [Shift + I 키]: 얼굴 이동 보간(인터폴레이션) 시작점 지정")
print(" - [도착 프레임에서 Enter]: 보간 시작점과 현재 박스 위치 사이를 부드럽게 채우기")
print(" - [X 키]: 선택된 모든 사각형 삭제")
print(" - [D 키]: 현재 프레임의 모든 사각형 삭제")
print(" - [ESC 키]: 수정 완료 및 최종 영상 렌더링 시작")
print("="*50 + "\n")

cap = cv2.VideoCapture(video_path)
curr_frame = saved_last_frame
paused = True
direction = 1        
playback_speed = 1  
drawing = False
ix, iy = -1, -1
temp_box = None      
selected_indices = set()

copy_mode = False
copy_start_frame = -1
copy_target_boxes = []

interp_mode = False
interp_start_frame = -1
interp_start_box = None

def draw_gui_window(frame, boxes, f_idx, t_box, s_indices, speed, d, c_mode, c_start, i_mode, i_start):
    # frame은 원본 크기 상태입니다.
    img_disp = frame.copy()
    
    # 1. 원본 좌표 그대로 원본 크기 이미지(img_disp)에 사각형 그리기
    if boxes:
        for idx, box in enumerate(boxes):
            x, y, w, h = [int(v) for v in box]
            if idx in s_indices:
                cv2.rectangle(img_disp, (x, y), (x+w, y+h), (255, 0, 0), 3) 
                cv2.putText(img_disp, f"SEL #{idx}", (x, max(20, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            else:
                cv2.rectangle(img_disp, (x, y), (x+w, y+h), (0, 255, 0), 2) 
            
    if t_box:
        tx, ty, tw, th = [int(v) for v in t_box]
        cv2.rectangle(img_disp, (tx, ty), (tx+tw, ty+th), (0, 165, 255), 2)
    
    # 2. 사각형이 모두 그려진 후에 화면 표시용 크기로 리사이즈
    if display_scale < 1.0:
        img_disp = cv2.resize(img_disp, (disp_width, disp_height))
    
    if paused:
        status = "PAUSED"
    else:
        status = f"PLAYING ({'FWD' if d == 1 else 'REV'} {speed}x)"
        
    cv2.putText(img_disp, f"Frame: {f_idx}/{total_frames} | Status: {status}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    if c_mode:
        cv2.putText(img_disp, f"[COPY MODE] Start: {c_start} -> Play & Pause at End, then Press [Enter]", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    if i_mode:
        cv2.putText(img_disp, f"[INTERPOLATION MODE] Start Frame: {i_start} -> Move to End, Select Box & Press [Enter]", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
    return img_disp

def mouse_callback(event, x, y, flags, param):
    global drawing, ix, iy, curr_frame, temp_box, selected_indices, annotations
    
    # 화면 좌표(x, y)를 원본 영상 좌표로 완벽 변환
    orig_x = x / display_scale
    orig_y = y / display_scale
    
    if event == cv2.EVENT_LBUTTONDOWN:
        # 클릭 시 이전 프레임에서 크기 참조
        ref_w, ref_h = 150.0, 150.0
        if curr_frame > 0 and str(curr_frame - 1) in annotations:
            prev_boxes = annotations[str(curr_frame - 1)]
            if prev_boxes:
                # 클릭 지점과 가장 가까운 박스 찾기
                min_dist = float('inf')
                for b in prev_boxes:
                    dist = np.sqrt((orig_x - (b[0]+b[2]/2))**2 + (orig_y - (b[1]+b[3]/2))**2)
                    if dist < min_dist:
                        min_dist = dist
                        ref_w, ref_h = b[2], b[3]
        
        drawing = True
        ix, iy = orig_x, orig_y
        # 클릭 시엔 우선 참조 크기로 생성
        temp_box = [float(orig_x - ref_w/2), float(orig_y - ref_h/2), float(ref_w), float(ref_h)]

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            # 드래그 시: 시작점(ix, iy)과 현재점(orig_x, orig_y)으로 정확히 계산
            x_min = min(ix, orig_x)
            y_min = min(iy, orig_y)
            w_val = abs(orig_x - ix)
            h_val = abs(orig_y - iy)
            temp_box = [float(x_min), float(y_min), float(w_val), float(h_val)]

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False

edit_window = "Manual Review & Edit"
cv2.namedWindow(edit_window, cv2.WINDOW_NORMAL)
cv2.setMouseCallback(edit_window, mouse_callback)

while cap.isOpened():
    cap.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
    ret, frame = cap.read()
    if not ret: break

    boxes = annotations.get(str(curr_frame), [])
    selected_indices = {idx for idx in selected_indices if idx < len(boxes)}

    disp_frame = draw_gui_window(frame, boxes, curr_frame, temp_box, selected_indices, playback_speed, direction, copy_mode, copy_start_frame, interp_mode, interp_start_frame)
    cv2.imshow(edit_window, disp_frame)

    annotations["_last_frame"] = curr_frame
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(annotations, f, indent=4)

    wait_time = max(1, int(30 / playback_speed)) if not paused else 30
    key = cv2.waitKey(wait_time) & 0xFF

    if key == 27: 
        print("\n수정을 완료하고 최종 영상을 렌더링합니다...")
        break
    elif key == ord(' '):  
        if not paused and direction == 1:
            paused = True
        else:
            paused = False
            direction = 1
    elif key == ord('z') or key == ord('Z'):  
        if not paused and direction == -1:
            paused = True
        else:
            paused = False
            direction = -1
    elif key == 13:  
        if copy_mode:
            end_frame = curr_frame
            if end_frame >= copy_start_frame:
                for f_target in range(copy_start_frame, end_frame + 1):
                    f_str = str(f_target)
                    if f_str not in annotations:
                        annotations[f_str] = []
                    for box in copy_target_boxes:
                        annotations[f_str].append(list(box))
                print(f"\n[구간 복사 완료] Frame {copy_start_frame}부터 Frame {end_frame}까지 사각형 복사 완료!")
            copy_mode = False
            copy_target_boxes = []
        elif interp_mode:
            end_frame = curr_frame
            if end_frame > interp_start_frame and len(selected_indices) == 1:
                end_box = annotations[str(end_frame)][list(selected_indices)[0]]
                total_steps = end_frame - interp_start_frame
                
                start_x, start_y, start_w, start_h = interp_start_box
                end_x, end_y, end_w, end_h = end_box
                
                print(f"\n[이동 보간 시작] Frame {interp_start_frame} -> Frame {end_frame} 구간 부드러운 이동 적용 중...")
                for step, f_target in enumerate(range(interp_start_frame, end_frame + 1)):
                    ratio = step / total_steps
                    curr_x = start_x + (end_x - start_x) * ratio
                    curr_y = start_y + (end_y - start_y) * ratio
                    curr_w = start_w + (end_w - start_w) * ratio
                    curr_h = start_h + (end_h - start_h) * ratio
                    
                    f_str = str(f_target)
                    if f_str not in annotations:
                        annotations[f_str] = []
                    annotations[f_str].append([curr_x, curr_y, curr_w, curr_h])
                print("[이동 보간 완료]")
            interp_mode = False
            interp_start_box = None
    elif key == ord('.'):  
        playback_speed = min(16, playback_speed * 2)
    elif key == ord(','):  
        playback_speed = max(1, playback_speed // 2)
    elif key == ord('d') or key == ord('D'): 
        if str(curr_frame) in annotations:
            del annotations[str(curr_frame)]
        temp_box = None
        selected_indices.clear()
    elif key == ord('x') or key == ord('X'):
        if selected_indices and str(curr_frame) in annotations:
            current_boxes = annotations[str(curr_frame)]
            sorted_indices = sorted(list(selected_indices), reverse=True)
            for idx in sorted_indices:
                current_boxes.pop(idx)
            selected_indices.clear()
            if not current_boxes:
                del annotations[str(curr_frame)]
    elif key == ord('a') or key == ord('A'):
        if temp_box is not None:
            if str(curr_frame) not in annotations:
                annotations[str(curr_frame)] = []
            annotations[str(curr_frame)].append(list(temp_box))
            temp_box = None
    elif key == ord('f') or key == ord('F'):
        if key == ord('F'):  
            if selected_indices and str(curr_frame) in annotations:
                copy_target_boxes = [annotations[str(curr_frame)][idx] for idx in selected_indices]
                copy_start_frame = curr_frame
                copy_mode = True
        else:  
            if selected_indices and str(curr_frame) in annotations:
                target_boxes = [annotations[str(curr_frame)][idx] for idx in selected_indices]
                next_frame = min(total_frames - 1, curr_frame + 1)
                if str(next_frame) not in annotations:
                    annotations[str(next_frame)] = []
                for box in target_boxes:
                    annotations[str(next_frame)].append(list(box))
                curr_frame = next_frame
    elif key == ord('i') or key == ord('I'):
        if key == ord('I'):  
            if len(selected_indices) == 1 and str(curr_frame) in annotations:
                interp_start_box = list(annotations[str(curr_frame)][list(selected_indices)[0]])
                interp_start_frame = curr_frame
                interp_mode = True
    
    if key == ord('n'):
        curr_frame = min(total_frames - 1, curr_frame + 1)
        temp_box = None
    elif key == ord('b'):
        curr_frame = max(0, curr_frame - 1)
        temp_box = None

    if not paused:
        curr_frame += direction * playback_speed
        temp_box = None
        if curr_frame >= total_frames:
            curr_frame = total_frames - 1
            paused = True
        elif curr_frame < 0:
            curr_frame = 0
            paused = True

cv2.destroyWindow(edit_window)
cap.release()

if "_last_frame" in annotations:
    del annotations["_last_frame"]
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(annotations, f, indent=4)

# --- [6단계] 최종 영상 렌더링 (다중 합성) ---
print("\n[3단계] 최종 다중 마스크 합성 영상 생성 중...")
cap = cv2.VideoCapture(video_path)
out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

with tqdm(total=total_frames, desc="Rendering Final Video", unit="frame") as pbar:
    f_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break

        boxes = annotations.get(str(f_idx), [])
        if boxes:
            for box in boxes:
                x, y, w, h = [int(v) for v in box]
                cx, cy = max(0, x), max(0, y)
                cw, ch = w, h
                if cx + cw > width: cw = width - cx
                if cy + ch > height: ch = height - cy

                if cw > 0 and ch > 0:
                    try:
                        resized_overlay = cv2.resize(overlay_img, (cw, ch))
                        if resized_overlay.shape[2] == 4:
                            overlay_rgb = resized_overlay[:, :, :3]
                            mask = resized_overlay[:, :, 3] / 255.0
                        else:
                            overlay_rgb = resized_overlay
                            mask = np.ones((ch, cw), dtype=np.float32)

                        roi = frame[cy:cy+ch, cx:cx+cw]
                        if roi.shape[0] == ch and roi.shape[1] == cw:
                            for c in range(3):
                                roi[:, :, c] = (1 - mask) * roi[:, :, c] + mask * overlay_rgb[:, :, c]
                            frame[cy:cy+ch, cx:cx+cw] = roi
                    except cv2.error:
                        pass

        out.write(frame)
        pbar.update(1)
        f_idx += 1

cap.release()
out.release()
print(f"\n모든 작업이 완료되었습니다! 최종 저장 파일: {output_path}")
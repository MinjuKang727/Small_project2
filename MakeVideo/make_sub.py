from pathlib import Path
import cv2
import numpy as np

def load_lyrics_from_file(file_path):
    """
    텍스트 파일에서 가사를 읽어와 줄 단위 리스트로 반환합니다.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("가사 파일을 찾을 수 없습니다.")
        return []

def is_black(color, threshold=40):
    """
    RGB 평균값이 임계값보다 낮으면 검은색으로 판단합니다.
    """
    return all(c < threshold for c in color)

def detect_color_changes(video_path, threshold=30):
    """
    영상의 프레임을 순회하며 단색 배경의 색상(평균 BGR)이 바뀔 때의 시간을 감지합니다.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"영상을 열 수 없습니다: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30.0  # FPS를 가져오지 못할 경우 기본값 설정

    change_times = [0.0]
    prev_color = None
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_count / fps
        mean_color = cv2.mean(frame)[:3]

        if prev_color is None:
            prev_color = mean_color
            frame_count += 1
            continue

        color_diff = np.linalg.norm(np.array(mean_color) - np.array(prev_color))
        
        if color_diff > threshold:
            change_times.append(current_time)
            prev_color = mean_color

        frame_count += 1

    cap.release()
    return change_times

def generate_subtitles_from_file(video_path, lyrics_file_path):
    lyrics = load_lyrics_from_file(lyrics_file_path)
    if not lyrics:
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"영상을 열 수 없습니다: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30.0
    
    prev_color = None
    lyric_index = 0
    subtitles = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        mean_color = cv2.mean(frame)[:3]
        
        if prev_color is None:
            is_currently_black = is_black(mean_color)
            text = "" if is_currently_black else lyrics[lyric_index]
            subtitles.append((0.0, text))
            if not is_currently_black:
                lyric_index += 1
            prev_color = mean_color
        else:
            color_diff = np.linalg.norm(np.array(mean_color) - np.array(prev_color))
            
            if color_diff > 30:  # 색상 변화 임계값
                if is_black(mean_color):
                    subtitles.append((current_time, ""))
                else:
                    text = lyrics[lyric_index] if lyric_index < len(lyrics) else ""
                    subtitles.append((current_time, text))
                    lyric_index += 1
                
                prev_color = mean_color
        
        frame_count += 1

    cap.release()
    return subtitles

def save_to_srt(subtitles, output_file):
    """
    자막 리스트를 .srt 형식으로 변환하여 파일로 저장합니다.
    """
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        milliseconds = int((secs - int(secs)) * 1000)
        return f"{hours:02}:{minutes:02}:{int(secs):02},{milliseconds:03}"

    with open(output_file, 'w', encoding='utf-8') as f:
        for i in range(len(subtitles)):
            start_time = subtitles[i][0]
            end_time = subtitles[i+1][0] if i + 1 < len(subtitles) else start_time + 5.0
            text = subtitles[i][1]
            
            f.write(f"{i + 1}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{text}\n\n")

# --- 사용 예시 ---
if __name__ == "__main__":
    timestamp_video_path = Path("C:/Users/KJY/Documents/Programming/MakeVideo/data/timestamp.mp4")  # 대상 동영상 파일 경로
    lyric_path = Path("C:/Users/KJY/Documents/Programming/MakeVideo/data/lyric.txt")
    lyrics = lyric_path.read_text(encoding="utf-8").split("\n")
    output_srt_path = Path("C:/Users/KJY/Documents/Programming/MakeVideo/data/sub.srt")

    # 1. 색상이 바뀔 때의 시간 리스트 추출
    times = detect_color_changes(timestamp_video_path)
    print("색상 변경 시간 리스트:", times)

    # 2. 가사 매칭 및 검은색 배경 공백 처리 적용
    results = generate_subtitles_from_file(timestamp_video_path, lyric_path)
    if results:
        save_to_srt(results, output_srt_path)
        print(f"'{output_srt_path}' 파일이 성공적으로 생성되었습니다.")
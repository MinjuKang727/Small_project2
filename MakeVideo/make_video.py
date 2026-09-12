
import re
import cv2
import numpy as np
from pathlib import Path
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, ColorClip
from moviepy.editor import ImageSequenceClip

def load_lyrics_from_file(file_path):
    """텍스트 파일에서 가사를 읽어와 리스트로 반환합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("가사 파일을 찾을 수 없습니다.")
        return []

def is_black(color, threshold=40):
    """RGB 평균값이 임계값보다 낮으면 검은색으로 판단합니다."""
    return all(c < threshold for c in color)

def process_timeline(video_path, lyrics_file_path, image_names):
    """
    영상 색상 변화를 감지하여 타임스탬프를 찍고, 
    가사와 이미지를 매칭하여 통합 타임라인 리스트를 생성합니다.
    (검은색 배경일 경우 가사는 공백, 이미지는 이전 이미지 유지)
    """
    lyrics = load_lyrics_from_file(lyrics_file_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"영상을 열 수 없습니다: {video_path}")
        return [], 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps

    prev_color = None
    lyric_index = 0
    img_index = 0
    events = [] # (start_time, text, image_name)
    frame_count = 0

    # 첫 프레임 처리
    ret, frame = cap.read()
    if ret:
        mean_color = cv2.mean(frame)[:3]
        prev_color = mean_color
        
        is_currently_black = is_black(mean_color)
        text = "" if is_currently_black else (lyrics[lyric_index] if lyric_index < len(lyrics) else "")
        if not is_currently_black:
            lyric_index += 1
            
        current_image = image_names[img_index] if image_names else None
        events.append((0.0, text, current_image))
        frame_count += 1

    # 프레임 순회하며 변경점 포착
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        current_time = frame_count / fps
        mean_color = cv2.mean(frame)[:3]
        color_diff = np.linalg.norm(np.array(mean_color) - np.array(prev_color))
        
        if color_diff > 30: # 색상 변화 발생
            is_currently_black = is_black(mean_color)
            
            if is_currently_black:
                # 검은색 배경: 가사는 공백, 이미지는 직전 이미지 유지
                text = ""
                current_image = events[-1][2] if events else (image_names[0] if image_names else None)
            else:
                # 일반 배경: 다음 가사 매칭 및 다음 이미지로 교체
                text = lyrics[lyric_index] if lyric_index < len(lyrics) else ""
                lyric_index += 1
                
                if img_index + 1 < len(image_names):
                    img_index += 1
                current_image = image_names[img_index] if image_names else None

            events.append((current_time, text, current_image))
            prev_color = mean_color
            
        frame_count += 1

    cap.release()
    return events, video_duration

def save_to_srt(events, video_duration, output_file):
    """타임라인 데이터를 기반으로 .srt 자막 파일을 생성합니다."""
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        milliseconds = int((secs - int(secs)) * 1000)
        return f"{hours:02}:{minutes:02}:{int(secs):02},{milliseconds:03}"

    with open(output_file, 'w', encoding='utf-8') as f:
        for i in range(len(events)):
            start_time = events[i][0]
            end_time = events[i+1][0] if i + 1 < len(events) else video_duration
            text = events[i][1]
            
            f.write(f"{i + 1}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{text}\n\n")

def create_video_with_images_and_audio(events, video_duration, image_folder, audio_path, output_video_path):
    clips = []
    
    # 1. 클립 생성
    for i in range(len(events)):
        start_time = events[i][0]
        image_name = events[i][2]
        end_time = events[i+1][0] if i + 1 < len(events) else video_duration
        duration = end_time - start_time
        if duration <= 0: continue
            
        img_path = Path(image_folder) / image_name
        if img_path.exists():
            clip = ImageClip(str(img_path)).set_duration(duration)
        else:
            clip = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(duration)
        clips.append(clip)

    if not clips: return

    # 2. 비디오 연결
    final_video = concatenate_videoclips(clips, method="compose")

    # 3. 오디오 로드 및 결합
    audio_file_str = str(audio_path)
    if Path(audio_path).exists():
        # 오디오 로드
        audio = AudioFileClip(audio_file_str)
        
        # 영상 전체 길이를 오디오 길이에 강제 동기화
        final_video = final_video.set_duration(audio.duration)
        
        # 오디오를 영상에 셋팅
        final_video = final_video.set_audio(audio)
    else:
        print(f"오디오 파일을 찾을 수 없습니다: {audio_file_str}")

    # 4. 파일 쓰기
    # fps와 오디오 코덱을 명시적으로 선언
    final_video.write_videofile(
        output_video_path, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        temp_audiofile='temp-audio.m4a', 
        remove_temp=True
    )
    print(f"'{output_video_path}' 비디오가 성공적으로 생성되었습니다!")

def create_video_fast(events, image_folder, audio_path, output_video_path, fps=24):
    frame_list = []
    current_img_path = None
    
    # print(f"{'Line':<6} | {'Start(s)':<8} | {'Dur(s)':<6} | {'Image File':<12} | {'Text'}")
    # print("-" * 60)
    
    for i in range(len(events)):
        start_time = events[i][0]
        text = events[i][1]
        img_name = events[i][2]
        
        # 다음 이벤트 시작 시간 계산
        end_time = events[i+1][0] if i + 1 < len(events) else None
        duration = end_time - start_time if end_time else 5.0
        num_frames = int(duration * fps)
        
        # # [디버깅용 출력]
        # print(f"{i+1:<6} | {start_time:<8.2f} | {duration:<6.2f} | {str(img_name):<12} | {text}")
        
        # 이미지 업데이트 로직
        if text.strip() != "":
            if img_name:
                current_img_path = str(Path(image_folder) / img_name)
        
        # 이미지 시퀀스에 프레임 추가
        if current_img_path and Path(current_img_path).exists():
            frame_list.extend([current_img_path] * num_frames)
        else:
            # 이미지가 없을 경우 검은 화면 프레임 추가
            frame_list.extend(["black_placeholder"] * num_frames)

    # # 렌더링 시작 전 전체 분석 시간 출력
    # total_video_time = sum(events[i+1][0] - events[i][0] for i in range(len(events)-1)) if len(events) > 1 else 0
    # print("-" * 75)
    # print(f"총 타임라인 시간: {total_video_time:.2f}초")

    # 3. None으로 남은 구간은 검은 화면으로 대체 (옵션)
    # 필요한 경우 ImageSequenceClip 생성 전 None을 검은색 이미지 경로로 교체 가능
    # 여기서는 간단히 오류 방지를 위해 필터링 처리
    frame_list = [f if f is not None else "black_placeholder" for f in frame_list]

    # 4. 이미지 시퀀스 클립 생성
    final_video = ImageSequenceClip(frame_list, fps=fps)

    # 5. 오디오 결합 및 저장
    audio_file_str = str(audio_path)
    if Path(audio_path).exists():
        audio = AudioFileClip(audio_file_str)
        # 영상 길이를 오디오에 맞춤
        final_video = final_video.set_duration(audio.duration)
        final_video = final_video.set_audio(audio)
    
    final_video.write_videofile(
        str(output_video_path), 
        fps=fps, 
        codec="libx264", 
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

def parse_time_to_seconds(time_str):
    """ SRT 시간 형식(HH:MM:SS,mmm)을 초(float)로 변환합니다. """
    hours, minutes, rest = time_str.split(':')
    seconds, milliseconds = rest.split(',')
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000.0

def get_timestamps_from_srt(srt_file_path):
    """
    기존 srt 파일에서 시작 시간(타임스탬프) 리스트를 추출합니다.
    """
    timestamps = []
    try:
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # SRT 시간 패턴 매칭 (예: 00:00:01,234 --> 00:00:04,567)
        time_patterns = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', content)
        
        for start_str, end_str in time_patterns:
            start_sec = parse_time_to_seconds(start_str)
            timestamps.append(start_sec)
            
    except FileNotFoundError:
        print(f"SRT 파일을 찾을 수 없습니다: {srt_file_path}")
        
    return timestamps

def create_timeline_from_srt(srt_file_path, lyrics_file_path, image_names):
    timestamps = get_timestamps_from_srt(srt_file_path)
    lyrics = load_lyrics_from_file(lyrics_file_path) # 가사 파일 내용 로드
    
    if not timestamps:
        return [], 0.0

    events = []
    
    # [핵심 수정] 
    # SRT 구간(timestamps)은 총 5개인데, 실제 가사는 4개라면
    # 가사가 있는 구간에서만 이미지를 넘기도록 변경합니다.
    lyric_idx = 0
    img_idx = 0
    
    # SRT 파일의 자막 텍스트도 가져와야 가사가 없는 구간을 정확히 판단 가능
    # get_subtitles_text 함수를 추가하거나, 아래처럼 직접 파싱
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        srt_content = f.read().split('\n\n')
    
    for i, block in enumerate(srt_content):
        if i >= len(timestamps): break
        
        # 블록에서 시간 줄 제외하고 텍스트만 추출
        lines = block.split('\n')
        text = "\n".join(lines[2:]).strip() # 자막 내용
        
        start_time = timestamps[i]
        
        # 이미지 결정
        current_img = image_names[img_idx]
        
        # 텍스트가 비어있지 않으면(진짜 가사면) 다음 이미지로 인덱스 증가
        # 가사 리스트에도 text가 존재하는지 확인
        if text != "":
            if img_idx + 1 < len(image_names):
                img_idx += 1
                
        events.append((start_time, text, current_img))

    video_duration = timestamps[-1] + 5.0
    return events, video_duration

def get_timeline(target_srt, video_file, lyrics_file, image_list):
    """
    SRT 파일 상태에 따라 타임라인을 생성하거나 동영상을 분석하여 생성합니다.
    """
    # 1. SRT 파일 존재 및 내용 확인
    if target_srt.exists() and target_srt.stat().st_size > 0:
        print(f"'{target_srt}' 파일 발견. 동영상 분석을 건너뜁니다.")
        return create_timeline_from_srt(str(target_srt), lyrics_file, image_list)
    
    # 2. SRT가 없거나 비어있으면 동영상 분석
    else:
        print(f"SRT가 없거나 비어있습니다. '{video_file}' 분석 시작...")
        events, duration = process_timeline(str(video_file), str(lyrics_file), image_list)
        save_to_srt(events, duration, str(target_srt))
        return events, duration

# --- 실행부 ---
if __name__ == "__main__":
    # 경로 설정 (Path 객체 사용)
    data_dir = Path("C:/Users/KJY/Documents/Programming/MakeVideo/data")
    video_file = data_dir / "timestamp.mp4"
    lyrics_file = data_dir / "lyric.txt"
    image_folder = data_dir / "img"
    audio_path = data_dir / "audio.mp3"
    output_srt = data_dir / "sub.srt"
    output_video = data_dir / "final_video.mp4"

    # 이미지 리스트 생성
    img_num_list = [1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    image_list = [ f"{i}.png" for i in img_num_list]

    # [핵심 로직 실행]
    timeline_events, duration = get_timeline(output_srt, video_file, lyrics_file, image_list)

    if timeline_events:
        print(f"총 {len(timeline_events)}개의 타임라인 이벤트가 준비되었습니다.")
        
        # 오디오 길이에 맞춰 최종 비디오 길이 재설정
        if audio_path.exists():
            with AudioFileClip(str(audio_path)) as audio:
                duration = audio.duration
        
        print("이미지 및 오디오 합성 비디오 생성 중...")
        # create_video_with_images_and_audio(
        #     timeline_events, duration, str(image_folder), str(audio_path), str(output_video)
        # )
        create_video_fast(timeline_events, image_folder, audio_path, str(output_video))
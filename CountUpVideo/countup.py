import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm
from pathlib import Path

def create_counter_image(
    current_time_sec=0.0,
    output_path="counter_image.png",
    width=1280,
    height=720,
    bg_color=(255, 229, 247),   # 배경 박스 색상 (RGB)
    text_color=(255, 8, 85),    # 글자 색상 (RGB)
):
    """
    지정한 시간(초)의 텍스트와 스타일을 적용하여 단일 이미지로 저장하는 메서드
    """
    new_folder = Path(output_path).parent
    new_folder.mkdir(parents=True, exist_ok=True)

    # 폰트 설정
    try:
        font = ImageFont.truetype("malgun.ttf", 90)
    except IOError:
        font = ImageFont.load_default()

    # 시간 포맷팅 (HH:MM:SS.mmm)
    hours = int(current_time_sec // 3600)
    minutes = int((current_time_sec % 3600) // 60)
    seconds = int(current_time_sec % 60)
    milliseconds = int(round((current_time_sec - int(current_time_sec)) * 1000))
    
    if milliseconds >= 1000:
        milliseconds = 999

    time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    # 이미지 생성 및 배경 설정
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 박스 위치 및 크기 설정
    box_width, box_height = 550, 140
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2
    
    # 둥근 배경 박스 그리기
    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_width, box_y + box_height],
        radius=20,
        fill=bg_color
    )
    
    # 텍스트 중앙 정렬 계산
    bbox = draw.textbbox((0, 0), time_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    text_x = box_x + (box_width - text_w) / 2 - bbox[0]
    text_y = box_y + (box_height - text_h) / 2 - bbox[1]
    
    # 텍스트 그리기
    draw.text((text_x, text_y), time_text, font=font, fill=text_color)
    
    # 이미지 파일 저장
    img.save(output_path)
    print(f"이미지 저장 완료: {output_path}")


def create_counter_video(
    duration_seconds=1200, 
    fps=30, 
    output_filename="counter_video.mp4",
    bg_color=(20, 20, 20),      # 배경 박스 색상 (RGB)
    text_color=(0, 255, 102),   # 글자 색상 (RGB)
):
    """
    hold 기능이 제거된 순수 카운트업 영상 생성기
    """

    base_dir = Path(__file__).resolve().parent
    new_folder = base_dir / f"save/{duration_seconds}s"
    new_folder.mkdir(parents=True, exist_ok=True)
    output_path = new_folder / output_filename
    
    width, height = 1280, 720  # 해상도 설정
    total_frames = duration_seconds * fps
    
    print(f"총 {duration_seconds}초 ({total_frames} 프레임) 영상 생성 시작...")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    try:
        font = ImageFont.truetype("malgun.ttf", 90)
    except IOError:
        font = ImageFont.load_default()

    box_width, box_height = 550, 140
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2

    # 공통 텍스트 렌더링 함수
    def draw_frame(current_time_sec):
        hours = int(current_time_sec // 3600)
        minutes = int((current_time_sec % 3600) // 60)
        seconds = int(current_time_sec % 60)
        milliseconds = int(round((current_time_sec - int(current_time_sec)) * 1000))
        
        if milliseconds >= 1000:
            milliseconds = 999

        time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw.rounded_rectangle(
            [box_x, box_y, box_x + box_width, box_y + box_height],
            radius=20,
            fill=bg_color
        )
        
        bbox = draw.textbbox((0, 0), time_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        text_x = box_x + (box_width - text_w) / 2 - bbox[0]
        text_y = box_y + (box_height - text_h) / 2 - bbox[1]
        
        draw.text((text_x, text_y), time_text, font=font, fill=text_color)
        
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # 타이머 진행 프레임 생성 및 저장 (Hold 로직 제거됨)
    for i in tqdm(range(total_frames), desc="프레임 생성 및 저장 중"):
        if i == total_frames - 1:
            current_time_sec = float(duration_seconds)
        else:
            current_time_sec = i / fps

        frame_bgr = draw_frame(current_time_sec)
        video_writer.write(frame_bgr)

    video_writer.release()
    print(f"완료! 저장된 파일: {output_filename}")
    return new_folder


if __name__ == "__main__":
    folder_dir = Path("./save")

    SET_DURATION_SECONDS = 30 * 60   # 재생 시간 (초) -> 30분
    bg_color = (255, 229, 247)
    text_color = (255, 8, 85)

    
    # # 1. 기존 스타일이 적용된 카운트업 영상 생성 (Hold 기능 없음)
    # folder_dir = create_counter_video(
    #     duration_seconds=SET_DURATION_SECONDS, 
    #     output_filename=f"countup_{SET_DURATION_SECONDS}s.mp4",
    #     bg_color=bg_color,
    #     text_color=text_color
    # )
    # print(folder_dir)
    # START_TIME_SEC = 0
    # END_TIME_SEC = SET_DURATION_SECONDS
    
    # # 2. 동일한 스타일로 특정 시간을 이미지로 생성하는 테스트
    # create_counter_image(
    #     current_time_sec=START_TIME_SEC,  
    #     output_path = folder_dir / f"time_img_{START_TIME_SEC}s.png",
    #     bg_color=bg_color,
    #     text_color=text_color
    # )
    # create_counter_image(
    #         current_time_sec=END_TIME_SEC,  
    #         output_path= folder_dir / f"time_img_{END_TIME_SEC}s.png",
    #         bg_color=bg_color,
    #         text_color=text_color
    #     )
    
    TIME_SEC = 18 * 60 + 28.1
    create_counter_image(
            current_time_sec=TIME_SEC,  
            output_path= folder_dir / f"time_img_{TIME_SEC}s.png",
            bg_color=bg_color,
            text_color=text_color
        )
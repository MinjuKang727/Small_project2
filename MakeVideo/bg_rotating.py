import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from tqdm import tqdm

def create_rotating_pattern_video(
    image_path,
    output_filename="rotating_pattern.mp4",
    duration_seconds=10,
    fps=30,
    bg_color=(240, 240, 240),  # 전체 배경 색상 (RGB)
    grid_spacing_x=300,        # 이미지 간 가로 간격
    grid_spacing_y=300,        # 이미지 간 세로 간격
    rotation_speed=0.5,        # 초당 회전 각도 (속도 조절)
    image_scale=0.3,           # 이미지 크기 비율 (원본 기준)
    pattern_type="staggered",  # 패턴 종류: "grid", "staggered", "diagonal", "honeycomb"
    width=1280,
    height=720
):
    """
    다양한 패턴 스타일(기본 격자, 지그재그, 대각선, 벌집형)을 지원하는 회전 동영상 생성기
    """
    total_frames = duration_seconds * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    source_img = Image.open(image_path).convert("RGBA")
    new_size = (int(source_img.width * image_scale), int(source_img.height * image_scale))
    resized_img = source_img.resize(new_size, Image.Resampling.LANCZOS)
    
    print(f"총 {duration_seconds}초 ({total_frames} 프레임) [{pattern_type}] 패턴 영상 생성 시작...")
    
    for frame_idx in tqdm(range(total_frames), desc="회전 패턴 영상 생성 중"):
        current_time = frame_idx / fps
        angle = current_time * rotation_speed * 360
        
        rotated_img = resized_img.rotate(angle, expand=True)
        bg = Image.new("RGB", (width, height), bg_color)
        
        start_x = -grid_spacing_x * 2
        start_y = -grid_spacing_y
        end_x = width + grid_spacing_x * 2
        end_y = height + grid_spacing_y
        
        # 벌집 패턴일 경우 세로 간격을 조금 더 좁혀서 맞물리게 조정
        actual_spacing_y = int(grid_spacing_y * 0.866) if pattern_type == "honeycomb" else grid_spacing_y
        
        row_idx = 0
        y = start_y
        while y < end_y:
            # 패턴 종류에 따른 x축 오프셋 계산
            if pattern_type == "staggered":
                # 지그재그 (홀수 행마다 절반 밀기)
                x_offset = (grid_spacing_x // 2) if (row_idx % 2 != 0) else 0
            elif pattern_type == "diagonal":
                # 대각선 흐름 (행이 내려갈수록 오른쪽으로 일정하게 밀림)
                x_offset = (row_idx * (grid_spacing_x // 3)) % grid_spacing_x
            elif pattern_type == "honeycomb":
                # 벌집 형태 (지그재그와 유사하지만 세로 간격이 좁음)
                x_offset = (grid_spacing_x // 2) if (row_idx % 2 != 0) else 0
            else:
                # 기본 격자
                x_offset = 0
            
            x = start_x + x_offset
            while x < end_x:
                paste_x = x + (grid_spacing_x - rotated_img.width) // 2
                paste_y = y + (actual_spacing_y - rotated_img.height) // 2
                
                bg.paste(rotated_img, (int(paste_x), int(paste_y)), rotated_img)
                
                x += grid_spacing_x
            
            y += actual_spacing_y
            row_idx += 1
        
        frame_bgr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)
        
    video_writer.release()
    print(f"완료! 저장된 파일: {output_filename}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent / "data/background"
    my_image = base_dir / "img/nunchaku.png"
    img_name = my_image.stem
    
    # 예시: 대각선 흐름 패턴으로 생성하기
    output_video = base_dir / "save" / f"rotating_{img_name}_diagonal.mp4"
    create_rotating_pattern_video(
        image_path=str(my_image),
        output_filename=str(output_video),
        duration_seconds=10,
        bg_color=(245, 247, 250),
        grid_spacing_x=250,
        grid_spacing_y=250,
        rotation_speed=0.2,
        image_scale=0.25,
        pattern_type="diagonal"  # "grid", "staggered", "diagonal", "honeycomb" 중 선택 가능
    )
import cv2
import numpy as np
import math
from PIL import Image
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

def create_rotating_pattern_video(
    image_path,
    output_filename="rotating_pattern.mp4",
    duration_seconds=10,
    fps=30,
    bg_color=(245, 247, 250),  # 전체 배경 색상 (RGB)
    grid_spacing=250,          # 격자 간격 (격자/물결 패턴용)
    rotation_speed=0.2,        # 초당 회전 각도 (속도 조절)
    image_scale=0.25,          # 이미지 크기 비율 (원본 기준)
    pattern_type="radial_expanding",  # 패턴 종류 선택: 
                                      # "grid", "staggered", "diagonal", "honeycomb", 
                                      # "wave", "radial", "radial_expanding"
    width=1280,
    height=720
):
    """
    다양한 패턴(격자, 엇갈림, 대각선, 벌집, 물결, 방사형, 원형 확산)과 
    회전 효과를 조합하여 동영상을 생성하는 함수
    """
    total_frames = duration_seconds * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # 출력 파일 경로 설정 및 폴더 자동 생성
    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    # 1. 소스 이미지 로드 및 크기 조절
    source_img = Image.open(image_path).convert("RGBA")
    new_size = (int(source_img.width * image_scale), int(source_img.height * image_scale))
    resized_img = source_img.resize(new_size, Image.Resampling.LANCZOS)
    
    print(f"총 {duration_seconds}초 ({total_frames} 프레임) [{pattern_type}] 패턴 영상 생성 시작...")
    
    # 원형 확산 패턴을 위한 설정 값
    max_radius = math.hypot(width, height) / 2
    expansion_speed = max_radius / duration_seconds
    num_layers = 8
    
    for frame_idx in tqdm(range(total_frames), desc="영상 렌더링 중"):
        current_time = frame_idx / fps
        angle = current_time * rotation_speed * 360
        
        # 미리 회전된 이미지 생성
        rotated_img = resized_img.rotate(angle, expand=True)
        bg = Image.new("RGB", (width, height), bg_color)
        
        # --- 패턴별 렌더링 로직 ---
        
        # 1. 원형 확산 (Expanding Radial) 패턴
        if pattern_type == "radial_expanding":
            icons_per_layer = 32
            for layer in range(num_layers):
                current_layer_radius = (expansion_speed * current_time + (layer * max_radius / num_layers)) % max_radius
                
                # 중심에서 멀어질수록 크기가 커지는 원근감 효과 추가
                scale_factor = 0.2 + (current_layer_radius / max_radius) * 0.8
                scaled_w = int(rotated_img.width * scale_factor)
                scaled_h = int(rotated_img.height * scale_factor)
                
                # 크기가 0이 되는 오류 방지
                if scaled_w > 0 and scaled_h > 0:
                    zoomed_img = rotated_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                else:
                    zoomed_img = rotated_img

                for i in range(icons_per_layer):
                    theta = (2 * math.pi / icons_per_layer) * i + (current_time * 0.2 * (layer % 2 * 2 - 1))
                    px = width // 2 + current_layer_radius * math.cos(theta) - zoomed_img.width // 2
                    py = height // 2 + current_layer_radius * math.sin(theta) - zoomed_img.height // 2
                    bg.paste(zoomed_img, (int(px), int(py)), zoomed_img)

        # 2. 방사형 회전 (Radial Spin) 패턴
        elif pattern_type == "radial":
            num_circles = 6
            for r in range(1, num_circles + 1):
                radius = r * 100
                items_in_circle = r * 8
                for i in range(items_in_circle):
                    theta = (2 * math.pi / items_in_circle) * i + (current_time * 0.5 * (r % 2 * 2 - 1))
                    px = width // 2 + radius * math.cos(theta) - rotated_img.width // 2
                    py = height // 2 + radius * math.sin(theta) - rotated_img.height // 2
                    bg.paste(rotated_img, (int(px), int(py)), rotated_img)

        # 3. 격자 기반 패턴 (Grid, Staggered, Diagonal, Honeycomb, Wave)
        else:
            start_x = -grid_spacing * 2
            start_y = -grid_spacing
            end_x = width + grid_spacing * 2
            end_y = height + grid_spacing
            
            actual_spacing_y = int(grid_spacing * 0.866) if pattern_type == "honeycomb" else grid_spacing
            
            row_idx = 0
            y = start_y
            while y < end_y:
                offset_x = 0
                offset_y = 0
                
                if pattern_type == "staggered" and (row_idx % 2 != 0):
                    offset_x = grid_spacing // 2
                elif pattern_type == "diagonal":
                    offset_x = (row_idx * (grid_spacing // 3)) % grid_spacing
                elif pattern_type == "honeycomb" and (row_idx % 2 != 0):
                    offset_x = grid_spacing // 2
                elif pattern_type == "wave":
                    offset_y = math.sin(current_time * 3 + (y / grid_spacing)) * 30
                
                x = start_x + offset_x
                while x < end_x:
                    paste_x = x + (grid_spacing - rotated_img.width) // 2
                    paste_y = y + (actual_spacing_y - rotated_img.height) // 2
                    
                    bg.paste(rotated_img, (int(paste_x), int(paste_y + offset_y)), rotated_img)
                    x += grid_spacing
                
                y += actual_spacing_y
                row_idx += 1
        
        # OpenCV 포맷(BGR)으로 변환 후 저장
        frame_bgr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)
        
    video_writer.release()
    print(f"완료! 저장된 파일: {output_filename}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent / "data/background"
    img_dir = base_dir / "img"
    my_image = img_dir / "fist_golden.png"
    img_name = my_image.stem
    
    # 💡 원하시는 패턴 타입("radial_expanding")으로 테스트해 보세요!
    now = datetime.now()
    file_timestamp = now.strftime("%Y%m%d%H%M%S")
    pattern_type = "staggered"
    output_video = base_dir / "save" / f"{pattern_type}_{img_name}_{file_timestamp}.mp4"

    
    create_rotating_pattern_video(
        image_path=str(my_image),
        output_filename=str(output_video),
        duration_seconds=60,
        bg_color=(0,0,0),
        grid_spacing=250,
        rotation_speed=0.2,
        image_scale=0.25,
        pattern_type=pattern_type
        # 사용 가능한 옵션: 
        # "grid"(격자), "staggered"(지그재그), "diagonal"(대각선 흐름), "honeycomb"(벌집), "wave"(물결), "radial"(원형), "radial_expanding"(원형 확산)
    )



    # base_dir = Path(__file__).resolve().parent / "data/background"
    
    # img_dir = base_dir / "img"
    # img_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    # img_names = [
    #     file.stem for file in img_dir.iterdir() 
    #     if file.is_file() and file.suffix.lower() in img_extensions
    # ]

    # for img_name in img_names:
    #     my_image = img_dir / f"{img_name}.png"
        
    #     # 💡 원하시는 패턴 타입("radial_expanding")으로 테스트해 보세요!
    #     now = datetime.now()
    #     file_timestamp = now.strftime("%Y%m%d%H%M%S")
    #     pattern_type = "staggered"
    #     output_video = base_dir / "save" / f"{pattern_type}_{img_name}_{file_timestamp}.mp4"
    #     bg_color = (255, 255, 255)
    #     if "white" in img_name :
    #         bg_color = (0, 0, 0)
        
    #     create_rotating_pattern_video(
    #         image_path=str(my_image),
    #         output_filename=str(output_video),
    #         duration_seconds=60,
    #         bg_color=bg_color,
    #         grid_spacing=250,
    #         rotation_speed=0.2,
    #         image_scale=0.25,
    #         pattern_type=pattern_type
    #         # 사용 가능한 옵션: 
    #         # "grid"(격자), "staggered"(지그재그), "diagonal"(대각선 흐름), "honeycomb"(벌집), "wave"(물결), "radial"(원형), "radial_expanding"(원형 확산)
    #     )
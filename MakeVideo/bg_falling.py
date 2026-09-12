import cv2
import numpy as np
import random
from PIL import Image, ImageOps
from pathlib import Path
from tqdm import tqdm

def create_falling_images_video(
    image_path,
    output_filename="falling_effect.mp4",
    duration_seconds=10,
    fps=30,
    bg_color=(255, 255, 255),
    width=1280,
    height=720,
    min_speed=3,  # 최소 떨어지는 속도 (기본값: 3)
    max_speed=8   # 최대 떨어지는 속도 (기본값: 8)
):
    """
    배경색 위에 이미지가 랜덤하게 회전하며 떨어지는 영상 생성
    """
    total_frames = duration_seconds * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    source_img = Image.open(image_path).convert("RGBA")
    falling_objects = []
    
    print(f"총 {duration_seconds}초 ({total_frames} 프레임) 영상 생성 시작...")
    
    for _ in tqdm(range(total_frames), desc="회전 낙하 효과 영상 생성 중"):
        img = Image.new("RGB", (width, height), bg_color)
        
        # 새로운 객체 생성
        if random.random() < 0.05:
            scale = random.uniform(0.1, 0.3)
            size = (int(source_img.width * scale), int(source_img.height * scale))
            img_resized = source_img.resize(size, Image.Resampling.LANCZOS)
            
            falling_objects.append({
                "img_base": img_resized,
                "x": random.uniform(0, width - img_resized.width),
                "y": -img_resized.height,
                "speed": random.uniform(min_speed, max_speed),  # 👈 여기서 전달받은 속도 범위 적용
                "angle": random.uniform(0, 360),
                "rot_speed": random.uniform(-5, 5)
            })
        
        # 객체 이동, 회전 및 그리기
        for obj in falling_objects[:]:
            obj["y"] += obj["speed"]
            obj["angle"] += obj["rot_speed"]
            
            rotated_img = obj["img_base"].rotate(obj["angle"], expand=True)
            
            paste_x = obj["x"] - (rotated_img.width - obj["img_base"].width) / 2
            paste_y = obj["y"] - (rotated_img.height - obj["img_base"].height) / 2
            
            img.paste(rotated_img, (int(paste_x), int(paste_y)), rotated_img)
            
            if obj["y"] > height:
                falling_objects.remove(obj)
        
        video_writer.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        
    video_writer.release()
    print(f"영상 생성 완료: {output_filename}")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent / "data/background"
    my_image = base_dir / "img/nunchaku.png"
    img_name = my_image.stem
    
    output_video = base_dir / "save" / f"falling_rotating_{img_name}.mp4"
    
    create_falling_images_video(
        image_path=str(my_image),
        output_filename=str(output_video),
        duration_seconds=60,
        bg_color=(240, 248, 255),
        min_speed=1,   # 👈 느리게 하고 싶다면 낮추고(예: 1, 2), 빠르게 하고 싶다면 높이세요(예: 5, 10)
        max_speed=12   # 👈 
    )
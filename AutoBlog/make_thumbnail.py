from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime


def create_blog_thumbnail(
    input_image_path: Path,
    output_image_path: Path,
    title_text: str
):
  # 1. 파일 존재 여부 확인 (pathlib의 .exists() 활용)
  if not input_image_path.exists():
    print(f"오류: 원본 파일을 찾을 수 없습니다 - {input_image_path}")
    return

  try:
    # 2. 이미지 열기 (pathlib 객체를 그대로 전달 가능)
    img = Image.open(input_image_path)
    draw = ImageDraw.Draw(img)

    # 폰트 설정 (pathlib으로 폰트 경로 지정)
    font_path = Path("C:/USERS/KJY/APPDATA/LOCAL/MICROSOFT/WINDOWS/FONTS/CHIRONSUNGHK-EXTRABOLD.TTF")

    if font_path.exists():
        title_font = ImageFont.truetype(str(font_path), 80)
    else:
        print(f"경고: 폰트 파일을 찾을 수 없습니다 ({font_path}). 기본 폰트를 사용합니다.")
        title_font = ImageFont.load_default()

    width, height = img.size
    padding_x = 80  # 좌우 여백
    padding_y = 80  # 상하 여백
    max_allowed_width = width - (2 * padding_x)
    max_allowed_height = height - (2 * padding_y)

    # [자동 폰트 크기 조절] 텍스트가 패딩 영역을 넘지 않도록 크기 조정
    font_size = 80  # 시작 폰트 크기
    min_font_size = 20  # 최소 폰트 크기 마지노선

    while font_size >= min_font_size:
        if font_path.exists():
            title_font = ImageFont.truetype(str(font_path), font_size)
        else:
            title_font = ImageFont.load_default()
            break

        # 현재 폰트 크기로 텍스트 블록 크기 계산
        bbox = draw.multiline_textbbox((0, 0), title_text, font=title_font, align="center")
          
        text_block_width = bbox[2] - bbox[0] # 텍스트 블록의 총 가로 길이
        text_block_height = bbox[3] - bbox[1] # 텍스트 블록의 총 세로 길이

        # 설정한 패딩 박스 안에 쏙 들어가면 반복 중지
        if (
            text_block_width <= max_allowed_width
            and text_block_height <= max_allowed_height
        ):
            break

        # 크기를 초과하면 폰트 크기를 5씩 줄여가며 재검사
        font_size -= 5

    # 6. 정중앙 좌표 (X, Y) 계산 (패딩 박스 내부에서의 중앙이 아니라 전체 이미지 기준 정중앙)
    x_centered = (width - text_block_width) / 2
    y_centered = (height - text_block_height) / 2

    

    # 4. 텍스트 스타일 설정 (검은색, 정중앙 정렬)
    text_color = "black"
    shadow_color = (200, 200, 200, 128) # 반투명 회색 그림자
    shadow_offset = 3

    # 그림자 효과 그리기
    draw.multiline_text(
        (x_centered + shadow_offset, y_centered + shadow_offset),
        title_text,
        font=title_font,
        fill=shadow_color,
        align="center",
    )

    # 실제 검은색 텍스트 그리기
    draw.multiline_text(
        (x_centered, y_centered),
        title_text,
        font=title_font,
        fill=text_color,
        align="center",
    )

    # 8. 결과 이미지 저장 (투명도 제거 후 JPEG 저장)
    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 5. 결과 이미지 저장 (부모 디렉토리가 없으면 자동 생성)
    output_image_path.mkdir(parents=True, exist_ok=True)
    output_image_path = output_image_path / f"{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg"
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    img.save(output_image_path, "JPEG")
    print(f"썸네일 생성 완료: {output_image_path}")

    # 6. 이미지 미리보기 (Pillow 내장 .show() 활용)
    img.show()

  except Exception as e:
    print(f"예기치 않은 오류 발생: {e}")


# --- 실행 예제 (Path 객체 활용) ---
if __name__ == "__main__":
  # 경로를 Path 객체로 정의
  input_file = Path("C:/Users/KJY/Documents/Programming/AutoBlog/img/korean.png")
  output_file = input_file.parent / "thumbnails"

  create_blog_thumbnail(
      input_image_path=input_file,
      output_image_path=output_file,
      title_text="Pathlib으로 썸네일 자동화!"
  )
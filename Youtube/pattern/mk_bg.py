from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass, astuple, field
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from enum import Enum
import numpy as np
import textwrap
# import random
import os
import cv2
import math
import ast
import re

# 유튜브 API 관련 라이브러리 추가
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]
@dataclass
class PatternInfo:
    info: str = ""
    id: str = ""
    variables: dict = field(default_factory=dict)
    default_variables: dict = field(default_factory=dict)


class PatternType(Enum):
    GRID = PatternInfo("Grid Matrix", "PLVeCOtK5QQz4", 
                       {
        "image_scale":0.5,
        "grid_spacing": 1000
    }, {
        "image_scale":0.5,
        "grid_spacing": 1000
    })  # 격자
    STAGGERED = PatternInfo("Staggered Pattern", "PLPZJEljNKB70", 
                       {
        "image_scale":0.5,
        "grid_spacing": 1000
    }, {
        "image_scale":0.5,
        "grid_spacing": 1000
    })  # 지그재그
    DIAGONAL = PatternInfo("Diagonal Flow", "PLPnj1KZvMBtc", 
                       {
        "image_scale":0.5,
        "grid_spacing": 1000
    }, {
        "image_scale":0.5,
        "grid_spacing": 1000
    })  # 대각선 흐름
    HONEYCOMB = PatternInfo("Honeycomb", "PLUWboFiwnsnc", 
                       {
        "image_scale":0.5,
        "grid_spacing": 1000
    }, {
        "image_scale":0.5,
        "grid_spacing": 1000
    })  # 벌집
    WAVE = PatternInfo("Wave Motion", "PLCL9N4rgiBWc", 
                       {
        "image_scale":0.5,
        "grid_spacing": 1000,
        "amplitude": 40,          # 파도타기 물결의 높낮이(진폭)
    }, {
        "image_scale":0.5,
        "grid_spacing": 1000,
        "amplitude": 40,          
    })  # 물결
    RADIAL = PatternInfo("Radial Circle", "PLVerQEPBfbug", 
                         {
        "image_scale":0.5,
        "num_circles": 6,         # 그려질 원의 총 개수
        "base_radius": 200,       # 화면 정중앙의 빈 공간(여백) 크기를 결정하는 첫 번째 원의 기본 반지름
        "radius_step": 180,       # 각 원과 원 사이의 거리 간격 (값이 클수록 원 간의 간격이 넓어짐)
        "icon_margin_ratio": 1.1  # 아이콘끼리 겹치는 것을 방지하기 위한 최소 여백 배율 계수
    }, {
        "image_scale":0.5,
        "num_circles": 6,         
        "base_radius": 200,       
        "radius_step": 180,       
        "icon_margin_ratio": 1.1  
    })  # 원형
    RADIAL_EXPANDING = PatternInfo("Hypnotic Expanding", "PLGWXb3hZm8R4", 
                        {
        "image_scale":0.5,
        "num_layers": 7,          # 방사형으로 퍼져나가는 레이어(동심원 층)의 총 개수
        "icons_per_layer": 28,    # 각 레이어당 배치되는 아이콘의 개수
        "min_radius": 120,        # 중심부 아이콘들이 너무 겹치지 않도록 지정하는 최소 시작 반지름(픽셀)
    }, {
            "image_scale":0.5,
            "num_layers": 7,         
            "icons_per_layer": 28,   
            "min_radius": 120,       
        })  # 원형 확산
    SPIRAL = PatternInfo("Vortex Spiral", "", 
                         {
        "image_scale":0.5,
        "num_arms": 6,            # 나선형 소용돌이가 뻗어 나오는 팔(Arm)의 개수
        "items_per_arm": 20,      # 하나의 팔 위에 나열되는 아이콘 개수
        "min_radius": 150,        # 소용돌이 시작점의 최소 반지름
    }, {
            "image_scale":0.5,
            "num_arms": 6,            
            "items_per_arm": 20,      
            "min_radius": 150,        
        })  # 나선형 소용돌이
    INFINITY = PatternInfo("Infinity Loop", "", 
                           {
        "image_scale":0.5,
        "num_items": 100,         # 무한대(8자) 궤도를 따라 배치되는 총 아이콘 개수
        "scale_multiplier": 0.35, # 8자 모양 전체의 크기 확대를 조절하는 배율
    }, {
            "image_scale":0.5,
            "num_items": 100,         
            "scale_multiplier": 0.35, 
        })  # 무한대 궤도
    RAINFALL = PatternInfo("Rainfall Parallax", "", 
                           {
        "image_scale":0.5,
        "num_drops": 60,          # 화면에 떨어지는 비 효과 아이콘의 총 개수
        "min_scale": 0.15,        # 원근감을 주기 위한 최소 아이콘 크기 비율
        "max_scale": 0.45,        # 원근감을 주기 위한 최대 아이콘 크기 비율
    }, {
            "image_scale":0.5,
            "num_drops": 60,          
            "min_scale": 0.15,        
            "max_scale": 0.45,        
        })  # 패럴랙스 낙하
    PENDULUM = PatternInfo("Pendulum Wave", "", 
                           {
        "image_scale":0.5,
        "rows": 15,               # 진자 운동 행(Row)의 개수
        "cols": 12,               # 진자 운동 열(Col)의 개수
        "amplitude": 50,          # 진자가 좌우로 흔들리는 폭(진폭)
    }, {
            "image_scale":0.5,
            "rows": 15,               
            "cols": 12,               
            "amplitude": 50,         
        })  # 진자 운동
    BREATHING = PatternInfo("Breathing Scatter", "", 
                            {
        "image_scale":0.5,
        "num_dots": 50,           # 무작위로 산포되는 아이콘의 총 개수
        "min_scale": 0.2,         # 숨쉬기 효과 최소 크기 비율
        "max_scale": 0.6,         # 숨쉬기 효과 최대 크기 비율
    }, {
            "image_scale":0.5,
            "num_dots": 50,          
            "min_scale": 0.2,         
            "max_scale": 0.6,         
        })  # 랜덤 산포 브리징

    PATTERN_VARIABLE_INFO = {
        "GRID": {
            "grid_spacing": "이미지 간 간격"
        },
        "STAGGERED": {
            "grid_spacing": "이미지 간 간격"
        },
        "DIAGONAL": {
            "grid_spacing": "이미지 간 간격"
        },
        "HONEYCOMB": {
            "grid_spacing": "이미지 간 간격"
        },
        "WAVE": {
            "grid_spacing": "이미지 간 간격"
        },
        "RADIAL": {
            "num_circles": "그려질 원의 총 개수",
            "base_radius": "첫 번째 원의 기본 반지름 (안쪽 빈 공간)",
            "radius_step": "원과 원 사이의 거리 간격",
            "icon_margin_ratio": "아이콘 간 최소 여백 배율"
        },
        "RADIAL_EXPANDING": {
            "num_layers": "방사형 동심원 층의 총 개수",
            "icons_per_layer": "각 레이어당 배치되는 아이콘 개수",
            "min_radius": "중심부 최소 시작 반지름"
        },
        "SPIRAL": {
            "num_arms": "나선형 소용돌이의 팔(Arm) 개수",
            "items_per_arm": "하나의 팔 위에 나열되는 아이콘 개수",
            "min_radius": "소용돌이 시작점의 최소 반지름"
        },
        "INFINITY": {
            "num_items": "무한대(8자) 궤도 총 아이콘 개수",
            "scale_multiplier": "8자 모양 전체의 크기 배율"
        },
        "RAINFALL": {
            "num_drops": "비 효과 아이콘의 총 개수",
            "min_scale": "원근감 최소 아이콘 크기 비율",
            "max_scale": "원근감 최대 아이콘 크기 비율"
        },
        "PENDULUM": {
            "rows": "진자 운동 행(Row) 개수",
            "cols": "진자 운동 열(Col) 개수",
            "amplitude": "좌우 흔들림 폭(진폭)"
        },
        "BREATHING": {
            "num_dots": "무작위 산포 아이콘의 총 개수",
            "min_scale": "숨쉬기 효과 최소 크기 비율",
            "max_scale": "숨쉬기 효과 최대 크기 비율"
        }
    }

    def get_info(self):
        return self.value.info

    def get_id(self):
        return self.value.id

    @classmethod
    def get_variable_info(cls, pattern_type):
        try:
            return cls.PATTERN_VARIABLE_INFO.value[pattern_type.name]
        except:
            print("키 에러 : ", pattern_type)


    @classmethod
    def set_grid_spacing(cls, grid_spacing):
        for p in PatternType:
            if hasattr(p.value, "grid_spacing"):
                p.value.grid_spacing = grid_spacing

    @classmethod
    def set_image_scale(cls, image_scale):
        for p in PatternType:
            if hasattr(p.value, "image_scale"):
                p.value.image_scale = image_scale

    

class ScreenSize(Enum):
    HD = (1280, 720, 250, 0.25)  # (width, height, grid_spacing, image_scale)
    FHD = (1920, 1080, 250, 0.25)
    FK = (3840, 2160, 1000, 0.5)
    # HD_SHORTS = ScreenSpec(720, 1280, 250, 0.25, 10)
    # FHD_SHORTS = ScreenSpec(1080, 1920, 250, 0.25, 10)
    # FK_SHORTS = ScreenSpec(2160, 3840, 700, 0.35, 10) # (width, height, grid_spacing, image_scale, time(s))

    def grid_spacing(self):
        return self.value[2]
    def image_scale(self):
        return self.value[3]


@dataclass
class PathInfo:
    base_dir: Path = Path(__file__).resolve().parent
    client_secret_path: Path = Path(__file__).resolve().parent.parent / "client_secret.json"
    token_path: Path = Path(__file__).resolve().parent.parent / "token.json"
    credentials = None
    img_dir: Path = Path(__file__).resolve().parent / "img"
    save_dir: Path = Path(__file__).resolve().parent / "save"
    img_path: Path = Path()
    output_path: Path = Path()
    output_filename: str = ""


    def set_output_filename(self, img_name, pattern_type, bg_color_hex):
        self.output_filename = f"{pattern_type}_{img_name}_{bg_color_hex.replace("#", "")}"

    def set_output_path(self, output_file_name):
        self.output_path = self.save_dir / output_file_name / f"{output_file_name}.mp4"
        return self.output_path

    def get_video_path(self):
        return self.output_path.with_suffix(".mp4")

    def get_thumbnail_path(self):
        return self.output_path.with_suffix(".jpg")

    def set_img_path(self, img_file_name):
        self.img_path = self.img_dir / img_file_name
        return self.img_path

    def set_img_dir(self, img_dir):
        self.img_dir = self.base_dir / img_dir
        return self.img_dir

@dataclass
class ImageSpec:
    name: str = "Icon"
    url: str = "www.flaticon.com"
    author: str = "Flaticon"


    def set(self, name, url, author):
        self.name = name
        self.url = url
        self.author = author
        subject_desc = name.replace("_", " ").title()

        Setting.YOUTUBE_METADATA.value.subject_desc = subject_desc


    
@dataclass
class ScreenSpec:
    screen_size: str = ""
    width: int = 0
    height: int = 0
    grid_spacing: int = 0
    image_scale: float = 0

    def screen(self, screen_size:ScreenSize):
        self.screen_size = screen_size.name
        self.width, self.height, self.grid_spacing, self.image_scale = screen_size.value

        if screen_size == ScreenSize.HD:
            Setting.YOUTUBE_METADATA.value.res_label = "720p HD"
        elif screen_size == ScreenSize.FHD:
            Setting.YOUTUBE_METADATA.value.res_label = "1080p FHD"
        elif screen_size == ScreenSize.FK:
            Setting.YOUTUBE_METADATA.value.res_label = "4K UHD"

        PatternType.set_grid_spacing(self.grid_spacing)
        PatternType.set_image_scale(self.image_scale)

    def horizontal(self): # 가로형
        w, h, _, _ = ScreenSize[self.screen_size].value
        self.width = max(w, h)
        self.height = min(w, h)

    def vertical(self): # 세로형
        w, h, _, _ = ScreenSize[self.screen_size].value
        self.width = min(w, h)
        self.height = max(w, h)

@dataclass
class VideoSpec:
    pattern_type: str = ""
    background_rgb: tuple = (255, 255, 255)
    background_hex: str = "#FFFFFF"
    duration: int = 0
    is_shorts: bool = False

    def spec(self, bg_color, pattern_type:PatternType):
        self.pattern_type = pattern_type.name
        Setting.YOUTUBE_METADATA.value.pattern_desc = pattern_type.get_info()
        
        hex_pattern = r"^#?([A-Fa-f0-9]{3}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$"

        if re.match(hex_pattern, str(bg_color)):
            self.background_hex = bg_color

            hex_str = hex_str.lstrip('#')
            # 3자리 축약형(#FFF)인 경우 6자리(#FFFFFF)로 확장
            if len(hex_str) == 3:
                hex_str = ''.join([c * 2 for c in hex_str])
            self.background_rgb = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

        elif (isinstance(bg_color, tuple) and 
                len(bg_color) == 3 and 
                all(isinstance(x, int) and 0 <= x <= 255 for x in bg_color)):
            self.background_rgb = bg_color
            r, g, b = bg_color
            self.background_hex = f"#{r:02x}{g:02x}{b:02x}".upper()


        color_desc = f"{self.background_hex} background"
        
        if self.background_rgb == (0, 0, 0):
            color_desc = "black background" 
        elif self.background_rgb == (255, 255, 255):
            color_desc = "white background"

        Setting.YOUTUBE_METADATA.value.color_desc = color_desc

        return self.background_hex, self.pattern_type
        

    def set_duration(self, value):
        screen_size = Setting.SCREEN.value
        if screen_size.width == 0:
            raise Exception("화면 크기 설정 먼저 한 후에 영상 길이 설정해 주세요.")

        self.duration = value
        if value < 60:
            Setting.SCREEN.value.vertical()
            self.is_shorts = True
        else:
            Setting.SCREEN.value.horizontal()
            self.is_shorts = False

        pattern_type_info = Setting.get_pattern_type().get_info()
        youtube_metadata = Setting.YOUTUBE_METADATA.value
        if len(youtube_metadata.title) == 0:
            if self.is_shorts :
                title = f"Spinning {youtube_metadata.subject_desc} {pattern_type_info} Loop #{youtube_metadata.res_label.replace(' ', '_')} #Shorts"
            else:
                title = f"Spinning {youtube_metadata.subject_desc} {pattern_type_info} Loop | {youtube_metadata.res_label.replace(' ', '_')} Visual Relaxation"
                
            Setting.YOUTUBE_METADATA.value.title = title


@dataclass
class YoutubeMetadata:
    title : str = ""
    description: str = ""
    tags: str = ""
    res_label: str = ""
    color_desc: str = ""
    pattern_desc: str = ""
    subject_desc: str = ""
    comment: str = ""


class Setting(Enum):
    PATH = PathInfo()
    SCREEN = ScreenSpec()
    IMG = ImageSpec()
    VIDEO = VideoSpec()
    YOUTUBE_METADATA = YoutubeMetadata()

    @classmethod
    def get_pattern_type(cls):
        return PatternType[cls.VIDEO.value.pattern_type]

    @classmethod
    def get_youtube_metadata(cls):
        return cls.YOUTUBE_METADATA.value





def generate_youtube_metadata():
    img_name, img_url, img_author = astuple(Setting.IMG.value)
    pattern_type, background_rgb, background_hex, duration, is_shorts = astuple(Setting.VIDEO.value)
    _, _, _, res_label, color_desc, pattern_desc, subject_desc, _ = astuple(Setting.get_youtube_metadata())
    pattern_type = pattern_type.replace("_", " ").title().replace(" ", "")
    pattern_type_info = Setting.get_pattern_type().get_info()

    description = f"""A mesmerizing and hypnotic loop video featuring a {pattern_type_info} pattern of rotating {subject_desc.lower()} icons. 

Designed for minimalist aesthetics and visual relaxation, this hypnotic pattern makes the perfect background ambiance for your focus sessions, study time, or a quiet moment of calm.

🎯 Video Details
• Style: Minimalist & Kitsch Motion Loop
• Subject: {pattern_desc} Pattern of Rotating {subject_desc} Icons
• Use: Focus background, study ambiance, digital wallpaper, visual rest

#MinimalistAesthetic #LoopVideo #VisualRelaxation #MotionGraphics #SatisfyingLoops #AmbientVideo #FocusBackground #HypnoticPattern #{img_name} #{pattern_type} #{duration}s

--------------------------------------------------
[Backgound color]
RGB: rgb{background_rgb}
HEX: {background_hex}

[Image Sources]
{img_name.title()} ICON URL Path: {img_url}
(Author: {img_author})
"""
    Setting.YOUTUBE_METADATA.value.description = description
    tags = f"{img_name}, {pattern_type}, {pattern_type_info.replace(" ", "")} loop, spinning animation, {res_label}, minimalist animation, motion graphics, visual relaxation, satisfying loops, loop video, focus background, study ambiance, visual hypnosis, hypnotic loop, kinetic pattern, 루프비디오, 미니멀아트, 모션그래픽, bg_color, rgb{str(background_rgb).replace(",", "")}, {background_hex}, {duration}s"

    if is_shorts:
        tags += ", shorts"

    Setting.YOUTUBE_METADATA.value.tags = tags

def add_thumbnail_text():
    """썸네일 이미지에 유튜브 스타일의 굵고 시인성 높은 텍스트를 합성하는 함수 (자동 줄바꿈 지원)"""
    thumbnail_path = Setting.PATH.value.get_thumbnail_path()
    title_text = Setting.YOUTUBE_METADATA.value.title
    img = Image.open(thumbnail_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    width, height = img.size
    
    # 폰트 설정 (윈도우 기본 굵은 폰트인 맑은 고딕 볼드 사용, 크기는 4K/FHD 해상도에 맞춰 조절)
    try:
        font_size = int(height * 0.07)  # 화면 높이의 약 7% 크기 (여러 줄 배치를 위해 약간 조정)
        font = ImageFont.truetype("impact.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # ★ [핵심 추가] 텍스트가 이미지를 넘어가지 않도록 자동 줄바꿈 처리
    # 썸네일 전체 너비의 85%를 최대 텍스트 박스 너비로 설정
    max_text_width = width * 0.85
    
    # 글자 1글자당 평균 너비를 대략적으로 추정하여 한 줄에 들어갈 글자 수 계산
    # 정확한 계산을 위해 draw.textlength를 활용한 wrapper 로직 구현
    avg_char_width = font.getbbox("A")[2] if hasattr(font, "getbbox") else font_size * 0.5
    approx_chars_per_line = int(max_text_width / avg_char_width)
    
    # textwrap.wrap을 사용해 길어진 제목을 여러 줄의 리스트로 분할
    wrapped_lines = textwrap.wrap(title_text, width=approx_chars_per_line)
    
    # 줄바꿈된 텍스트 전체의 높이와 최대 너비 재계산
    line_spacing = int(font_size * 0.2)  # 줄 간 간격
    total_text_height = 0
    line_bboxes = []
    
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        l_width = bbox[2] - bbox[0]
        l_height = bbox[3] - bbox[1]
        line_bboxes.append((line, l_width, l_height))
        total_text_height += l_height + line_spacing
        
    total_text_height -= line_spacing  # 마지막 줄의 여백 제거

    # 시작 y 좌표 계산 (중앙 하단 배치 기준)
    start_y = int(height * 0.70) - (total_text_height // 2)
    
    current_y = start_y
    for line, l_width, l_height in line_bboxes:
        # 각 줄별로 가운데 정렬(x 좌표) 계산
        x = (width - l_width) // 2
        
        # 유튜브 스타일 외곽선(Stroke) 효과 주기 (검은색 테두리)
        stroke_width = max(3, int(font_size * 0.04))
        for adj_x in range(-stroke_width, stroke_width + 1):
            for adj_y in range(-stroke_width, stroke_width + 1):
                if adj_x != 0 or adj_y != 0:
                    draw.text((x + adj_x, current_y + adj_y), line, font=font, fill="black")

        # 메인 텍스트 그리기 (노란색)
        draw.text((x, current_y), line, font=font, fill=(255, 230, 0))
        
        current_y += l_height + line_spacing

    # RGB로 변환 후 덮어쓰기 저장
    final_img = img.convert("RGB")
    final_img.save(thumbnail_path, "JPEG", quality=95)
    print(f"유튜브 스타일 썸네일 텍스트 합성 완료 (자동 줄바꿈 적용)")


def upload_video_to_youtube():
    """생성된 영상과 썸네일을 유튜브에 자동 업로드하는 함수"""
    print("\n유튜브 인증 및 업로드를 시작합니다...")

    video_path = Setting.PATH.value.get_video_path()
    thumbnail_path = Setting.PATH.value.get_thumbnail_path()

    # 최초 실행 시 브라우저 창이 뜨며 구글 계정 로그인 및 권한 허용을 진행합니다.
    client_secret_path = Setting.PATH.value.client_secret_path
    token_path = Setting.PATH.value.token_path
    credentials = None

    # 이미 저장된 토큰 파일이 있다면 불러옴
    if os.path.exists(token_path):
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # 토큰이 없거나 만료된 경우 새로 로그인 진행
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            credentials = flow.run_local_server(port=0)
        
        # 새로 발급받은 인증 정보를 token.json 파일로 저장
        with open(token_path, "w") as token:
            token.write(credentials.to_json())

    youtube = build("youtube", "v3", credentials=credentials)


    title = Setting.YOUTUBE_METADATA.value.title
    description = Setting.YOUTUBE_METADATA.value.description
    tags = Setting.YOUTUBE_METADATA.value.tags

    body = {
        "snippet": {
            "title": title,                          
            "description": description,
            "tags": [tag.strip() for tag in tags.split(",")],
            "categoryId": "1",  # 1: Film & Animation, 24: Entertainment, 26 Howto & Style
            "defaultLanguage": "en",          # 메타데이터 언어 (영어)
            "defaultAudioLanguage": "en"      # 오디오/콘텐츠 언어 (영어)
        },
        "status": {
            "privacyStatus": "unlisted",  # 안전하게 '비공개'로 업로드 후 검토 추천 ('public'으로 바꾸면 즉시 공개)
            "selfDeclaredMadeForKids": False
        }
    }

    media_video = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)

    print("유튜브 영상 전송 중...")
    insert_request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_video
    )

    response = None
    while response is None:
        status, response = insert_request.next_chunk()
        if status:
            print(f"업로드 진행률: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    print(f"업로드 성공! 영상 ID: {video_id}")

    # # 썸네일 업로드 연동
    # if thumbnail_path and Path(thumbnail_path).exists():
    #     print("썸네일 이미지 적용 중...")
    #     youtube.thumbnails().set(
    #         videoId=video_id,
    #         media_body=MediaFileUpload(str(thumbnail_path))
    #     )
    #     print("썸네일 설정 완료!")

    # 1. 패턴 이름(pattern_type)에 맞는 재생목록에 자동 추가 기능
    # (주의: 사전에 유튜브 스튜디오에서 해당 이름의 재생목록을 만들어 두고 playlist_id를 매핑해야 합니다)
    try:
        target_playlist_id = Setting.get_pattern_type().get_id()
        if target_playlist_id:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": target_playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            ).execute()
            print(f"[{Setting.get_pattern_type().name}] 재생목록에 영상 추가 완료!")
    except Exception as e:
        print(f"⚠️ 재생목록 추가 중 오류 발생 (플레이리스트 ID를 확인하세요): {e}")

    # 2. 댓글 자동 작성 기능
    try:
        comment_text = Setting.YOUTUBE_METADATA.value.comment
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
        ).execute()
        print("유튜브 고정 댓글 작성 완료!")
    except Exception as e:
        print(f"⚠️ 댓글 작성 중 오류 발생: {e}")


def show_interactive_preview(
    bg_color=(242, 235, 245),
    pattern_type=PatternType.STAGGERED,
    screen_size = ScreenSize.FK
):
    """
    미리보기를 띄운 뒤, 키보드 입력으로 확정(Enter)하면 
    곧바로 영상 생성, 메타데이터 생성, 유튜브 업로드까지 연달아 실행합니다.
    """
    width, height, grid_spacing, image_scale = screen_size.value
    image_path = Setting.PATH.value.img_path

    while True:
        print(f"\n[미리보기] 현재 설정값 ➔ 스케일: {image_scale}, 그리드 간격: {grid_spacing}")
        
        # 1. 이미지 처리 및 미리보기 생성 로직
        source_img = Image.open(image_path).convert("RGBA")
        new_size = (int(source_img.width * image_scale), int(source_img.height * image_scale))
        resized_img = source_img.resize(new_size, Image.Resampling.LANCZOS)
        
        rotated_img = resized_img.rotate(0, expand=True, resample=Image.Resampling.BICUBIC)
        bg = Image.new("RGB", (width, height), bg_color)

        max_radius = math.hypot(width, height) / 2
        num_layers = 8
        patternInfo = pattern_type.value

        # 패턴 배치 로직
        if pattern_type == PatternType.RADIAL_EXPANDING: 
            center_x, center_y = width // 2, height // 2
            num_layers = patternInfo.variables.get("num_layers", 7)
            icons_per_layer = patternInfo.variables.get("icons_per_layer", 28)
            min_radius = patternInfo.variables.get("min_radius", 120)
            
            for layer in range(num_layers):
                # 중심에서부터 층별로 확실하게 퍼져나가는 거리 계산
                current_layer_radius = min_radius + (layer * (max_radius - min_radius) / num_layers)
                scale_factor = 0.3 + (current_layer_radius / max_radius) * 0.7
                
                scaled_w = int(rotated_img.width * scale_factor)
                scaled_h = int(rotated_img.height * scale_factor)
                zoomed_img = rotated_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS) if scaled_w > 0 and scaled_h > 0 else rotated_img

                for i in range(icons_per_layer):
                    theta = (2 * math.pi / icons_per_layer) * i
                    px = center_x + current_layer_radius * math.cos(theta) - zoomed_img.width // 2
                    py = center_y + current_layer_radius * math.sin(theta) - zoomed_img.height // 2
                    bg.paste(zoomed_img, (int(px), int(py)), zoomed_img)

        elif pattern_type == PatternType.RADIAL:
            center_x, center_y = width // 2, height // 2
            num_circles = patternInfo.variables.get("num_circles", 6)
            base_radius = patternInfo.variables.get("base_radius", 200)
            radius_step = patternInfo.variables.get("radius_step", 180)
            margin_ratio = patternInfo.variables.get("icon_margin_ratio", 1.1)
             
            for r in range(1, num_circles + 1):
                radius = base_radius + (r * radius_step)
                
                # 원의 둘레(2 * pi * r)와 아이콘 크기를 고려하여 겹치지 않게 개수 자동 비례 혹은 수동 조절
                items_in_circle = int(2 * math.pi * radius / (rotated_img.width * margin_ratio)) # 1.1은 아이콘 간 최소 여백 비율
                
                for i in range(items_in_circle):
                    theta = (2 * math.pi / items_in_circle) * i
                    px = center_x + radius * math.cos(theta) - rotated_img.width // 2
                    py = center_y + radius * math.sin(theta) - rotated_img.height // 2
                    bg.paste(rotated_img, (int(px), int(py)), rotated_img)

        elif pattern_type == PatternType.SPIRAL:
            # 🌀 Vortex Spiral: 화면 정중앙을 명확한 중심점으로 지정하고 바깥으로 뻗어나감
            center_x, center_y = width // 2, height // 2
            num_arms = patternInfo.variables.get("num_arms", 6)
            items_per_arm = patternInfo.variables.get("items_per_arm", 20)
            min_radius = patternInfo.variables.get("min_radius", 150)
            
            for arm in range(num_arms):
                arm_base_angle = (2 * math.pi / num_arms) * arm
                for i in range(items_per_arm):
                    t = (i + 1) / items_per_arm
                    # 최소 반지름부터 최대 화면 거리까지 비례해서 뻗어나감
                    radius = min_radius + t * (max_radius - min_radius)
                    theta = arm_base_angle + (t * 3 * math.pi)
                    
                    px = center_x + radius * math.cos(theta) - rotated_img.width // 2
                    py = center_y + radius * math.sin(theta) - rotated_img.height // 2
                    bg.paste(rotated_img, (int(px), int(py)), rotated_img)

        elif pattern_type == PatternType.INFINITY:
            # ∞ Infinity Loop: 베르누이의 LEMNISCATE(8자 무한대) 매개변수 방정식 활용
            num_items = patternInfo.variables.get("num_items", 100)
            scale_factor_inf = min(width, height) * patternInfo.variables.get("scale_multiplier", 0.35)
            for i in range(num_items):
                t = (2 * math.pi * i) / num_items
                # 8자 곡선 공식
                denominator = 1 + math.sin(t)**2
                px = width // 2 + int((scale_factor_inf * math.cos(t)) / denominator) - rotated_img.width // 2
                py = height // 2 + int((scale_factor_inf * math.sin(t) * math.cos(t)) / denominator) - rotated_img.height // 2
                bg.paste(rotated_img, (px, py), rotated_img)

        elif pattern_type == PatternType.RAINFALL:
            # 🌧️ Rainfall Parallax: 크고 빠른 앞쪽 레이어와 작고 느린 뒤쪽 레이어 연출
            num_drops = patternInfo.variables.get("num_drops", 60)
            min_s = patternInfo.variables.get("min_scale", 0.15)
            max_s = patternInfo.variables.get("max_scale", 0.45)

            for i in range(num_drops):
                # 의사 난수(Pseudo-random) 형태로 위치 고정 분산
                np.random.seed(i * 42)
                rx = int(np.random.uniform(0, width))
                ry = int(np.random.uniform(0, height))
                scale_p = np.random.uniform(min_s, max_s)  # 원근감에 따른 크기 차등
                
                drop_w = int(source_img.width * scale_p)
                drop_h = int(source_img.height * scale_p)
                if drop_w > 0 and drop_h > 0:
                    scaled_drop = source_img.resize((drop_w, drop_h), Image.Resampling.LANCZOS)
                    bg.paste(scaled_drop, (rx - drop_w // 2, ry - drop_h // 2), scaled_drop)

        elif pattern_type == PatternType.PENDULUM:
            # ⏳ Pendulum Wave: 행별로 진폭이 달라지는 좌우 교차 진자 구조
            rows = patternInfo.variables.get("rows", 15)
            cols = patternInfo.variables.get("cols", 12)
            amplitude = patternInfo.variables.get("amplitude", 50)
            row_spacing_p = height // (rows + 1)
            col_spacing_p = width // (cols + 1)
            for r in range(rows):
                # 행마다 미세하게 오프셋을 주어 웨이브 진자 느낌 배가
                offset_p = int(math.sin(r * 0.5) * amplitude)
                for c in range(cols):
                    px = col_spacing_p * (c + 1) + offset_p - rotated_img.width // 2
                    py = row_spacing_p * (r + 1) - rotated_img.height // 2
                    bg.paste(rotated_img, (px, py), rotated_img)

        elif pattern_type == PatternType.BREATHING:
            # 🫁 Breathing Scatter: 무작위 산포 상태에서 크기만 다양하게 배치
            num_dots = patternInfo.variables.get("num_dots", 50)
            min_s = patternInfo.variables.get("min_scale", 0.2)
            max_s = patternInfo.variables.get("max_scale", 0.6)

            # 최소 크기와 최대 크기의 중간값(Center)과 진폭(Amplitude) 계산
            scale_center = (min_s + max_s) / 2
            scale_amplitude = (max_s - min_s) / 2
            for i in range(num_dots):
                np.random.seed(i * 99)
                bx = int(np.random.uniform(50, width - 50))
                by = int(np.random.uniform(50, height - 50))
                b_scale = scale_center + scale_amplitude * math.sin(i)
                
                b_w = int(source_img.width * b_scale)
                b_h = int(source_img.height * b_scale)
                if b_w > 0 and b_h > 0:
                    b_img = source_img.resize((b_w, b_h), Image.Resampling.LANCZOS)
                    bg.paste(b_img, (bx - b_w // 2, by - b_h // 2), b_img)
        
        # else:
        #     start_x = -grid_spacing * 2
        #     start_y = -grid_spacing
        #     end_x = width + grid_spacing * 2
        #     end_y = height + grid_spacing
        #     actual_spacing_y = int(grid_spacing * 0.866) if pattern_type == PatternType.HONEYCOMB else grid_spacing

        #     row_idx = 0
        #     y = start_y
        #     while y < end_y:
        #         offset_x = 0  # PatternType.GRID 세팅
        #         offset_y = 0
        #         if pattern_type == PatternType.STAGGERED and (row_idx % 2 != 0):
        #             offset_x = grid_spacing // 2
        #         elif pattern_type == PatternType.DIAGONAL:
        #             offset_x = (row_idx * (grid_spacing // 3)) % grid_spacing
        #         elif pattern_type == PatternType.HONEYCOMB and (row_idx % 2 != 0):
        #             offset_x = grid_spacing // 2
                
        #         x = start_x + offset_x
        #         while x < end_x:
        #             paste_x = x + (grid_spacing - rotated_img.width) // 2
        #             paste_y = y + (actual_spacing_y - rotated_img.height) // 2

        #             offset_y = 0
        #             if pattern_type == PatternType.WAVE:
        #                 wave_amp = patternInfo.variables.get("amplitude", 40)
        #                 offset_y = math.sin(x / grid_spacing) * wave_amp
                        
        #             bg.paste(rotated_img, (int(paste_x), int(paste_y + offset_y)), rotated_img)
        #             x += grid_spacing

        #         y += actual_spacing_y
        #         row_idx += 1
        else:
            start_x = -grid_spacing * 2
            start_y = -grid_spacing
            end_x = width + grid_spacing * 2
            end_y = height + grid_spacing
            
            # HONEYCOMB인 경우에만 0.866 세로 간격 적용, 나머지는 기본 grid_spacing 사용
            actual_spacing_y = int(grid_spacing * 0.866) if pattern_type == PatternType.HONEYCOMB else grid_spacing

            row_idx = 0
            y = start_y
            while y < end_y:
                offset_x = 0  
                offset_y = 0
                
                # ★ [수정] STAGGERED, HONEYCOMB뿐만 아니라 WAVE 패턴도 홀수 행에 가로 교차 오프셋 적용
                if (pattern_type == PatternType.STAGGERED or pattern_type == PatternType.HONEYCOMB or pattern_type == PatternType.WAVE) and (row_idx % 2 != 0):
                    offset_x = grid_spacing // 2
                elif pattern_type == PatternType.DIAGONAL:
                    offset_x = (row_idx * (grid_spacing // 3)) % grid_spacing
                
                x = start_x + offset_x
                while x < end_x:
                    paste_x = x + (grid_spacing - rotated_img.width) // 2
                    paste_y = y + (actual_spacing_y - rotated_img.height) // 2

                    # WAVE 패턴인 경우 기존대로 엇갈린 상태에서 수직 파도타기 오프셋 추가
                    if pattern_type == PatternType.WAVE:
                        wave_amp = patternInfo.variables.get("amplitude", 40)
                        # 미리보기 함수에서는 current_time 대신 x 좌표 기준, 동영상 함수에서는 current_time + x 좌표 기준 사용
                        # (예시: 동영상 함수 기준)
                        offset_y = math.sin((x / grid_spacing)) * wave_amp
                        
                    bg.paste(rotated_img, (int(paste_x), int(paste_y + offset_y)), rotated_img)
                    x += grid_spacing

                y += actual_spacing_y
                row_idx += 1

        # 화면에 띄우기
        preview_cv = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
        window_title = "Pattern Preview (Enter: Proceed | R: Modify | Esc: Exit)"
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 1280, 720)
        cv2.imshow(window_title, preview_cv)
        
        print("\5n[조작 안내]")
        print(" • [Enter] 또는 [Space] : 마음에 듦! 👉 곧바로 영상 제작 및 업로드 진행")
        print(" • [1] 키 : 수정 필요! 👉 이미지 스케일을 다시 입력")
        print(" • [2] 키 : 수정 필요! 👉 배경 색을 다시 입력")
        print(" • [3] 키 : 수정 필요! 👉 패턴을 다시 입력")
        v_info_dict = PatternType.get_variable_info(pattern_type)
        sorted_key = sorted(v_info_dict.keys())
        for i, key in enumerate(sorted_key):
            print(f" • [{i + 4}] 키 : 수정 필요! 👉 {v_info_dict[key]}(을)를 다시 입력")
        print(" • [ESC] 키 : 🏃‍♂️ 프로그램 종료")

        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()

        # 2. 키 입력 분기 처리
        # if True:
        if key == 13 or key == 32:  # Enter 또는 Space
            print("\n✨ 설정 확정! 다음 단계를 진행합니다.")
            pattern_type, bg_color_hex = Setting.VIDEO.value.spec(bg_color, pattern_type)
            Setting.SCREEN.value.screen(screen_size)
            img_name = image_path.stem
            Setting.PATH.value.set_output_filename(img_name, pattern_type, bg_color_hex)
            break

        elif key == ord('1'):
            print("\n--- 값을 새로 조정합니다 ---")
            try:
                new_scale_input = input(f"새로운 이미지 스케일 입력 (현재: {image_scale}, 기본값: {screen_size.image_scale()}): ").strip()
                if new_scale_input:
                    image_scale = float(new_scale_input)
            except ValueError:
                print("⚠️ 잘못된 입력입니다. 숫자로 입력해 주세요. 이전 값으로 유지합니다.")

        elif key == ord('2'):
            print("\n--- 값을 새로 조정합니다 ---")
            try:
                new_bg_color_input = input(f"새로운 배경색 입력 (현재: {bg_color}): ").strip()
                if new_bg_color_input:
                    bg_color = ast.literal_eval(new_bg_color_input)
            except ValueError:
                print("⚠️ 잘못된 입력입니다. 숫자로 입력해 주세요. 이전 값으로 유지합니다.")
        elif key == ord('3'):
            print("\n--- 값을 새로 조정합니다 ---")
            try:
                new_pattern_type_input = input(f"새로운 패턴 입력 (현재: {pattern_type.name}/ 입력 가능 목록: {[p.name for p in PatternType]}): ").strip().upper().replace(" ", "_")
                if new_pattern_type_input:
                    pattern_type = PatternType[new_pattern_type_input]
            except ValueError:
                print("⚠️ 잘못된 입력입니다. 문자로 입력해 주세요. 이전 값으로 유지합니다.")
        elif key == 27:  # ESC 키
            print("프로그램을 종료합니다.")
            break
        else:
            for i, v_info_key in enumerate(sorted_key):
                if key == ord(f'{i + 4}'):
                    print("\n--- 값을 새로 조정합니다 ---")
                    try:          
                        cur_value = pattern_type.value.variables.get(v_info_key)
                        default_value = pattern_type.value.default_variables.get(v_info_key)      
                        new_variable_input = input(f"새로운 {v_info_dict[v_info_key]} 입력 (현재: {cur_value}, 기본값: {default_value}): ").strip()
                        if new_variable_input:
                            if isinstance(default_value, float):
                                pattern_type.value.variables[v_info_key] = float(new_variable_input)
                            else:
                                pattern_type.value.variables[v_info_key] = int(new_variable_input)
                    except ValueError:
                        print("⚠️ 잘못된 입력입니다. 숫자로 입력해 주세요. 이전 값으로 유지합니다.")
                    break

            print("잘못된 입력입니다. [Enter]를 누르면 진행, [R]을 누르면 수정할 수 있습니다.")



def create_rotating_pattern_video(
    duration_seconds=60,
    rotation_speed=0.2,
    fps=30
):

    Setting.VIDEO.value.set_duration(duration_seconds)
    _, width, height, grid_spacing, image_scale = astuple(Setting.SCREEN.value)
    pattern_type, bg_color, _, _, _ = astuple(Setting.VIDEO.value)
    total_frames = duration_seconds * fps
    
    output_filename = Setting.PATH.value.output_filename
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    output_filename = f"{output_filename}_{duration_seconds}s_{timestamp}"
    video_path = Setting.PATH.value.set_output_path(output_filename)
    
    video_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 윈도우 환경에서 가장 안정적인 mp4v 코덱으로 고정
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
    
    if not video_writer.isOpened():
        print("에러: VideoWriter 초기화에 실패했습니다.")
    else:
        print("비디오 Writer가 성공적으로 초기화되었습니다.")

    image_path = Setting.PATH.value.img_path
    source_img = Image.open(image_path).convert("RGBA")
    new_size = (int(source_img.width * image_scale), int(source_img.height * image_scale))
    # 원본 품질 유지를 위한 LANCZOS 리사이징 (유지)
    resized_img = source_img.resize(new_size, Image.Resampling.LANCZOS)

    pattern_type = PatternType[pattern_type]
    print(f"총 {duration_seconds}초 ({total_frames} 프레임) [{pattern_type.name}] 패턴 영상 생성 시작 (FHD)...")

    max_radius = math.hypot(width, height) / 2
    expansion_speed = max_radius / duration_seconds
    num_layers = 8
    thumbnail_path = None
    thumbnail_saved = False

    for frame_idx in tqdm(range(total_frames), desc="영상 렌더링 중"):
        current_time = frame_idx / fps
        if pattern_type == PatternType.WAVE:
            angle = 0  # WAVE 패턴일 때는 아이콘이 회전하지 않도록 각도를 0으로 설정합니다.
        else:
            angle = current_time * rotation_speed * 360

        # ★핵심 수정: resample=Image.Resampling.BICUBIC 추가
        # 회전 시 픽셀이 뭉개지는 것을 방지하고 부드럽게 처리합니다.
        rotated_img = resized_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        
        bg = Image.new("RGB", (width, height), bg_color)
        patternInfo = pattern_type.value

        if pattern_type == PatternType.RADIAL_EXPANDING :
            center_x, center_y = width // 2, height // 2
            num_layers = patternInfo.variables.get("num_layers", 7)
            icons_per_layer = patternInfo.variables.get("icons_per_layer", 28)
            min_radius = patternInfo.variables.get("min_radius", 120)
            
            for layer in range(num_layers):
                # 시간에 따라 반지름이 계속 퍼져나가도록 순환 구조 적용
                current_layer_radius = min_radius + ((expansion_speed * current_time + (layer * (max_radius - min_radius) / num_layers)) % (max_radius - min_radius))
                scale_factor = 0.3 + (current_layer_radius / max_radius) * 0.7
                
                scaled_w = int(rotated_img.width * scale_factor)
                scaled_h = int(rotated_img.height * scale_factor)
                zoomed_img = rotated_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS) if scaled_w > 0 and scaled_h > 0 else rotated_img

                for i in range(icons_per_layer):
                    theta = (2 * math.pi / icons_per_layer) * i + (current_time * 0.2 * (layer % 2 * 2 - 1))
                    px = center_x + current_layer_radius * math.cos(theta) - zoomed_img.width // 2
                    py = center_y + current_layer_radius * math.sin(theta) - zoomed_img.height // 2
                    bg.paste(zoomed_img, (int(px), int(py)), zoomed_img)

        elif pattern_type == PatternType.RADIAL:
            center_x, center_y = width // 2, height // 2
            num_circles = patternInfo.variables.get("num_circles", 6)
            base_radius = patternInfo.variables.get("base_radius", 200)
            radius_step = patternInfo.variables.get("radius_step", 180)
            margin_ratio = patternInfo.variables.get("icon_margin_ratio", 1.1)
            
            for r in range(1, num_circles + 1):
                radius = base_radius + (r * radius_step)
                
                # 원의 둘레(2 * pi * r)와 아이콘 크기를 고려하여 겹치지 않게 개수 자동 비례 혹은 수동 조절
                items_in_circle = int(2 * math.pi * radius / (rotated_img.width * margin_ratio)) # 1.1은 아이콘 간 최소 여백 비율
                
                for i in range(items_in_circle):
                    theta = (2 * math.pi / items_in_circle) * i + (current_time * 0.3 * (r % 2 * 2 - 1))
                    px = center_x + radius * math.cos(theta) - rotated_img.width // 2
                    py = center_y + radius * math.sin(theta) - rotated_img.height // 2
                    bg.paste(rotated_img, (int(px), int(py)), rotated_img)

        elif pattern_type == PatternType.SPIRAL:
            center_x, center_y = width // 2, height // 2
            num_arms = patternInfo.variables.get("num_arms", 6)
            items_per_arm = patternInfo.variables.get("items_per_arm", 20)
            min_radius = patternInfo.variables.get("min_radius", 150)
            
            for arm in range(num_arms):
                arm_base_angle = (2 * math.pi / num_arms) * arm
                for i in range(items_per_arm):
                    t = (i + 1) / items_per_arm
                    radius = min_radius + t * (max_radius - min_radius)
                    # 시간에 따라 회전하며 바깥으로 뻗어 나오는 모션 부여
                    theta = arm_base_angle + (t * 3 * math.pi) + (current_time * 0.6)
                    
                    px = center_x + radius * math.cos(theta) - rotated_img.width // 2
                    py = center_y + radius * math.sin(theta) - rotated_img.height // 2
                    bg.paste(rotated_img, (int(px), int(py)), rotated_img)

        elif pattern_type == PatternType.INFINITY:
            num_items = patternInfo.variables.get("num_items", 100)
            scale_factor_inf = min(width, height) * patternInfo.variables.get("scale_multiplier", 0.35)
            for i in range(num_items):
                # 시간에 따라 t값을 밀어주어 8자 궤도를 따라 아이콘이 순환하도록 함
                t = (2 * math.pi * i) / num_items + (current_time * 1.5)
                denominator = 1 + math.sin(t)**2
                px = width // 2 + int((scale_factor_inf * math.cos(t)) / denominator) - rotated_img.width // 2
                py = height // 2 + int((scale_factor_inf * math.sin(t) * math.cos(t)) / denominator) - rotated_img.height // 2
                bg.paste(rotated_img, (px, py), rotated_img)

        elif pattern_type == PatternType.RAINFALL:
            num_drops = patternInfo.variables.get("num_drops", 60)
            min_s = patternInfo.variables.get("min_scale", 0.15)
            max_s = patternInfo.variables.get("max_scale", 0.45)
            for i in range(num_drops):
                np.random.seed(i * 42)
                rx = int(np.random.uniform(0, width))
                base_y = np.random.uniform(0, height)
                speed = np.random.uniform(100, 400)  # 낙하 속도
                
                # 시간에 따라 아래로 흐르며 화면 끝에 도달하면 위로 순환
                ry = int((base_y + current_time * speed) % height)
                scale_p = np.random.uniform(min_s, max_s)
                
                drop_w = int(source_img.width * scale_p)
                drop_h = int(source_img.height * scale_p)
                if drop_w > 0 and drop_h > 0:
                    scaled_drop = source_img.resize((drop_w, drop_h), Image.Resampling.LANCZOS)
                    bg.paste(scaled_drop, (rx - drop_w // 2, ry - drop_h // 2), scaled_drop)

        elif pattern_type == PatternType.PENDULUM:
            rows = patternInfo.variables.get("rows", 15)
            cols = patternInfo.variables.get("cols", 12)
            amplitude = patternInfo.variables.get("amplitude", 50)
            row_spacing_p = height // (rows + 1)
            col_spacing_p = width // (cols + 1)
            for r in range(rows):
                # 진자처럼 시간에 따라 좌우로 왕복 운동하는 오프셋 부여
                offset_p = int(math.sin(current_time * 3 + (r * 0.5)) * amplitude)
                for c in range(cols):
                    px = col_spacing_p * (c + 1) + offset_p - rotated_img.width // 2
                    py = row_spacing_p * (r + 1) - rotated_img.height // 2
                    bg.paste(rotated_img, (px, py), rotated_img)

        elif pattern_type == PatternType.BREATHING:
            num_dots = patternInfo.variables.get("num_dots", 50)
            min_s = patternInfo.variables.get("min_scale", 0.2)
            max_s = patternInfo.variables.get("max_scale", 0.6)

            scale_center = (min_s + max_s) / 2
            scale_amplitude = (max_s - min_s) / 2
            for i in range(num_dots):
                np.random.seed(i * 99)
                bx = int(np.random.uniform(50, width - 50))
                by = int(np.random.uniform(50, height - 50))
                
                # 시간에 따라 크기가 주기적으로 커졌다 작아지는 숨쉬기 효과 (Sine 함수 이용)
                b_scale = scale_center + scale_amplitude * math.sin(current_time * 2 + i)
                
                b_w = int(source_img.width * b_scale)
                b_h = int(source_img.height * b_scale)
                if b_w > 0 and b_h > 0:
                    b_img = source_img.resize((b_w, b_h), Image.Resampling.LANCZOS)
                    bg.paste(b_img, (bx - b_w // 2, by - b_h // 2), b_img)

        # else:
        #     start_x = -grid_spacing * 2
        #     start_y = -grid_spacing
        #     end_x = width + grid_spacing * 2
        #     end_y = height + grid_spacing
        #     actual_spacing_y = int(grid_spacing * 0.866) if pattern_type == PatternType.HONEYCOMB else grid_spacing

        #     row_idx = 0
        #     y = start_y
        #     while y < end_y:
        #         offset_x = 0
        #         offset_y = 0
        #         if pattern_type == PatternType.STAGGERED and (row_idx % 2 != 0):
        #             offset_x = grid_spacing // 2
        #         elif pattern_type == PatternType.DIAGONAL:
        #             offset_x = (row_idx * (grid_spacing // 3)) % grid_spacing
        #         elif pattern_type == PatternType.HONEYCOMB and (row_idx % 2 != 0):
        #             offset_x = grid_spacing // 2

        #         x = start_x + offset_x
        #         while x < end_x:
        #             paste_x = x + (grid_spacing - rotated_img.width) // 2
        #             paste_y = y + (actual_spacing_y - rotated_img.height) // 2

        #             offset_y = 0
        #             if pattern_type == PatternType.WAVE:
        #                 wave_amp = patternInfo.variables.get("amplitude", 40)
        #                 offset_y = math.sin(current_time * 4 + (x / grid_spacing)) * wave_amp

        #             bg.paste(rotated_img, (int(paste_x), int(paste_y + offset_y)), rotated_img)
        #             x += grid_spacing

        #         y += actual_spacing_y
        #         row_idx += 1
        else:
            start_x = -grid_spacing * 2
            start_y = -grid_spacing
            end_x = width + grid_spacing * 2
            end_y = height + grid_spacing
            
            # HONEYCOMB인 경우에만 0.866 세로 간격 적용, 나머지는 기본 grid_spacing 사용
            actual_spacing_y = int(grid_spacing * 0.866) if pattern_type == PatternType.HONEYCOMB else grid_spacing

            row_idx = 0
            y = start_y
            while y < end_y:
                offset_x = 0  
                offset_y = 0
                
                # ★ [수정] STAGGERED, HONEYCOMB뿐만 아니라 WAVE 패턴도 홀수 행에 가로 교차 오프셋 적용
                if (pattern_type == PatternType.STAGGERED or pattern_type == PatternType.HONEYCOMB or pattern_type == PatternType.WAVE) and (row_idx % 2 != 0):
                    offset_x = grid_spacing // 2
                elif pattern_type == PatternType.DIAGONAL:
                    offset_x = (row_idx * (grid_spacing // 3)) % grid_spacing
                
                x = start_x + offset_x
                while x < end_x:
                    paste_x = x + (grid_spacing - rotated_img.width) // 2
                    paste_y = y + (actual_spacing_y - rotated_img.height) // 2

                    # WAVE 패턴인 경우 기존대로 엇갈린 상태에서 수직 파도타기 오프셋 추가
                    if pattern_type == PatternType.WAVE:
                        wave_amp = patternInfo.variables.get("amplitude", 40)
                        # 미리보기 함수에서는 current_time 대신 x 좌표 기준, 동영상 함수에서는 current_time + x 좌표 기준 사용
                        # (예시: 동영상 함수 기준)
                        offset_y = math.sin(current_time * 4 + (x / grid_spacing)) * wave_amp
                        
                    bg.paste(rotated_img, (int(paste_x), int(paste_y + offset_y)), rotated_img)
                    x += grid_spacing

                y += actual_spacing_y
                row_idx += 1

        # if not thumbnail_saved:
        #     thumbnail_path = Setting.PATH.value.get_thumbnail_path()
        #     bg.save(thumbnail_path, "JPEG")
            
        #     # 폰트 크기 조절을 위한 배율 변수 (기본값 0.07)
        #     font_scale_ratio = 0.07 
            
        #     # 폰트 크기 반영 함수를 포함한 내부 로직
        #     def render_thumbnail_with_custom_font():
        #         img = Image.open(thumbnail_path).convert("RGBA")
        #         draw = ImageDraw.Draw(img)
        #         width, height = img.size
                
        #         try:
        #             font_size = int(height * font_scale_ratio)
        #             font = ImageFont.truetype("impact.ttf", font_size)
        #         except IOError:
        #             font = ImageFont.load_default()

        #         max_text_width = width * 0.85
        #         avg_char_width = font.getbbox("A")[2] if hasattr(font, "getbbox") else font_size * 0.5
        #         approx_chars_per_line = int(max_text_width / avg_char_width)
                
        #         wrapped_lines = textwrap.wrap(Setting.YOUTUBE_METADATA.value.title, width=approx_chars_per_line)
                
        #         line_spacing = int(font_size * 0.2)
        #         total_text_height = 0
        #         line_bboxes = []
                
        #         for line in wrapped_lines:
        #             bbox = draw.textbbox((0, 0), line, font=font)
        #             l_width = bbox[2] - bbox[0]
        #             l_height = bbox[3] - bbox[1]
        #             line_bboxes.append((line, l_width, l_height))
        #             total_text_height += l_height + line_spacing
                    
        #         total_text_height -= line_spacing
        #         start_y = int(height * 0.70) - (total_text_height // 2)
                
        #         current_y = start_y
        #         for line, l_width, l_height in line_bboxes:
        #             x = (width - l_width) // 2
        #             stroke_width = max(3, int(font_size * 0.04))
        #             for adj_x in range(-stroke_width, stroke_width + 1):
        #                 for adj_y in range(-stroke_width, stroke_width + 1):
        #                     if adj_x != 0 or adj_y != 0:
        #                         draw.text((x + adj_x, current_y + adj_y), line, font=font, fill="black")
        #             draw.text((x, current_y), line, font=font, fill=(255, 230, 0))
        #             current_y += l_height + line_spacing

        #         final_img = img.convert("RGB")
        #         final_img.save(thumbnail_path, "JPEG", quality=95)

        #     # 최초 썸네일 텍스트 합성 실행
        #     render_thumbnail_with_custom_font()
            
        #     while True:
        #         thumb_preview_img = cv2.imread(str(thumbnail_path))
        #         thumb_window_title = "Thumbnail Preview (Enter: Proceed | T: Title | S: Font Size | Esc: Exit)"
        #         cv2.namedWindow(thumb_window_title, cv2.WINDOW_NORMAL)
        #         cv2.resizeWindow(thumb_window_title, 960, 540)
        #         cv2.imshow(thumb_window_title, thumb_preview_img)
                
        #         print("\n📸 [썸네일 미리보기 확인]")
        #         print(" • [Enter] 또는 [Space] : 썸네일 마음에 듦! 👉 영상 생성 및 업로드 진행")
        #         print(" • [T] 키 : 유튜브 제목 문구 수정")
        #         print(" • [S] 키 : 🔠 텍스트 크기(비율) 조절")
        #         print(" • [ESC] : 🏃‍♂️ 중지")
                
        #         key = cv2.waitKey(0) & 0xFF
                
        #         if key == 27:
        #             cv2.destroyAllWindows()
        #             print("작업을 취소합니다.")
        #             return None, None
        #         elif key == ord('t') or key == ord('T'):  # T 키를 누르면 제목 수정
        #             cv2.destroyAllWindows()
        #             print(f"\n현재 제목: {Setting.YOUTUBE_METADATA.value.title}")
        #             print("안내: 원하시는 위치에서 줄바꿈을 하려면 '\\n'을 입력해 주세요.")
                    
        #             new_title_input = input("수정할 새로운 유튜브 제목을 입력하세요: ").strip()
        #             if new_title_input:
        #                 # ★ [핵심] 사용자가 입력한 '\\n' 문자열을 실제 줄바꿈 문자('\n')로 변환
        #                 processed_title = new_title_input.replace("\\n", "\n")
                        
        #                 Setting.YOUTUBE_METADATA.value.title = processed_title
        #                 print(f"제목이 변경되었습니다. 썸네일을 재생성합니다...")
                        
        #                 bg.save(thumbnail_path, "JPEG")
        #                 render_thumbnail_with_custom_font()  # 변경된 제목과 줄바꿈으로 썸네일 다시 그리기
        #             continue
        #         elif key == ord('s') or key == ord('S'):  # S 키를 눌러 폰트 크기 변경
        #             cv2.destroyAllWindows()
        #             print(f"\n현재 폰트 크기 비율: {font_scale_ratio * 100}% (화면 높이 대비)")
        #             try:
        #                 new_scale_input = input("새로운 폰트 크기 비율을 입력하세요 (예: 0.06 -> 6%, 기본 0.07): ").strip()
        #                 if new_scale_input:
        #                     font_scale_ratio = float(new_scale_input)
        #                     bg.save(thumbnail_path, "JPEG")
        #                     render_thumbnail_with_custom_font()
        #                     print(f"폰트 크기가 {font_scale_ratio * 100}%로 변경되었습니다.")
        #             except ValueError:
        #                 print("⚠️ 잘못된 입력입니다. 숫자로 입력해 주세요.")
        #             continue
        #         elif key == 13 or key == 32:
        #             cv2.destroyAllWindows()
        #             break
            
        #     print(f"썸네일 이미지 확정 및 저장 완료: {thumbnail_path.name}")
        #     thumbnail_saved = True

        frame_bgr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)

    video_writer.release()
    print(f"동영상 생성 완료! 저장된 파일: {video_path.name}, 쇼츠: {Setting.VIDEO.value.is_shorts}({Setting.VIDEO.value.duration}s), 스크린 크기(w:{Setting.SCREEN.value.width}, h:{Setting.SCREEN.value.height})")
    return thumbnail_path, video_path

def create_all_type(bg_color):
    for pattern_type in PatternType:
        if pattern_type in [PatternType.WAVE, PatternType.DIAGONAL, PatternType.HONEYCOMB, PatternType.GRID, PatternType.STAGGERED]:
            continue
        # 미리보기 이미지 먼저 생성하기!
        show_interactive_preview(
            bg_color=bg_color,
            pattern_type=pattern_type,
            screen_size = ScreenSize.FK
        )

        create_rotating_pattern_video(
            duration_seconds=10, # 기본: 60s, 쇼츠: 10s
            rotation_speed=0.2
        )

        upload = False
        
        if upload:
            # 2. 메타데이터(제목, 설명글, 태그) 자동 생성
            generate_youtube_metadata()
    
            # 3. 유튜브 자동 업로드 함수 호출
            upload_video_to_youtube()



if __name__ == "__main__":
    img_path = Setting.PATH.value.set_img_path(f"sunflower.png")
    img_name = img_path.stem
    img_url = "www.flaticon.com/free-icon/sunflower_7963548"
    img_author = "juicy_fish - Flaticon"
    
    Setting.IMG.value.set(img_name, img_url, img_author)
    comment = """[Ad] Vibrant & Cheerful Sunflower Interior Decor #WealthLuck + Free Poster Art
https://link.coupang.com/a/gSf1TAJ2ku"""
    Setting.YOUTUBE_METADATA.value.comment = comment
    pattern_type = PatternType.HONEYCOMB
    bg_color = (210, 228, 218)
    create_all_type(bg_color)

    # show_interactive_preview(
    #     bg_color=bg_color,
    #     pattern_type=pattern_type,
    #     screen_size = ScreenSize.FK
    # )

    # create_rotating_pattern_video(
    #     duration_seconds=60*5, # 기본: 60s, 쇼츠: 10s
    #     rotation_speed=0.2
    # )

    # upload = False
    
    # if upload:
    #     # 2. 메타데이터(제목, 설명글, 태그) 자동 생성
    #     generate_youtube_metadata()

    #     # 3. 유튜브 자동 업로드 함수 호출
    #     upload_video_to_youtube()
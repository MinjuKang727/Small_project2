from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from openpyxl import Workbook, load_workbook
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import win32clipboard as clipboard
from types import SimpleNamespace
import unicodedata
import win32con
import pandas as pd
import pyperclip
import textwrap
import logging
import time
import re
import io

###### 로그 기록하기 ######
# 1. 로거(Logger) 객체 생성
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 로그 포맷 정의
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

# 2. 파일 핸들러 (파일에 남기기)
file_handler = logging.FileHandler("./data/auto_blog.log", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 3. 스트림 핸들러 (터미널 화면에 출력하기)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class SUFFIX(Enum):
    IMG = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    SUB = {".ttf", ".otf"}
    TXT = {".txt"}
    EXCEL = {".xlsx"}

class SRC(Enum):
    # 폰트
    FONT_CHIRONSUNGHK_EXTRABOLD = SimpleNamespace(PATH=Path("C:/USERS/KJY/APPDATA/LOCAL/MICROSOFT/WINDOWS/FONTS/CHIRONSUNGHK-EXTRABOLD.TTF"))  # 세련된 글씨체 
    FONT_CHIRONGOROUNDTC_EXTRABOLD = SimpleNamespace(PATH=Path("C:/USERS/KJY/APPDATA/LOCAL/MICROSOFT/WINDOWS/FONTS/CHIRONGOROUNDTC-EXTRABOLD.TTF"))  # 둥글둥글
    FONT_CHIRONHEIHK_EXTRABOLD = SimpleNamespace(PATH=Path("C:/USERS/KJY/APPDATA/LOCAL/MICROSOFT/WINDOWS/FONTS/CHIRONHEIHK-EXTRABOLD.TTF"))  # 사각형

    # 이미지 저장 폴더 
    IMG_FOLDER = SimpleNamespace(PATH=Path("C:/Users/KJY/Documents/Programming/AutoBlog/img"))
    # 이미지 파일
    BLANK_IMG = SimpleNamespace(PATH="blank.png") # name = value
    KOREAN_IMG = SimpleNamespace(PATH="korean.png")
    KUKSOOL_IMG = SimpleNamespace(PATH="kuksool.png")
    THUMBNAIL_IMG = SimpleNamespace(PATH="")
    # 생성 이미지 저장 폴더
    OUTPUT_IMG_FOLDER = SimpleNamespace(PATH=Path("C:/Users/KJY/Documents/Programming/AutoBlog/img/thumbnails"))

    # 데이터 저장 폴더
    DATA_FOLDER = SimpleNamespace(PATH=Path("C:/Users/KJY/Documents/Programming/AutoBlog/data"))
    # 엑셀 파일
    XLSX = SimpleNamespace(PATH=Path("C:/Users/KJY/Documents/Programming/AutoBlog/data/data.xlsx"))
    #텍스트 파일
    CONTENT_UPDATED = SimpleNamespace(PATH="content_updated.txt")
    CONTENT_LOG = SimpleNamespace(PATH="content_log.txt")
    THUMBNAIL_UPDATED = SimpleNamespace(PATH="thumbnail_updated.txt")
    THUMBNAIL_LOG = SimpleNamespace(PATH="thumbnail_log.txt")


    def set(self, path):
        if path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            raise FileExistsError("해당 경로에 파일이 존재하지 않아 경로 설정에 실패했습니다.")

        self.value.PATH = path

    def ck_exist(self):
        path = self.value.PATH
        suffix = Path(path).suffix.lower()

        if not isinstance(path, Path):
            if suffix in SUFFIX.IMG.value:
                path = SRC.IMG_FOLDER.ck_exist() / path
            elif suffix in (SUFFIX.TXT.value | SUFFIX.EXCEL.value):
                path = SRC.DATA_FOLDER.ck_exist() / path
            self.value.PATH = path
            path = self.ck_exist()
            return path
        
        if path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            logging.warning(f"해당 경로에 파일이 존재하지 않습니다. ({str(path)})")
            path.parent.mkdir(parents=True, exist_ok=True)

            if self == SRC.BLANK_IMG:
                logging.warning("이미지를 새로 생성 및 저장합니다.")
                width = 960
                height = 960
                image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                image.save(self.value.PATH)
            elif suffix in SUFFIX.IMG.value:
                logging.warning("빈 이미지로 대체합니다.")
                path = SRC.BLANK_IMG.ck_exist()
            elif suffix in SUFFIX.EXCEL.value:
                logging.warning("빈 엑셀 파일을 새로 생성 및 저장합니다.")
                wb = Workbook()
                wb.save(path)
            elif suffix in SUFFIX.TXT.value:
                logging.warning("빈 텍스트 파일을 새로 생성 및 저장합니다.")
                path.write_text("", encoding="utf-8")
            elif suffix in SUFFIX.SUB.value:
                logging.warning(f"폰트 파일을 찾을 수 없습니다\n({path}).\n기본 폰트를 사용합니다.")
                path = False

        return path
            

class URL(Enum):
    NAVER_HANJA_DICT = 'https://hanja.dict.naver.com/#/search?query=검색어'

    def get_url(self, word):
        return self.value.replace("검색어", word)

class Hanja_Dict(Enum):
    KOREAN="한글"
    HANJA="한자"
    HANJA_ALL="전체 한자"
    HANJA_SINGLE="개별 한자"
    PRON="발음 키"
    MEAN="뜻"

    CUR_DATA = SimpleNamespace()

    @classmethod
    def get(cls, key):
        if isinstance(key, Enum):
            key = key.name
        return getattr(cls.CUR_DATA.value, key, "")

    @classmethod
    def clear(cls):
        cls.CUR_DATA.value.__dict__.clear()

    # @classmethod
    # def set(cls, key, value):
    #     if isinstance(key, Enum):
    #         key = key.name
    #     return setattr(cls.CUR_DATA.value, key, value)

    @classmethod
    def set_by_dict(cls, dict):
        for key, value in dict.items():
            if isinstance(key, Enum):
                key = key.name
            setattr(cls.CUR_DATA.value, key, value)


def get_enum(value):
    if isinstance(value, Title):
        return Title.get_by_value(value)
    elif isinstance(value, SubTitle):
            return SubTitle.get_by_value(value)
    elif isinstance(value, Subject):
            return Subject.get_by_value(value)
    
class Title(Enum):
    WORD="어휘"
    CONFUSING="헷갈리는 어휘"
    PROVERB="속담"

    KOREAN="국어"
    HANJA="한자"
    HISTORY="한국사"
    ENGLISH="영어"
    VOCA = "영단어"

    @classmethod
    def get_by_value(value):
        for title in list(Title):
            if title.value == value:
                return title

class SubTitle(Enum):
    SELECT="선택"
    SPACING="띄어쓰기"
    SUBJECT="주관식"
    HANJA="한자어 독음"

    GRAMMAR="문법"
    WORD="어휘"
    BLANK=""

    @classmethod
    def get_by_value(value):
        for title in list(Title):
            if title.value == value:
                return title

class Subject(Enum):
    HANJA="한자어"
    PRON="표준 발음"
    ABC="사전 순서"
    SPELLING="맞춤법"
    SINGLE="낱개"
    SET="묶음"
    BLANK=""

    @classmethod
    def get_by_value(value):
        for title in list(Title):
            if title.value == value:
                return title

class Cols(Enum):
    DATE="날짜"
    TITLE = "구분"
    WORD = "단어"
    MEAN = "뜻"
    ANSWER = "정답"

    SUBTITLE = "세부 구분"
    SUBJECT = "주제"
    QUESTION = "문제"
    EXPLANATION = "해설"

class Excel_Key(Enum):
    NAME=auto()
    COLS=auto()
    GROUPBY_KEY=auto()
    TITLE=auto()
    SUBTITLE=auto()
    SUBJECT=auto()

    THUMBNAIL_IMG=auto()
    THUMBNAIL_TXT=auto()

    WB=auto()
    SHEET_NAME_LIST=auto()
    WS=auto()
    CUR_SHEET=auto()
    GROUPBY_DATA=auto()



class Excel(Enum):
    KOREAN = SimpleNamespace({Excel_Key.NAME.name:"국어",
                             Excel_Key.COLS.name:[Cols.TITLE, Cols.WORD, Cols.MEAN, Cols.ANSWER],
                             Excel_Key.GROUPBY_KEY.name:[Cols.DATE, Cols.TITLE],
                             Excel_Key.TITLE.name:[Title.WORD, Title.CONFUSING, Title.PROVERB],
                             Excel_Key.THUMBNAIL_IMG.name:SRC.KOREAN_IMG,
                             Excel_Key.THUMBNAIL_TXT.name:"#해커스공무원 #매일 국어"})
    DAILY = SimpleNamespace({Excel_Key.NAME.name:"매일",
                            Excel_Key.COLS.name:[Cols.TITLE, Cols.SUBTITLE, Cols.SUBJECT, Cols.QUESTION, Cols.EXPLANATION, Cols.ANSWER],
                            Excel_Key.GROUPBY_KEY.name:[Cols.DATE, Cols.TITLE, Cols.SUBTITLE, Cols.SUBJECT],
                            Excel_Key.TITLE.name:[Title.KOREAN, Title.HANJA, Title.HISTORY, Title.ENGLISH, Title.VOCA],
                            Excel_Key.SUBTITLE.name:[SubTitle.SELECT, SubTitle.SPACING, SubTitle.SUBJECT, SubTitle.HANJA, SubTitle.GRAMMAR, SubTitle.WORD, SubTitle.BLANK],
                            Excel_Key.SUBJECT.name: [Subject.HANJA, Subject.PRON, Subject.ABC, Subject.SPELLING, Subject.SINGLE, Subject.SET, Subject.BLANK]})

    CUR_WORK = SimpleNamespace()
    CREATING = SimpleNamespace()


    @classmethod
    def get(cls, key):
        simplens = cls.CUR_WORK.value

        if isinstance(key, Enum):
            key = key.name
        return getattr(simplens, key)

    @classmethod
    def set(cls, key, value):
        if isinstance(key, Enum):
            key = key.name
        setattr(cls.CUR_WORK.value, key, value)

    @classmethod
    def update(cls, dict):
        if isinstance(dict, Enum):
            dict = dict.value.__dict
        cls.CUR_WORK.value.__dict__.update(dict)

    @classmethod
    def groupby(cls):
        logging.info("엑셀 데이터 groupby 중...")
        ws = cls.get(Excel_Key.WS)
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        if len(header_row) != len(cls.get(Excel_Key.COLS)):
            logging.warning("엑셀 파일에 존재하는 열 개수와 프로그램에 설정된 열의 개수가 일치하지 않습니다.")

        col_idx = {name: idx for idx, name in enumerate(header_row) if name is not None}
        groupby_cols = [col.name for col in cls.get(Excel_Key.GROUPBY_KEY)]
        groupby_indices = sorted([col_idx[col] for col in groupby_cols])
        last_indices = sorted([i for i in range(len(header_row)) if i not in groupby_indices])

        # 그룹별 데이터를 담을 딕셔너리 (기본값이 리스트인 형태)
        groupby_data = defaultdict(list)
    
        # min_row=2부터 시작하여 헤더(1행)를 제외하고 데이터 읽기
        # values_only=True로 지정하면 셀 안의 값만 튜플 형태로 가져옵니다.
        for row in ws.iter_rows(min_row=2, values_only=True):
            cur_row = [val if val is not None else "" for val in row]  # A열: 부서명 (인덱스 0)
            groupby_key = tuple(cur_row[i] for i in groupby_indices)
            last_cols = tuple(cur_row[i] for i in last_indices)
            groupby_data[groupby_key].append(last_cols)

        set(Excel_Key.GROUPBY_DATA, groupby_data)
        return groupby_data

    @classmethod
    def read(cls, excel_path):
        logging.info("엑셀 파일 읽는 중...")
        cls.CUR_WORK.value.__dict__.clear()
        wb = load_workbook(excel_path)
        cls.set(Excel_Key.WB, wb)  # 엑셀 파일 데이터
        sheet_name_list = wb.sheetnames
        cls.set(Excel_Key.SHEET_NAME_LIST, sheet_name_list)  # 시트 이름 리스트

        target_sheet_name = sheet_name_list[0]
        if len(sheet_name_list) > 1:
            info_list = [f"{i + 1}. {name}" for i, name in enumerate(sheet_name_list)]
            Work.work(Work.SELECT_IN_RANGE, Work_Content.SHEET, sheet_name_list, info_list)
            target_sheet_name = Work.ask()

        ws = wb[target_sheet_name]
        cls.set(Excel_Key.WS, ws)

        for sheet in list(Excel):
            if target_sheet_name == getattr(sheet.value, Excel_Key.NAME.name, ""):
                cls.set(Excel_Key.CUR_SHEET, sheet)
                cls.update(sheet)
                break
        
        return ws

    @classmethod
    def create(cls, groupby_key, last_data, include_date=False):
        i = 0
        if not include_date:
            i = 1
        match get_name_tuple(groupby_key)[i:]:
            case (Title.WORD):
                search_hanja_with_kor


def get_name_tuple(groupby_key):
    return tuple([get_enum(data) for data in groupby_key])
        

class Data(Enum):
    IMG = "사진"
    STRING = "글"

class Content(Enum):
    THUMBNAIL = "썸네일"
    BLOG = "블로그"

# class Korean_Title(Enum):
#     WORD = "어휘"
#     CONFUSING = "헷갈리는 어휘"
#     PROVERB = "속담"


def get_visual_width(text):
    """문자열의 실제 시각적 너비를 계산 (한글/한자는 2칸, 영문/기호는 1칸)"""
    return sum(2 if unicodedata.east_asian_width(char) in 'WF' else 1 for char in text)

def get_boxed_str(text, max_width=100):
    """
    문자열이 너무 길면 지정한 너비(max_width)를 기준으로 줄바꿈을 한 뒤 박스를 씌웁니다.
    """
    processed_lines = []
    
    # 1. 입력된 텍스트의 각 줄을 순회하며 너무 긴 줄은 자동 줄바꿈 처리
    for raw_line in text.split("\n"):
        if not raw_line.strip():
            processed_lines.append("")
            continue
            
        # textwrap은 글자 수 기준이므로 한글이 섞인 경우를 고려해 적절히 자릅니다.
        # (한글 폭을 고려해 대략적인 글자 수로 맞추거나 고정 길이 적용)
        wrapped_parts = textwrap.wrap(raw_line, width=max_width, break_long_words=True, break_on_hyphens=False)
        processed_lines.extend(wrapped_parts)

    # 2. 가장 긴 줄의 '시각적 너비' 계산
    if not processed_lines:
        max_len = 0
    else:
        max_len = max(get_visual_width(line) for line in processed_lines)

    # 3. 테두리 생성 (실제 시각적 너비 기준)
    border = "┌" + "─" * (max_len + 2) + "┐\n"
    bottom = "└" + "─" * (max_len + 2) + "┘"

    boxed_str = border
    for line in processed_lines:
        current_width = get_visual_width(line)
        # 부족한 너비만큼 공백을 채워줌 (우측 정렬 보정)
        padding = " " * (max_len - current_width)
        boxed_str += f"│ {line}{padding} │\n"
    boxed_str += bottom

    return boxed_str

class Ask_Key(Enum):
    ASK_TYPE = auto()
    WORK_TYPE = auto()
    WORK_CONTENT = auto()
    WORK_INFO = auto()
    CONTENT_INFO = auto()

    QUESTION = auto()
    NOTE = auto()
    BOXED_INFO = auto()
    CONDITION = auto()
    OPTIONS = auto()

    DATA_TYPE = auto()
    CONTENT_TYPE = auto()

class Option(Enum):
    YES = auto()
    NO = auto()
    PASTE = auto()
    RANGE = auto()
    ALL = auto()

class Ask(Enum):
    YN = SimpleNamespace({Ask_Key.QUESTION.name:"해당 작업을 진행하시겠습니까? (y:계속 진행, n:작업 취소)",
                            Ask_Key.OPTIONS.name:SimpleNamespace({Option.YES.name: ["y", "Y", "ㅛ"], 
                                                                    Option.NO.name: ["n", "N", "ㅜ"],
                                                                    Option.ALL.name: ["y", "Y", "ㅛ", "n", "N", "ㅜ"]}),
                            Ask_Key.CONDITION.name:"허용되지 않은 입력값입니다."})
    YPN = SimpleNamespace({Ask_Key.QUESTION.name:"해당 작업을 진행하시겠습니까? (y:계속 진행, p:클립보드에만 복사, n:작업 취소)",
                            Ask_Key.NOTE.name:"('y' 선택 시, 자동으로 클립보드에 복사도 됩니다.)",
                            Ask_Key.OPTIONS.name:SimpleNamespace({Option.YES.name: ["y", "Y", "ㅛ"], 
                                                Option.PASS.name: ["p", "P", "ㅔ"],
                                                Option.NO.name: ["n", "N", "ㅜ"],
                                                Option.ALL.name: ["y", "Y", "ㅛ", "p", "P", "ㅔ", "n", "N", "ㅜ"]}),
                            Ask_Key.CONDITION.name:"허용되지 않은 입력값입니다."})
    YNR = SimpleNamespace({Ask_Key.QUESTION.name:"현재 작업을 선택하시겠습니까? (y:선택, Enter or n:선택 안 함(다음 작업 진행), 숫자:해당 번호의 작업 선택)",
                            Ask_Key.OPTIONS.name:SimpleNamespace({Option.YES.name: ["y", "Y", "ㅛ"], 
                                                                    Option.NO.name: ["n", "N", "ㅜ", ""],
                                                                    Option.RANGE.name: [],
                                                                    Option.ALL.name: ["y", "Y", "ㅛ", "n", "N", "ㅜ"]}),
                            Ask_Key.CONDITION.name:"허용되지 않은 입력값입니다."})
    RANGE = SimpleNamespace({Ask_Key.QUESTION.name: "작업할 내용을 선택해 주세요.",
                            Ask_Key.CONDITION.name:"허용되지 않은 입력값입니다."})
                         


    # def get(self, key1, key2=""):
    #     if isinstance(key1, Enum):
    #         key1 = key1.name
    #     if isinstance(key2, Enum):
    #         key2 = key2.name

    #     value1 = getattr(self.value, key1)
    #     if key2 == "" and isinstance(value1, SimpleNamespace):
    #         key2 = Option.ALL.name
        
    #     return getattr(value1, key2, value1)


# def get_simpns(question, options=SimpleNamespace(), work_type="", condition="허용되지 않은 입력값입니다."):
#     ask_simpns = SimpleNamespace()

#     if isinstance(work_type, Work):
#         setattr(ask_simpns, Ask_Key.WORK_TYPE.name, work_type)
#         work_type_value = work_type.value

#         if hasattr(work_type_value, Option.RANGE.name):
#             options.ALL = work_type_value.OPT_RANGE
        
#     ask_simpns.update({Ask_Key.QUESTION.name: question,
#                         Ask_Key.CONDITION.name: condition,
#                         Ask_Key.OPTIONS.name: options})

#     return ask_simpns

class Data_Key(Enum):
    VALUE = auto()
    INFO = auto()

            
class Work_Content(Enum):
    WORK = SimpleNamespace({Ask_Key.WORK_INFO.name:"선택 할 수 있는 작업 불러오는 중...",
                            Ask_Key.BOXED_INFO.name: get_boxed_str('1. 블로그 글만 작성(with 엑셀)\n2.썸네일 이미지만 생성(with 엑셀)\n3.블로그 글 작성 & 썸네일 이미지 생성(with 엑셀)\n4.썸네일 이미지 생성(with 직접 입력)'),
                            Ask_Key.OPTIONS.name:SimpleNamespace({Option.ALL.name: [str(i + 1) for i in range(4)]})})
    SHEET = SimpleNamespace({Ask_Key.WORK_INFO.name:"엑셀 파일 내 시트 목록을 불러오는 중..."})
    THUMBNAIL_IMG = SimpleNamespace({Ask_Key.CONTENT_INFO.name:"썸네일 이미지",
                                    Ask_Key.DATA_TYPE.name:Data.IMG,
                                    Ask_Key.CONTENT_TYPE.name:Content.THUMBNAIL})
    THUMBNAIL_TXT = SimpleNamespace({Ask_Key.CONTENT_INFO.name:"썸네일 글",
                                    Ask_Key.DATA_TYPE.name:Data.STRING,
                                    Ask_Key.CONTENT_TYPE.name:Content.THUMBNAIL})
    BLOG_TXT = SimpleNamespace({Ask_Key.CONTENT_INFO.name:"블로그 글",
                                Ask_Key.DATA_TYPE.name:Data.STRING,
                                Ask_Key.CONTENT_TYPE.name:Content.BLOG})
    WORD = SimpleNamespace({Ask_Key.WORK_INFO.name:"선택 가능한 단어 목록 불러오는 중..."})

    DATA = SimpleNamespace()


    # @classmethod
    # def work(cls, data):
    #     cls.DATA.value.__dict__.clear()
    #     cls.DATA.value.update({Data_Key.VALUE.name: data,
    #                            Data_Key.INFO.name: []})


    # @classmethod
    # def set_data(cls, value, key=Data_Key.VALUE.name):
    #     if isinstance(key, Enum):
    #         key = key.name

    #     setattr(cls.DATA.value, key, value)

    # @classmethod
    # def get_data(cls, key=Data_Key.VALUE.name):
    #     if isinstance(key, Enum):
    #         key = key.name

    #     if not hasattr(cls.DATA.value, key) and key == Data_Key.INFO.name:
    #         cls.set_data(Data_Key.INFO, [])

    #     return getattr(cls.DATA.value, key)

class Work(Enum):
    SELECT_IN_RANGE = SimpleNamespace({Ask_Key.ASK_TYPE.name:Ask.RANGE,
                                      Ask_Key.OPTIONS.name:SimpleNamespace({Option.ALL.name: []})})
    SELECT_IN_YNR = SimpleNamespace({Ask_Key.ASK_TYPE.name:Ask.YNR})
    CREATE = SimpleNamespace({Ask_Key.ASK_TYPE.name:Ask.YN,
                            Ask_Key.WORK_INFO.name:"생성을 시도하는 중..."})
    SAVE = SimpleNamespace({Ask_Key.ASK_TYPE.name:Ask.YPN,
                            Ask_Key.WORK_INFO.name:"저장을 시도하는 중..."})
    OVERWRITE = SimpleNamespace({Ask_Key.ASK_TYPE.name:Ask.YN,
                                Ask_Key.WORK_INFO.name:"파일에 이미 이전 파일이 존재하여 덮어쓰기를 시도하는 중...",
                                Ask_Key.DATA_TYPE.name:Data.STRING})
    
    CUR_WORK = SimpleNamespace()


    @classmethod
    def get(cls, key1, key2=""):
        if isinstance(key1, Enum):
            if isinstance(key1, Option):
                value1 = getattr(cls.CUR_WORK.value, Ask_Key.OPTIONS.name)
                return getattr(value1, key1.name)
            elif isinstance(key1, Data_Key):
                value1 = getattr(cls.CUR_WORK.value, Work_Content.DATA.name)
                return getattr(value1, key1.name)
            else:
                key1 = key1.name

        if isinstance(key2, Enum):
            key2 = key2.name

        value1 = getattr(cls.CUR_WORK.value, key1, "")
        if key1 in [Ask_Key.OPTIONS, Ask_Key.OPTIONS.name] and key2 == "":
            key2 = Option.ALL.name
        return getattr(value1, key2, value1)

    @classmethod
    def eq(cls, key, value):
        return cls.get(key) == value

    # boxed_info 및 option range 업데이트 용 메서드
    @classmethod
    def update(cls, dict):  
        cls.CUR_WORK.value.__dict__.update(dict)

    @classmethod
    def update_range(cls, i):
        options = getattr(cls.CUR_WORK.value, Ask_Key.OPTIONS)
        getattr(options, Option.RANGE).append(i + 1)
        getattr(options, Option.ALL).append(i + 1)
        boxed_info = get_summary(Work.get(Data_Key.VALUE)[i], i)
        Work.get(Data_Key.INFO).append(boxed_info)
        cls.update({Ask_Key.BOXED_INFO.name:boxed_info})

    @classmethod
    def ck_data_type(cls, data_type, content_type=""):
        return cls.CUR_WORK.eq(Ask_Key.DATA_TYPE, data_type) and (content_type == "" or cls.CUR_WORK.eq(Ask_Key.CONTENT_TYPE, content_type))

    @classmethod
    def work(cls, work_type, work_content, data="", info_list=[]):
        cur_work = cls.CUR_WORK.value
        cur_work.__dict__.clear()  # 이전 작업 내용 삭제
    
        setattr(cur_work, Ask_Key.WORK_TYPE, work_type)
        setattr(cur_work, Ask_Key.WORK_CONTENT, work_content)
        cls.update(work_type.value.__dict__)  
        cls.update(work_content.value.__dict__)

        ask_type_dict = work_type.get(Ask_Key.ASK_TYPE).value.__dict__
        cls.update(ask_type_dict)  # Question, Options 업데이트

        if work_type == Work.SELECT_IN_RANGE and len(info_list) > 0:
            boxed_info = "\n".join([info for info in info_list])
            cls.update({Ask_Key.OPTIONS.name:SimpleNamespace({Option.ALL.name: [i + 1 for i in range(len(info_list))]}),
                        Ask_Key.BOXED_INFO.name:boxed_info})

        data_simpns = SimpleNamespace()
        data_simpns.__dict__.update({Data_Key.VALUE.name: data,
                                    Data_Key.INFO.name: info_list})
        cls.update({Work_Content.DATA.name: data_simpns})

    #### input 값 받기 전용 메서드
    @classmethod
    def ask(cls):
        content_info = cls.CUR_WORK.get(Ask_Key.CONTENT_INFO)
        work_info = cls.CUR_WORK.get(Ask_Key.WORK_INFO)
        boxed_info = cls.CUR_WORK.get(Ask_Key.BOXED_INFO)
        question = cls.CUR_WORK.get(Ask_Key.QUESTION)
        note = cls.CUR_WORK.get(Ask_Key.NOTE)
        condition = cls.CUR_WORK.get(Ask_Key.CONDITION)
        options = cls.CUR_WORK.get(Ask_Key.OPTIONS)

        if content_info != "":
            work_info = f"{content_info} {work_info}"

        logging.info(work_info)

        if boxed_info != "":
            question = f"{question}\n{boxed_info}"

        if note != "":
            question = f"{question}\n{note}"
        

        select = input(f"{question}\n> ")

        while select not in options:
            logging.info(condition)
            select = input(f"{question}\n> ")

        cls.reply(select)

    @classmethod
    def reply(cls, select):
        work_type = cls.get(Ask_Key.WORK_TYPE)
        work_content = cls.get(Ask_Key.WORK_CONTENT)

        if work_type == Work.SELECT_IN_RANGE:
            if work_content == Work_Content.WORK:
                match select:
                    case 1:
                        return get_str_contents()
                    case 2:
                        return get_img_content()
                    case 3:
                        return get_all_contents()
                    case 4:
                        day = "#33일차\n"
                        text_str = "#몸풀기 운동 #피구 #팔굽혀펴기 10회 당첨! #드디어 쌍절곤 2개! #물구나무서기 #열심히 연습 중 #흰띠 #띠별 발차기 #앞차기 #기초 5형 #호신술 #기본 7수"
                        word_list = [f"#{word.strip()}" for word in text_str[1:].split("#")]
                        title_text = break_text_leq16(word_list, day)

                        text_color = "white"
                        font_path = SRC.FONT_CHIRONHEIHK_EXTRABOLD.ck_exist()
                        input_img_path = SRC.KUKSOOL_IMG.ck_exist()
                        shadow = False

                        return create_thumbnail(title_text, text_color, font_path, input_img_path, shadow)
            elif work_content in [Work_Content.SHEET, Work_Content.WORD]:
                data = Work.get(Work_Content.DATA)
                select = int(select) - 1
                result = data[select]
                return result

        elif work_type == Work.SELECT_IN_YNR:
            data = Work.get(Data_Key.VALUE)

            if select in cls.get(Option.YES):
                Hanja_Dict.clear()
                return data[cls.get(Option.RANGE)[-1]]
            elif select in cls.get(Option.RANGE):
                confirm = -1
                yn = cls.get(Option.YES) + cls.get(Option.NO)
                boxed_info = get_boxed_str(cls.get(Data_Key.INFO)[select])

                while confirm not in yn:
                    confirm = input(f"아래 단어를 선택하시는 것이 맞습니까? (y:예, n:아니오)\n{boxed_info}")

                if confirm in cls.get(Option.YES):
                    Hanja_Dict.clear()
                    return data[int(select) - 1]
                
            return False
        
        elif work_type == Work.SAVE:
            if select in cls.get(Option.NO):
                logging.info("데이터 저장을 취소합니다.")
                return

            data_type = cls.get(Ask_Key.DATA_TYPE)
            content_type = cls.get(Ask_Key.CONTENT_TYPE)
            copy_to_clipboard()

            if select in cls.get(Option.PASTE):
                return

            updated_path = ""
            log_path = ""

            if data_type == Data.STRING:
                if content_type == Content.BLOG:
                    updated_path = SRC.CONTENT_UPDATED.ck_exist()
                    log_path = SRC.CONTENT_LOG.ck_exist()
                elif content_type == Content.THUMBNAIL:
                    updated_path = SRC.THUMBNAIL_UPDATED.ck_exist()
                    log_path = SRC.THUMBNAIL_LOG.ck_exist()

                pre_content = updated_path.read_text(encoding="utf-8")  # 기존 파일 읽기
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]\n{pre_content}\n{'-'*40}\n\n")

                updated_path.write_text(Work.get(Data_Key.VALUE), encoding="utf-8")
                logging.info("데이터 저장 완료.")
    
                # write_flag = True
                # if len(pre_content.strip()) > 0:
                #     Work.work(Work.OVERWRITE, cls.get(Ask_Key.WORK_CONTENT), Work.get(Data_Key.VALUE))
                #     write_flag = Work.ask()

                # if write_flag:
                #     updated_path.write_text(Work.get(Data_Key.VALUE), encoding="utf-8")
                #     logging.info("데이터 저장 완료.")
                # else:
                #     logging.info("덮어쓰기를 취소하여 데이터를 저장하지 않습니다.")

            elif data_type == Data.IMG:
                output_image_path = SRC.OUTPUT_IMG_FOLDER.ck_exist()
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                output_image_path = output_image_path / f"{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg"
                data.save(output_image_path, "JPEG")
                logging.info(f"데이터 저장 완료. ({output_image_path})")
                return
            
        elif work_type == Work.CREATE and select in cls.get(Option.YES):
            if cls.ck_data_type(Data.IMG, Data.THUMBNAIL):
                try:
                    create_thumbnail(Work.get(Data_Key.VALUE))
                except Exception as e:
                    logging.exception(e)

        elif work_type == Work.OVERWRITE:
            if select in cls.get(Option.YES):
                return True
            else:
                return False
                    
                            

#### 이미지 혹은 문자열 클립보드에 복사
def copy_to_clipboard():
    data_type = Work.get(Ask_Key.DATA_TYPE)
    data = Work.get(Data_Key.VALUE)
    try:
        if data_type == Data.IMG:
            # 2. BMP 포맷으로 변환 (클립보드 호환)
            output = io.BytesIO()
            data.convert("RGB").save(output, "BMP")
            copy_data = output.getvalue()[14:]  # BMP 헤더 14바이트 제거
            output.close()

            # 3. 클립보드에 이미지 복사
            clipboard.OpenClipboard()  # 클립보드 열기
            clipboard.EmptyClipboard()  # 클립보드 비우기
            clipboard.SetClipboardData(clipboard.CF_DIB, copy_data)
        elif data_type == Data.STRING:
            clipboard.OpenClipboard()
            clipboard.EmptyClipboard()
            clipboard.SetClipboardData(win32con.CF_UNICODETEXT, data)  # 텍스트 설정 (CF_UNICODETEXT는 유니코드 문자열 형식)
    except Exception as e:
        logging.exception(e)
    finally:
        logging.info("데이터가 클립보드에 복사되었습니다.")
        clipboard.CloseClipboard()

#### 썸네일 이미지 생성
def create_thumbnail(title_text: str, text_color="black", font_path="", input_image_path="", shadow_flag=True, line_spacing=15):
    """
    이미지를 생성합니다.
    line_spacing: 줄 간격(행간)을 조절할 픽셀 수 (기본값 15)
    """
    logging.info("이미지 생성 시작")

    if font_path == "":
        font_path = SRC.FONT_CHIRONSUNGHK_EXTRABOLD.ck_exist()
    if input_image_path == "":
        input_image_path = SRC.THUMBNAIL_IMG.ck_exist()

    try:
        # 2. 이미지 열기 (pathlib 객체를 그대로 전달 가능)
        img = Image.open(input_image_path)
        draw = ImageDraw.Draw(img)

        width, height = img.size
        padding_x = 80  # 좌우 여백
        padding_y = 80  # 상하 여백
        max_allowed_width = width - (2 * padding_x)
        max_allowed_height = height - (2 * padding_y)

        # [자동 폰트 크기 조절] 텍스트가 패딩 영역을 넘지 않도록 크기 조정
        font_size = 80  # 시작 폰트 크기
        min_font_size = 20  # 최소 폰트 크기 마지노선

        while font_size >= min_font_size:
            if font_path:
                title_font = ImageFont.truetype(str(font_path), font_size)
            else:
                try:
                    title_font = ImageFont.load_default(size=font_size)
                except TypeError:
                    title_font = ImageFont.load_default()
                    break

            # 현재 폰트 크기와 행간(spacing)을 반영하여 텍스트 블록 크기 계산
            bbox = draw.multiline_textbbox((0, 0), title_text, font=title_font, align="left", spacing=line_spacing)
                
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

        # 6. 정중앙 좌표 (X, Y) 계산
        x_centered = (width - text_block_width) / 2
        y_centered = (height - text_block_height) / 2

        if shadow_flag:
            shadow_color = (200, 200, 200, 128) # 반투명 회색 그림자
            shadow_offset = 3

            # 그림자 효과 그리기 (spacing 동일하게 적용 필수)
            draw.multiline_text(
                (x_centered + shadow_offset, y_centered + shadow_offset),
                title_text,
                font=title_font,
                fill=shadow_color,
                align="left",
                spacing=line_spacing,
            )

        # 실제 검은색 텍스트 그리기 (spacing 적용)
        draw.multiline_text(
            (x_centered, y_centered),
            title_text,
            font=title_font,
            fill=text_color,
            align="left",
            spacing=line_spacing,
        )

        # 6. 이미지 미리보기 및 저장 처리
        img.show()

        Work.work(Work.SAVE, Work_Content.THUMBNAIL_IMG, img)
        Work.ask()

    except Exception as e:
        logging.exception(f"이미지 생성 중, 예기치 않은 오류 발생: {e}")
    finally:
        img.close()

#### 문자열에서 (한자) 제거
def remove_hanja(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("문자열에서 한자 제거 중 에러 발생.\n입력값은 문자열이어야 합니다.")

    # 1. 소괄호와 그 안의 내용 제거
    no_parentheses = re.sub(r"\([^)]*\)", "", text)

    # 2. 한자 제거 (유니코드 범위: U+4E00 ~ U+9FFF)
    no_hanja = re.sub(r"[\u4E00-\u9FFF]", "", no_parentheses)

    # 3. 앞뒤 공백 정리
    return no_hanja.strip()



#### 블로그 내용 작성  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< sheet가 '국어'일 때 조건으로 코드 작성한 것임!!!! (시트 많아지면 수정 필요!!!!!)
def get_Korean_str(content_type, data_list):
    content_str = ""
    answer_list = []

    for i, data in enumerate(data_list):
        word, mean, answer = data
        logging.info(f"블로그 작성중...(단어: {word})")
        if content_type == Excel.get("TITLE", "WORD"):
            hanja_dict = search_hanja_with_kor(word, mean)

            dict_key_word = Excel.get("HANJA_DICT_KEY", Hanja_Dict.KOREAN.value)
            if dict_key_word not in hanja_dict:
                raise KeyError(f"'어휘' 관련 블로그 내용을 작성 중 에러 발생.\n필수 데이터인 '{dict_key_word}'키가 누락되었습니다.")
            content_str += f"#{hanja_dict[dict_key_word]}"

            dict_key_hanja = Excel.get("HANJA_DICT_KEY", "HANJA")
            dict_key_hanja_all = Excel.get("HANJA_DICT_KEY", "HANJA_ALL")
            dict_key_hanja_single = Excel.get("HANJA_DICT_KEY", "HANJA_SINGLE")

            hanja_in_hanja_dict = hanja_dict[dict_key_hanja]

            if dict_key_hanja in hanja_dict:
                if dict_key_hanja_all in hanja_in_hanja_dict:
                    hanja = hanja_in_hanja_dict[dict_key_hanja_all]
                    content_str += f" #{hanja}\n"

                    if dict_key_hanja_single in hanja_in_hanja_dict:
                        hanja_list = hanja_in_hanja_dict[dict_key_hanja_single]
                        content_str += "  ".join(hanja_list) + "\n"

            dict_key_pron = Excel.get("HANJA_DICT_KEY", "PRON")
            if dict_key_pron in hanja_dict:
                pron_list = []
                if len(pron_list) > 0:
                    for pron_key in hanja_dict[dict_key_pron]:
                        pron_list.append(f"{pron_key}: {hanja_dict[pron_key]}")
                    content_str += "\n".join(pron_list) + "\n"

            dict_key_mean = Excel.get("HANJA_DICT_KEY", "MEAN")
            if dict_key_mean not in hanja_dict:
                raise KeyError(f"'어휘' 관련 블로그 내용을 작성 중 에러 발생.\n필수 데이터인 '{dict_key_mean}'키가 누락되었습니다.")
            content_str += f"{"\n".join(hanja_dict[dict_key_mean])}\n"

        elif content_type == Excel.get("TITLE", "CONFUSING"):
            content_str += f"{i + 1}. {word}\n"
            answer, answer_sentence_list, option_list = get_confusing_list(word, answer)
            hashtag_options = "        " + " ".join([option for option in option_list])

            for i, answer_sentence in enumerate(answer_sentence_list):
                answer_str = f"{len(answer_list) + 1}. {answer_sentence}"

                if i == 0:
                    answer_str += hashtag_options
                answer_list.append(answer_str)

        elif content_type == Excel.get("TITLE", "PROVERB"):
            proverb = word.replace(" ", "_")
            content_str += f"#{proverb}\n{mean}\n"

    if content_type == Excel.get("TITLE", "CONFUSING"):
        answer = "\n".join(answer_list)
        content_str += f"\n\n\n\n\n\n\n\n#정답\n{answer}\n"

    return content_str

# 구분: 헷갈리는 어휘 데이터 추출
def get_confusing_list(word, answer):
    """
    세부 구분: 헷갈리는 어휘에서 데이터를 추출합니다.
    반환값: [문제, [정답 문자열, ...], [보기1, ...]] : list
    
    문자열 내에 소괄호('('')')가 존재하지 않는 경우 ValueError 발생!
    """
    match = re.search(r"\((.*?)\)", word) # 소괄호 안의 내용 찾기 (괄호 제외)
    if match:
        extracted = match.group(1)  # 첫 번째 그룹(괄호 안 내용) 가져오기: 이튿날 / 이튿날
        option_list = [w.strip() for w in extracted.split("/")]
        answer_list = [a.stri() for a in answer.split(",")]
        answer_sentence_list = []
        for answer in answer_list:
            answer_sentence = re.sub(r"\([^)]*\)", answer, word)
            answer_sentence_list.append(answer_sentence)
        return [word, answer_sentence_list, option_list]
    else:
        raise ValueError("'헷갈리는 어휘' 데이터 추출 중 에러 발생.\n문자열 내에 소괄호가 존재하지 않습니다.")

#### 크롤링에서 클릭할 a태그 선택
def find_target(tags, kor, mean="", hanja=""):
    logging.info("크롤링할 단어 선택 중...")

    for i in range(len(tags)):
        Work.work(Work.SELECT_IN_YNR, Work_Content.WORD, tags)
        Work.update_range(i)
        select_tag = Work.ask()
        if select_tag:
            return select_tag.find_element(By.CSS_SELECTOR, 'a')

    data_info_list = Work.get(Data_Key.INFO)
    Work.work(Work.SELECT_IN_RANGE, Work_Content.WORD, tags, data_info_list)
    select_tag = Work.ask()
    return select_tag.find_element(By.CSS_SELECTOR, 'a')
        
        

def get_summary(tag, idx):
    info_list = []
    temp = ""
    for i, txt in enumerate(tag.text.strip().split("\n")[:-1]):
        if i == 1:
            continue
        pattern = r'^\d+\.$'

        if len(temp) > 0:
            txt = temp + txt
            temp = ""

        elif bool(re.fullmatch(pattern, txt)):
            temp = txt
            continue
        
        info_list.append(txt)
    info_str = "\n".join(info_list)
    boxed_info = f"[{idx + 1}번]\n{get_boxed_str(info_str)}"
    return boxed_info

def separate_single_hanja(hanja_single):
    pattern = r'([^\s]+\s+[^\s]+)'
    result = re.sub(r'(?!^)(?=[\u4e00-\u9fff])', ' / ', hanja_single)
    return result

#### 한자 사전 검색 결과 dict 반환
def search_hanja_with_kor(word, mean=""):
    logging.info(f"한자 사전 검색 중...({word})")
    # 1. 코랩용 크롬 옵션 설정
    options = Options()
    options.add_argument('--headless')          # 화면 없이 실행 (필수)
    options.add_argument('--no-sandbox')        # 보안 관련 에러 방지
    options.add_argument('--disable-dev-shm-usage') # 메모리 부족 에러 방지

    # 2. WebDriver-manager를 이용해 자동으로 호환되는 드라이버 설정
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # 3. 테스트 접속
        naver_hanja_dict_url = URL.NAVER_HANJA_DICT.get_url(word)
        driver.get(naver_hanja_dict_url)

        try:
            tags = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '#searchPage_entry .row')
                )
            )

        except Exception as e:
            logging.warning(f"한자 사전 크롤링 중 에러 발생1 : {e}")

        target_link = find_target(tags, word, mean)

        # 4. 클릭 실행
        target_link.click()

        hanja_tag = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.component_entry')
            )
        )

        hanja_all, korean, hanja_single, pron = hanja_tag.text.strip().split("\n")[1:]

        mean_tag = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.mean_list.my_mean_list')
            )
        )

        mean_list = [remove_hanja(m) for m in mean_tag.text.strip().split("\n")]

        Hanja_Dict.set_by_dict({
            Hanja_Dict.KOREAN: korean,
            Hanja_Dict.HANJA_ALL: hanja_all,
            Hanja_Dict.HANJA_SINGLE: separate_single_hanja(hanja_single),
            Hanja_Dict.PRON: pron,
            Hanja_Dict.MEAN: "\n".join(mean_list)
        })
    
    except Exception as e:
        logging.warning(f"한자 사전 크롤링 중 에러 발생 : {e}")

    finally:
        # 4. 브라우저 종료
        driver.quit()
        logging.info(f"...완료")


#### 엑셀 파일 읽기
def read_xlsx():
    xlsx_src = SRC.XLSX.ck_exist()
    if not xlsx_src.exists():
        raise FileExistsError(f"엑셀 파일을 읽던 중 에러 발생.\n파일이 존재하지 않습니다.({str(xlsx_src)})")
    Excel.read(xlsx_src) # 엑셀 읽기
    logging.info("...완료")

    Excel.groupby() # 엑셀 데이터 groupby
    logging.info("...완료")

### 블로그 내용만 작성합니다.
def get_str_contents():
    content_str = ""
    groupby_data = read_xlsx()
    for name, data_list in groupby_data.items():
        logging.info(f"'{name}'의 데이터로 블로그 내용을 작성 중입니다.")
        content_str += f"#{name}\n\n"
        content_type = Excel.get("NAME")
        content_str += get_content_str(content_type, data_list) + "\n\n"

    logging.info(f"블로그 내용 작성이 완료되었습니다.\n\n{get_boxed_str(content_str)}\n")
    Work.work(Work.SAVE, Work_Content.BLOG_TXT)
    Work.ask()

### 블로그 내용 작성 및 썸네일 이미지를 생성합니다.
def get_all_contents():
    title_str = ""
    groupby_data = read_xlsx()

    title_str = Excel.get("THUMBNAIL_TXT") + "\n"
    for name, data_list in groupby_data.items():
        logging.info(f"'{name}'의 데이터로 썸네일 텍스트를 작성 중입니다.")
        title_str = get_title_str(name, data_list, title_str)
            
        content_type = Excel.get("NAME")
        content_str += get_content_str(content_type, data_list) + "\n\n"

    logging.info(f"블로그 내용 작성이 완료되었습니다.\n\n{get_boxed_str(content_str)}\n")
    Work.work(Work.SAVE, Work_Content.BLOG_TXT)
    Work.ask()

    save_thumbnail_txt(title_str)
    Work.work(Work.SAVE, Work_Content.THUMBNAIL_IMG)
    Work.ask()
    # ask(q_create_thumbnail, title_str)

### 썸네일 이미지를 생성합니다.
def get_img_content():
    groupby_data = read_xlsx()

    title_str = Excel.get("THUMBNAIL_TXT") + "\n"
    for name, data_list in groupby_data.items():
        logging.info(f"'{name}'의 데이터로 썸네일 텍스트를 작성 중입니다.")
        title_str = get_title_str(name, data_list, title_str)
    save_thumbnail_txt(title_str)
    create_thumbnail(title_str)


### 썸네일 이미지에 적을 텍스트를 가져옵니다.
def get_title_str(name, data_list, title_str):
    word_list = []
    title_str += f"#{name}\n"

    for word, _, answer in data_list:
        if name == Excel.CUR_SHEET.get("TITLE", "CONFUSING"):
            _, _, option_list = get_confusing_list(word, answer)  # [문제, [정답 문자열, ...], 보기1, 보기2]
            title_str += " ".join([f"#{option}" for option in option_list]) + "\n"
            continue

        word_list.append(f"#{word}")

    title_str += break_text_leq16(word_list, title_str)
    
    return title_str

def break_text_leq16(word_list, title_str="", max_width=16):
    """
    # 기호로 구분된 덩어리들을 연결하되, 한 줄이 max_width(16자)를 넘으려고 할 때
    # # 앞에서 줄바꿈을 하고, 윗줄 맨 뒤의 공백을 제거합니다.
    """
    cur_sentence = ""

    for word in word_list:
        if cur_sentence != "":
            temp = cur_sentence + " " + word
        else:
            temp = word

        if len(temp) < 17:
            cur_sentence = temp
        else:
            title_str += cur_sentence + "\n"
            cur_sentence = word

    if cur_sentence != "":
        title_str += cur_sentence

        
    return title_str


### 썸네일에 쓸 텍스트 저장
def save_thumbnail_txt(title_str):

    update_path = SRC.THUMBNAIL_UPDATED.ck_exist()
    log_path = SRC.THUMBNAIL_LOG.ck_exist()

    pre_thumbnail_txt = update_path.read_text(encoding="utf-8")  # 기존 파일 읽기
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]\n{pre_thumbnail_txt}\n{'-'*40}\n\n")

    # Work.work(Work.SAVE, Work_Content.THUMBNAIL_TXT)
    # Work.ask()
    update_path.write_text(title_str, encoding="utf-8")
    logging.info("썸네일에 쓸 텍스트 임시 저장 완료.")



try:
    Work.work(Work.SELECT_IN_RANGE, Work_Content.WORK)
    Work.ask()

except Exception as e:
    logging.exception(e)
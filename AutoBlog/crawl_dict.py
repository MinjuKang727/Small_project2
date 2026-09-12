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
import win32con
import pandas as pd
import pyperclip
import unicodedata
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

class URL(Enum):
    NAVER_HANJA_DICT = 'https://hanja.dict.naver.com/#/search?query=검색어'

    def get_url(self, word):
        return self.value.replace("검색어", word)

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

# def find_target(tags, word, mean=""):
#     logging.info("크롤링할 단어 선택 중...")
    
    # word0_hanja = tags[0].find_element(By.CSS_SELECTOR, 'a.link').text.strip()
    # word0_kor = tags[0].find_element(By.CSS_SELECTOR, '.mean').text.strip()  # 한자어 음독
    # word0_mean_tags = tags[0].find_elements(By.CSS_SELECTOR, 'p.mean')
    # word0_mean = "\n".join([mean_tag.text.strip() for mean_tag in word0_mean_tags])

    # if word0_kor != word:  # 검색 단어가 활용형일 경우, 첫번째 단어를 클릭
    #     q_choose_word = Question_Type.CHOOSE_WORD
    #     boxed_info = get_boxed_str(f"#{word0_hanja} #{word0_kor}\n{word0_mean}")
    #     q_dict = get_ask_dict(f"일치하는 한자가 존재하지 않습니다. 아래의 단어로 선택하시겠습니까?\n{boxed_info}\n(y:아래의 단어 선택, n:다른 단어 추가 조회)",
    #               [], ["y", "Y", "ㅛ"], ["n", "N", "ㅜ"])
    #     q_choose_word.set_by_dict(q_dict)
    #     choose_first = q_choose_word.reply(ask(q_choose_word))

    #     if choose_first:
    #         return tags[0].find_element(By.CSS_SELECTOR, '.origin a')
    # else:
    #     mean_token = mean.split()
    #     token_eq_rate = [0] * len(tags)
    #     max_eq_rate = [-1, -1]

    #     for i, tag in enumerate(tags):
    #         mean_tags = tag.find_elements(By.CSS_SELECTOR, 'p.mean')  # 한자어 뜻
    #         for mean_tag in mean_tags:
    #             try:
    #                 mean_txt = remove_hanja(mean_tag.text.strip())
    #             except Exception as e:
    #                 logging.exception(e)

    #             if mean_txt == mean:
    #                 return tag.find_element(By.CSS_SELECTOR, '.origin a')

    #             cur_tokens = mean_txt.split()
    #             exist = 0
    #             for token in mean_token:
    #                 if token in cur_tokens:
    #                     exist += 1

    #             token_eq_rate[i] = max(token_eq_rate[i], exist/len(cur_tokens))
    #         if token_eq_rate[i] > max_eq_rate[1]:
    #             max_eq_rate = [i, token_eq_rate[i]]

    #     return tags[max_eq_rate[0]].find_element(By.CSS_SELECTOR, '.origin a')

#### 한자 사전 검색 결과 dict 반환
def get_hanja_dict(word, mean=""):
    logging.info(f"'{word}' 사전 검색 중...")
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

        # 변경할 코드 (최대 10초 대기)
        try:
            tags = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '#searchPage_entry .row')
                )
            )
            
            # word_list = []
            # for tag in tags:
            #     info_list = []
            #     temp = ""
            #     for i, txt in enumerate(tag.text.strip().split("\n")[:-1]):
            #         if i == 1:
            #             continue
            #         pattern = r'^\d+\.$'

            #         if len(temp) > 0:
            #             txt = temp + txt
            #             temp = ""

            #         elif bool(re.fullmatch(pattern, txt)):
            #             temp = txt
            #             continue
                    
            #         info_list.append(txt)
            #     info_str = "\n".join(info_list)
            #     word_list.append(info_str)
            # logging.info(f"[TEST]\n{f"\n{'-'*100}\n".join([f"[{i+1}번]\n{get_boxed_str(word_info)}" for i, word_info in enumerate(word_list)])}\n\n\n")
            target_link = tags[1].find_element(By.CSS_SELECTOR, 'a')
                    
            # 4. 클릭 실행
            target_link.click()
    
            hanja_tag = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.component_entry')
                )
            )

            logging.info(f"[TEST] hanja_tag: {hanja_tag.text.strip().split("\n")[1:]}")
            mean_tag = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.mean_list.my_mean_list')
                )
            )
            logging.info(f"[TEST] mean_tag: {mean_tag.text.strip().split("\n")}")

        except Exception as e:
            logging.warning(f"'{word}'를 찾을 수 없어 TimeOut 에러 발생: {e}")

        
        # target_link = find_target(tags, word, mean)
        

        # # 4. 클릭 실행
        # target_link.click()

        # info_dict = {}
        # hanja_tag = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located(
        #         (By.CSS_SELECTOR, '.component_entry .word')
        #     )
        # )
        # hanja_txt = hanja_tag.text.strip()
        # dict_key_hanja = Sheet.get("HANJA_DICT_KEY", "HANJA")

        # info_dict[dict_key_hanja] = dict()
        # info_dict[dict_key_hanja][Sheet.get("HANJA_DICT_KEY", "HANJA_ALL")] = hanja_txt
        # info_dict[dict_key_hanja][Sheet.get("HANJA_DICT_KEY", "HANJA_SINGLE")] = []
        # word_tag = driver.find_element(By.CSS_SELECTOR, '.component_entry .mean')
        # word_txt = word_tag.text.strip()
        # info_dict[Sheet.get("HANJA_DICT_KEY", "WORD")] = word_txt
        # single_hanja_tags = WebDriverWait(driver, 10).until(
        #     EC.presence_of_all_elements_located(
        #         (By.CSS_SELECTOR, '.component_entry .hanja_item')
        #     )
        # )

        # for single_hanja_tag in single_hanja_tags:
        #     hanja = single_hanja_tag.find_element(By.CSS_SELECTOR, 'a')
        #     hanja_mean = single_hanja_tag.find_element(By.CSS_SELECTOR, '.mean_hanja')
        #     single_hanja_txt = hanja.text.strip()
        #     single_hanja_mean = hanja_mean.text.strip()
        #     info_dict[dict_key_hanja][Sheet.get("HANJA_DICT_KEY", "HANJA_SINGLE")].append(f"{single_hanja_txt} {single_hanja_mean}")

        # pronoun_tags = driver.find_elements(By.CSS_SELECTOR, '.component_entry .info_item')
        # info_dict[Sheet.get("HANJA_DICT_KEY", "PRON")] = []

        # for pronoun_tag in pronoun_tags:
        #     div_tags = pronoun_tag.find_elements(By.CSS_SELECTOR, 'div')
        #     pronoun_name = div_tags[0].text.strip()
        #     pronoun_txt = div_tags[1].text.strip()
        #     info_dict[Sheet.get("HANJA_DICT_KEY", "PRON")].append(pronoun_name)
        #     info_dict[pronoun_name] = pronoun_txt
        

        # mean_tags = driver.find_elements(By.CSS_SELECTOR, '.mean_desc')
        # info_dict[Sheet.get("HANJA_DICT_KEY", "MEAN")] = []
        # for mean_tag in mean_tags:
        #     mean_txt = remove_hanja(mean_tag.text.strip())
        #     info_dict[Sheet.get("HANJA_DICT_KEY", "MEAN")].append(mean_txt)

        # return info_dict

    finally:
        # 4. 브라우저 종료
        driver.quit()
        logging.info(f"크롤링 완료....(단어: {word})\n{'-'*40}")


get_hanja_dict("응되다")
get_hanja_dict("응고되다")
get_hanja_dict("먀우")
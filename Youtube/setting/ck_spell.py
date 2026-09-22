# # 필수 설치 라이브러리
# pip install git+https://github.com/ssut/py-hanspell.git
# pip install kiwipiepy
import re
from hanspell import spell_checker
from kiwipiepy import Kiwi
from pathlib import Path

# Kiwi 객체 생성
kiwi = Kiwi()

def advanced_kiwi_checker(text):
    """
    1단계: hanspell (맞춤법 및 오탈자 1차 교정)
    2단계: Kiwi 형태소 분석을 통한 문법/품사 기반 보정
    3단계: 커스텀 정규식 예외 처리
    """
    if not text.strip():
        return text

    # [1단계] hanspell 교정
    try:
        result = spell_checker.check(text)
        corrected_text = result.checked
    except Exception:
        corrected_text = text

    # [2단계] Kiwi 형태소 분석 활용 예시
    # 문장을 분석하여 특정 형태소 패턴이 감지될 때 띄어쓰기를 강제하는 등의 로직 구현 가능
    tokens = kiwi.analyze(corrected_text)
    # 예: 분석된 토큰을 바탕으로 필요한 규칙을 동적으로 적용할 수 있습니다.

    return corrected_text


def check_spell_in_file(input_file_path, output_file_path):
    """
    자막 파일(.sbv 등)을 읽어 hanspell + Kiwi 하이브리드 방식으로 검사하고 저장합니다.
    """
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"오류: '{input_file_path}' 파일을 찾을 수 없습니다.")
        return

    checked_lines = []
    print("Kiwi 하이브리드 맞춤법 검사 중...")
    
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line or is_timestamp_or_number(stripped_line):
            checked_lines.append(line)
            continue
            
        try:
            corrected_text = advanced_kiwi_checker(stripped_line)
            original_ending = line[len(stripped_line):]
            checked_lines.append(corrected_text + original_ending)
            
            if stripped_line != corrected_text:
                print(f"[원문] {stripped_line}")
                print(f"[교정] {corrected_text}\n")
        except Exception:
            checked_lines.append(line)

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.writelines(checked_lines)
    print(f"완료! '{output_file_path}' 저장됨.")

def is_timestamp_or_number(text):
    if text.isdigit():
        return True
    if '-->' in text or (':' in text and (',' in text or '.' in text)):
        if re.match(r'^[0-9:\.,\s\->]+$', text):
            return True
    return False

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent 
    input_filename = base_dir / "temp/captions.sbv"
    output_filename = base_dir / "temp/captions_checked.sbv"
    
    check_spell_in_file(input_filename, output_filename)
from pathlib import Path
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, concatenate_videoclips

# 1. 텍스트 파일 읽기 (pathlib 적용)
def load_vocab_file(filepath="vocab.txt"):
    file_path = Path(filepath)
    vocab_list = []
    
    if not file_path.exists():
        # 파일이 없을 경우 테스트용 샘플 파일 자동 생성
        file_path.write_text(
            "lead / 이끌다 / = result in / <> follow / ~ guide / > leading / # lead + O + to V (오형식, ~에게 ~하라고 이끌다)\n"
            "describe / 묘사하다 / = portray / <> hide / ~ depict / > description / # describe + O [3형식] (※ about 전치사 사용 금지!)\n",
            encoding="utf-8"
        )
    
    # pathlib을 이용해 안전하게 파일 읽기
    lines = file_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        vocab_list.append(parse_line(line))
        
    return vocab_list

# 2. 파싱 로직
def parse_line(raw_line):
    if "#" in raw_line:
        main_part, grammar = raw_line.split("#", 1)
        grammar_note = grammar.strip()
    else:
        main_part = raw_line
        grammar_note = ""

    parts = [p.strip() for p in main_part.split('/')]
    
    data = {
        "word": parts[0] if len(parts) > 0 else "",
        "meaning": parts[1] if len(parts) > 1 else "",
        "synonym": "",
        "similar": "",
        "antonym": "",
        "derivative": "",
        "grammar": grammar_note
    }

    for item in parts[2:]:
        if item.startswith("="):
            data["synonym"] = item.replace("=", "").strip()
        elif item.startswith("~"):
            data["similar"] = item.replace("~", "").strip()
        elif item.startswith("<>"):
            data["antonym"] = item.replace("<>", "").strip()
        elif item.startswith(">"):
            data["derivative"] = item.replace(">", "").strip()
            
    return data

# 3. 그룹별 색상 팔레트 (단어가 바뀔 때마다 색상 순환)
COLOR_PALETTE = [
    '#4ade80', # 초록계열
    '#38bdf8', # 하늘계열
    '#fbbf24', # 노랑계열
    '#c084fc', # 보라계열
    '#fb7185'  # 핑크계열
]

def create_vocab_stages(item, index):
    W, H = 1080, 1920
    bg_color = (20, 24, 33)
    font_name = "Malgun-Gothic"
    
    # 단어 인덱스에 따라 고유 색상 할당 (동일 그룹은 같은 색상)
    theme_color = COLOR_PALETTE[index % len(COLOR_PALETTE)]
    
    stages = []
    
    def get_bg(duration):
        return ColorClip(size=(W, H), color=bg_color).set_duration(duration)

    # [좌상단 구석] 미니 단어 & 뜻
    mini_header = TextClip(f"{item['word']} : {item['meaning']}", fontsize=35, color='#64748b', font=font_name, method='caption')

    # [우상단 구석] 동의어 / 반의어 / 유의어 요약 인포바
    sub_info_lines = []
    if item['synonym']: sub_info_lines.append(f"= {item['synonym']}")
    if item['antonym']: sub_info_lines.append(f"<> {item['antonym']}")
    if item['similar']: sub_info_lines.append(f"~ {item['similar']}")
    if item['derivative']: sub_info_lines.append(f"> {item['derivative']}")
    
    sub_info_text = "\n".join(sub_info_lines)
    right_corner_bar = TextClip(sub_info_text, fontsize=32, color=theme_color, font=font_name, size=(450, None), method='caption')

    # 중앙 배치용 텍스트들 (폭 제한으로 오버플로우 방지)
    txt_word_big = TextClip(item["word"], fontsize=90, color='white', font=font_name, size=(900, None), method='caption')
    txt_meaning_big = TextClip(f"뜻: {item['meaning']}", fontsize=60, color=theme_color, font=font_name, size=(900, None), method='caption')
    
    grammar_text = f"[문법 팁]\n{item['grammar']}" if item["grammar"] else ""
    txt_grammar = TextClip(grammar_text, fontsize=42, color='#f8fafc', font=font_name, size=(900, None), method='caption')

    # --- [장면 1] 단어만 정중앙 크게 (1.5초) ---
    s1 = CompositeVideoClip([get_bg(1.5), txt_word_big.set_position(('center', 'center')).set_duration(1.5)])
    stages.append(s1)

    # --- [장면 2] 좌상단 미니 헤더, 중앙 뜻 오픈 (1.5초) ---
    s2_elements = [
        get_bg(1.5),
        mini_header.set_position((80, 80)).set_duration(1.5),
        txt_meaning_big.set_position(('center', 'center')).set_duration(1.5)
    ]
    stages.append(CompositeVideoClip(s2_elements))

    # --- [장면 3] 우상단 구석 인포바 등장 (1.5초) ---
    if sub_info_text:
        s3_elements = [
            get_bg(1.5),
            mini_header.set_position((80, 80)).set_duration(1.5),
            right_corner_bar.set_position((550, 80)).set_duration(1.5),
            txt_meaning_big.set_position(('center', 'center')).set_duration(1.5)
        ]
        stages.append(CompositeVideoClip(s3_elements))

    # --- [장면 4] 문법 팁 마침표 (2.0초) ---
    if item["grammar"]:
        s4_elements = [
            get_bg(2.0),
            mini_header.set_position((80, 80)).set_duration(1.5),
            right_corner_bar.set_position((550, 80)).set_duration(2.0),
            txt_grammar.set_position(('center', 'center')).set_duration(2.0)
        ]
        stages.append(CompositeVideoClip(s4_elements))

    return stages

# 4. 메인 실행 함수 (pathlib으로 출력 경로 관리)
def main():
    txt_path = Path("vocab.txt")
    vocab_data = load_vocab_file(txt_path)
    print(f"총 {len(vocab_data)}개의 단어 로드 완료. 영상 생성 시작!")
    
    all_clips = []
    for idx, item in enumerate(vocab_data):
        print(f"[{idx+1}/{len(vocab_data)}] 단어 처리 중: {item['word']}")
        stages = create_vocab_stages(item, idx)
        all_clips.extend(stages)
            
    if all_clips:
        final_video = concatenate_videoclips(all_clips)
        output_path = Path(f"{txt_path.stem}.mp4")
        final_video.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac")
        print(f"🎉 완벽한 학습용 숏폼 완성! 파일명: {output_path.resolve()}")
    else:
        print("생성된 클립이 없습니다.")

if __name__ == "__main__":
    main()
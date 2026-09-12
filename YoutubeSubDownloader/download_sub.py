from datetime import timedelta
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi

# 1. 설정
video_id = "JmiZ1ykXedM"  # 유튜브 URL에서 v= 뒤의 ID 값
output_srt_path = Path(f"C:/Users/KJY/Documents/Programming/YoutubeSubDownloader/subs/{video_id}.srt")  # 저장할 자막 파일 이름


# 초를 SRT 시간 포맷 (00:00:00,000) 문자열로 바꿔주는 함수
def format_time(seconds: float) -> str:
  td = timedelta(seconds=seconds)
  hours = int(td.seconds // 3600)
  minutes = int((td.seconds % 3600) // 60)
  secs = int(td.seconds % 60)
  milliseconds = int(td.microseconds // 1000)
  return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


try:
  print("유튜브 자막을 가져오는 중...")
  ytt_api = YouTubeTranscriptApi()
  transcript_list = ytt_api.fetch(video_id, languages=["ko"])

  srt_lines = []

  for i, entry in enumerate(transcript_list, start=1):
    start_sec = entry.start
    # duration이 있다면 끝나는 시간 계산, 없으면 대략 2초 뒤로 설정
    end_sec = (
        start_sec + entry.duration
        if hasattr(entry, "duration")
        else start_sec + 2.0
    )
    text = entry.text.strip()

    start_str = format_time(start_sec)
    end_str = format_time(end_sec)

    # SRT 표준 포맷 블록 생성
    srt_block = f"{i}\n{start_str} --> {end_str}\n{text}\n"
    srt_lines.append(srt_block)

  # 파일로 저장 (UTF-8 인코딩)
  output_srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
  print(f"자막 파일 생성 완료: {output_srt_path.resolve()}")

except Exception as e:
  print(f"자막을 불러오거나 저장하는 중 오류 발생: {e}")
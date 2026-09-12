import json
import os

class KeywordManager:
    def __init__(self, filename="used_keywords.json"):
        self.filename = filename
        self.used_data = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_to_file(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.used_data, f, ensure_ascii=False, indent=4)

    def get_unique_keywords_and_explain(self, course_title, main_text):
        """
        AI가 추출한 키워드 중 중복되지 않은 것을 선별하고 설명을 생성합니다.
        """
        # 1. AI API(Gemini/GPT 등) 연동 지점
        # 실제로는 여기서 main_text를 AI에게 보내 키워드 리스트를 받아옵니다.
        # 예시: extracted_from_ai = ai_api.extract(main_text)
        
        # [테스트용 가상 추출 결과] 실제로는 강의 내용에 따라 AI가 보낸 리스트가 들어옵니다.
        all_extracted = ["Spring Boot", "Docker", "JPA", "AWS EC2", "MySQL", "Redis", "CI/CD"]
        
        if course_title not in self.used_data:
            self.used_data[course_title] = []

        # 중복 제외 필터링
        used_list = self.used_data[course_title]
        new_keywords = [k for k in all_extracted if k not in used_list]

        # 만약 모두 사용했다면 초기화 후 다시 시작
        if not new_keywords:
            new_keywords = all_extracted
            self.used_data[course_title] = []

        # 이번에 사용할 3개 선택
        selected = new_keywords[:3]
        
        # 2. 선택된 키워드별 설명 생성 (이 부분도 AI API가 생성하도록 구성)
        explanation = f"### 📚 [{course_title}] 핵심 개념 정리\n"
        for k in selected:
            # desc = ai_api.explain(k)
            desc = f"{k}에 대한 AI의 동적 설명입니다." 
            explanation += f"- **{k}**: {desc}\n"
        
        # 사용 기록 업데이트
        self.used_data[course_title].extend(selected)
        self.save_to_file()
        
        return explanation
import pandas as pd

def read_xlsx(xlsx_src):
    excel_data = pd.read_excel(xlsx_src, sheet_name=None)  # 딕셔너리 형식으로 데이터 전부 가져오기: {시트이름: DataFrame}

    # 각 시트의 데이터프레임에 접근
    sheet_name_list = list(excel_data.keys())
    sheet_data = ""
    if len(sheet_name_list) == 1:
        sheet_data = excel_data[sheet_name_list[0]]
    else:
        sheet_names_str = "\n".join([f"{i + 1}. {name}" for i, name in enumerate(sheet_name_list)])
        select_sheet_num = -1

        while select_sheet_num not in range(len(sheet_name_list)) :
            select = input(f"데이터를 읽을 시트를 선택해 주세요.(번호를 입력해 주세요)\n{sheet_names_str}\n> ")
            try:
                int_select = int(select)
                if int_select - 1 in range(len(sheet_name_list)):
                    select_sheet_num = int_select - 1
            except ValueError:
                print(f"입력값은 1 ~ {len(sheet_name_list)} 사이의 자연수이어야 합니다.")

        sheet_name = sheet_name_list[select_sheet_num]
        sheet_data = excel_data[sheet_name]

    # print(sheet_data)
    groupby_data = sheet_data.groupby("구분").apply(lambda x: x[['단어', '뜻']].fillna('').to_dict('records'))
    for name, data in groupby_data.items():
        print(name, data)
        for d in data:
            for word, mean in d.items():
                print(word, mean)

xlsx_src = "./data/data.xlsx"
read_xlsx(xlsx_src)
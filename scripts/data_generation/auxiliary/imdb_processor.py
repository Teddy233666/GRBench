import os
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_ROOT = Path(os.environ.get("GRBENCH_AUX_RAW_ROOT", REPO_ROOT / "data" / "raw"))
PROCESSED_ROOT = Path(
    os.environ.get("GRBENCH_AUX_PROCESSED_ROOT", REPO_ROOT / "data" / "processed" / "auxiliary")
)
IMDB_OUTPUT = str(PROCESSED_ROOT / "imdb")

# 定义原始数据文件路径
IMDB_RAW = RAW_ROOT / "IMDB"
CAST_INFO_PATH = str(IMDB_RAW / "cast_info.csv")
CHAR_NAME_PATH = str(IMDB_RAW / "char_name.csv")
COMP_CAST_TYPE_PATH = str(IMDB_RAW / "comp_cast_type.csv")
COMPANY_NAME_PATH = str(IMDB_RAW / "company_name.csv")
COMPANY_TYPE_PATH = str(IMDB_RAW / "company_type.csv")
COMPLETE_CAST_PATH = str(IMDB_RAW / "complete_cast.csv")
INFO_TYPE_PATH = str(IMDB_RAW / "info_type.csv")
KEYWORD_PATH = str(IMDB_RAW / "keyword.csv")
KIND_TYPE_PATH = str(IMDB_RAW / "kind_type.csv")
LINK_TYPE_PATH = str(IMDB_RAW / "link_type.csv")
MOVIE_COMPANIES_PATH = str(IMDB_RAW / "movie_companies.csv")
MOVIE_INFO_PATH = str(IMDB_RAW / "movie_info.csv")
MOVIE_INFO_IDX_PATH = str(IMDB_RAW / "movie_info_idx.csv")
MOVIE_KEYWORD_PATH = str(IMDB_RAW / "movie_keyword.csv")
MOVIE_LINK_PATH = str(IMDB_RAW / "movie_link.csv")
NAME_PATH = str(IMDB_RAW / "name.csv")
PERSON_INFO_PATH = str(IMDB_RAW / "person_info.csv")
ROLE_TYPE_PATH = str(IMDB_RAW / "role_type.csv")
TITLE_PATH = str(IMDB_RAW / "title.csv")
AKA_NAME_PATH = str(IMDB_RAW / "aka_name.csv")
AKA_TITLE_PATH = str(IMDB_RAW / "aka_title.csv")


def strip_unusual_lt(s: str) -> str:
    """移除不常见的换行符和制表符"""
    if s is None:
        return ''
    return s.translate(str.maketrans({
        '\u2028': '',  # LS
        '\u2029': '',  # PS
        '\n': '',
        '\r': '',
        '\t': ' '
    })).strip()


def read_csv_file(file_path, expected_columns=None):
    """读取CSV文件并返回数据行"""
    rows = []
    if not os.path.exists(file_path):
        print(f"Warning: File {file_path} does not exist")
        return rows

    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as fin:
            reader = csv.reader(fin)
            # 跳过标题行
            next(reader, None)
            for row in reader:
                if expected_columns and len(row) < expected_columns:
                    continue
                rows.append([strip_unusual_lt(field) for field in row])
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return rows


# 1. Title实体表
def T_title():
    output_file = os.path.join(IMDB_OUTPUT, 'T_title.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(TITLE_PATH, expected_columns=12)  # 增加预期列数
    processed_rows = []

    for row in rows:
        if len(row) >= 12:
            id_val = row[0]
            title = row[1]  # 添加title字段
            kind_id = row[3]
            series_years = row[10]
            production_year = row[4]
            season_nr = row[8]
            episode_nr = row[9]

            processed_rows.append([id_val, title, kind_id, series_years, production_year, season_nr, episode_nr])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'title', 'kind_id', 'series_years', 'production_year', 'season_nr', 'episode_nr'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 2. aka_title实体表
def T_aka_title():
    output_file = os.path.join(IMDB_OUTPUT, 'T_aka_title.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(AKA_TITLE_PATH, expected_columns=12)
    processed_rows = []

    for row in rows:
        if len(row) >= 12:
            id_val = row[0]
            movie_id = row[1]
            title = row[2]
            kind_id = row[4]
            production_year = row[5]
            season_nr = row[8]
            episode_nr = row[9]

            processed_rows.append([id_val, movie_id, title, kind_id, production_year, season_nr, episode_nr])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'movie_id', 'title', 'kind_id', 'production_year', 'season_nr', 'episode_nr'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 3. Name实体表
def T_name():
    output_file = os.path.join(IMDB_OUTPUT, 'T_name.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(NAME_PATH, expected_columns=9)
    processed_rows = []

    for row in rows:
        if len(row) >= 9:
            id_val = row[0]
            name = row[1]
            gender = row[4]

            processed_rows.append([id_val, name, gender])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name', 'gender'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 4. aka_name实体表
def T_aka_name():
    output_file = os.path.join(IMDB_OUTPUT, 'T_aka_name.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(AKA_NAME_PATH, expected_columns=8)
    processed_rows = []

    for row in rows:
        if len(row) >= 8:
            id_val = row[0]
            person_id = row[1]
            name = row[2]

            processed_rows.append([id_val, person_id, name])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'person_id', 'name'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 5. kind_type实体表
def T_kind_type():
    output_file = os.path.join(IMDB_OUTPUT, 'T_kind_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(KIND_TYPE_PATH, expected_columns=2)
    processed_rows = []

    for row in rows:
        if len(row) >= 2:
            id_val = row[0]
            kind = row[1]

            processed_rows.append([id_val, kind])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'kind'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 6. link_type实体表
def T_link_type():
    output_file = os.path.join(IMDB_OUTPUT, 'T_link_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(LINK_TYPE_PATH, expected_columns=2)
    processed_rows = []

    for row in rows:
        if len(row) >= 2:
            id_val = row[0]
            link = row[1]

            processed_rows.append([id_val, link])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'link'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 7. char_name实体表
def T_char_name():
    output_file = os.path.join(IMDB_OUTPUT, 'T_char_name.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(CHAR_NAME_PATH, expected_columns=7)
    processed_rows = []

    for row in rows:
        if len(row) >= 7:
            id_val = row[0]
            name = row[1]

            processed_rows.append([id_val, name])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 8. comp_cast_type实体表
def T_comp_cast_type():
    output_file = os.path.join(IMDB_OUTPUT, 'T_comp_cast_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(COMP_CAST_TYPE_PATH, expected_columns=2)
    processed_rows = []

    for row in rows:
        if len(row) >= 2:
            id_val = row[0]
            kind = row[1]

            processed_rows.append([id_val, kind])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'kind'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 9. complete_cast实体表
def T_complete_cast():
    output_file = os.path.join(IMDB_OUTPUT, 'T_complete_cast.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(COMPLETE_CAST_PATH, expected_columns=4)
    processed_rows = []

    for row in rows:
        if len(row) >= 4:
            id_val = row[0]
            movie_id = row[1]
            subject_id = row[2]
            status_id = row[3]

            processed_rows.append([id_val, movie_id, subject_id, status_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'movie_id', 'subject_id', 'status_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 10. company_name实体表
def T_company_name():
    output_file = os.path.join(IMDB_OUTPUT, 'T_company_name.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(COMPANY_NAME_PATH, expected_columns=7)
    processed_rows = []

    for row in rows:
        if len(row) >= 7:
            id_val = row[0]
            name = row[1]
            country_code = row[2]

            processed_rows.append([id_val, name, country_code])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name', 'country_code'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 11. company_type实体表
def T_company_type():
    output_file = os.path.join(IMDB_OUTPUT, 'T_company_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(COMPANY_TYPE_PATH, expected_columns=2)
    processed_rows = []

    for row in rows:
        if len(row) >= 2:
            id_val = row[0]
            kind = row[1]

            processed_rows.append([id_val, kind])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'kind'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 12. info_type实体表
def T_info_type():
    output_file = os.path.join(IMDB_OUTPUT, 'T_info_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(INFO_TYPE_PATH, expected_columns=2)
    processed_rows = []

    for row in rows:
        if len(row) >= 2:
            id_val = row[0]
            info = row[1]

            processed_rows.append([id_val, info])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'info'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 13. keyword实体表
def T_keyword():
    output_file = os.path.join(IMDB_OUTPUT, 'T_keyword.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(KEYWORD_PATH, expected_columns=3)
    processed_rows = []

    for row in rows:
        if len(row) >= 3:
            id_val = row[0]
            keyword = row[1]

            processed_rows.append([id_val, keyword])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'keyword'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 14. movie_info实体表
def T_movie_info():
    output_file = os.path.join(IMDB_OUTPUT, 'T_movie_info.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_INFO_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            id_val = row[0]
            info = row[3]
            note = row[4]
            # 第3个字段是info_type_id，但我们不需要它，因为要求中没有提到

            processed_rows.append([id_val, info, note])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'info', 'note'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 15. movie_info_idx实体表
def T_movie_info_idx():
    output_file = os.path.join(IMDB_OUTPUT, 'T_movie_info_idx.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_INFO_IDX_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            id_val = row[0]
            info = row[3]
            note = row[4]
            # 第3个字段是info_type_id，但我们不需要它，因为要求中没有提到

            processed_rows.append([id_val, info, note])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'info', 'note'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 16. movie_link实体表
def T_movie_link():
    output_file = os.path.join(IMDB_OUTPUT, 'T_movie_link.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_LINK_PATH, expected_columns=4)
    processed_rows = []

    for row in rows:
        if len(row) >= 4:
            id_val = row[0]
            movie_id = row[1]
            linked_movie_id = row[2]
            link_type_id = row[3]

            processed_rows.append([id_val, movie_id, linked_movie_id, link_type_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'movie_id', 'linked_movie_id', 'link_type_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 17. person_info实体表
def T_person_info():
    output_file = os.path.join(IMDB_OUTPUT, 'T_person_info.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(PERSON_INFO_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            id_val = row[0]
            info = row[3]
            note = row[4]

            processed_rows.append([id_val, info, note])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'info', 'note'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 18. role_type实体表
def T_role_type():
    output_file = os.path.join(IMDB_OUTPUT, 'T_role_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(ROLE_TYPE_PATH, expected_columns=2)
    processed_rows = []

    for row in rows:
        if len(row) >= 2:
            id_val = row[0]
            role = row[1]

            processed_rows.append([id_val, role])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'role'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 19. participate_in实体表
def T_participate_in():
    output_file = os.path.join(IMDB_OUTPUT, 'T_participate_in.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(CAST_INFO_PATH, expected_columns=6)
    processed_rows = []

    for row in rows:
        if len(row) >= 6:
            id_val = row[0]
            person_id = row[1]
            role_type_id = row[6]
            movie_id = row[2]

            processed_rows.append([id_val, person_id, role_type_id, movie_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'person_id', 'role_type_id', 'movie_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 20. movie_companies实体表
def T_movie_companies():
    output_file = os.path.join(IMDB_OUTPUT, 'T_movie_companies.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_COMPANIES_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            id_val = row[0]
            movie_id = row[1]
            company_id = row[2]
            company_type_id = row[3]

            processed_rows.append([id_val, movie_id, company_id, company_type_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'movie_id', 'company_id', 'company_type_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# ========== 边表构造 ==========

# 1. movie_info边表
def E_movie_info():
    output_file = os.path.join(IMDB_OUTPUT, 'E_movie_info.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_INFO_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            info_id = row[0]  # id取别名为info_id
            movie_id = row[1]  # 假设movie_id在第4个位置

            processed_rows.append([info_id, movie_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['info_id', 'movie_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 2. movie_infox边表 (这里假设movie_infox是movie_info_idx的别名)
def E_movie_infox():
    output_file = os.path.join(IMDB_OUTPUT, 'E_movie_infox.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_INFO_IDX_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            infox_id = row[0]  # id取别名为infox_id
            movie_id = row[1]  # 假设movie_id在第4个位置

            processed_rows.append([infox_id, movie_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['infox_id', 'movie_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 3. person_info边表
def E_person_info():
    output_file = os.path.join(IMDB_OUTPUT, 'E_person_info.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(PERSON_INFO_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            info_id = row[0]  # id取别名为info_id
            person_id = row[1]  # person_id在第2个位置

            processed_rows.append([info_id, person_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['info_id', 'person_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 4. Played边表
def E_Played():
    output_file = os.path.join(IMDB_OUTPUT, 'E_Played.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(CAST_INFO_PATH, expected_columns=6)
    processed_rows = []

    for row in rows:
        if len(row) >= 6:
            person_id = row[1]
            person_role_id = row[3]  # 假设person_role_id在第4个位置

            processed_rows.append([person_id, person_role_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['person_id', 'person_role_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 5. Has_role_type边表
def E_Has_role_type():
    output_file = os.path.join(IMDB_OUTPUT, 'E_Has_role_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(CAST_INFO_PATH, expected_columns=6)
    processed_rows = []

    for row in rows:
        if len(row) >= 6:
            person_role_id = row[3]  # 假设person_role_id在第4个位置
            role_type_id = row[6]

            processed_rows.append([person_role_id, role_type_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['person_role_id', 'role_type_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 6. In_movie边表
def E_In_movie():
    output_file = os.path.join(IMDB_OUTPUT, 'E_In_movie.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(CAST_INFO_PATH, expected_columns=6)
    processed_rows = []

    for row in rows:
        if len(row) >= 6:
            person_role_id = row[3]  # 假设person_role_id在第4个位置
            movie_id = row[2]  # 假设movie_id在第1个位置

            processed_rows.append([person_role_id, movie_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['person_role_id', 'movie_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 7. Movie_keyword边表
def E_Movie_keyword():
    output_file = os.path.join(IMDB_OUTPUT, 'E_Movie_keyword.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_KEYWORD_PATH, expected_columns=3)
    processed_rows = []

    for row in rows:
        if len(row) >= 3:
            movie_id = row[1]
            keyword_id = row[2]

            processed_rows.append([movie_id, keyword_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['movie_id', 'keyword_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 8. Movie_info_Of_type边表 (来自movie_info)
def E_Movie_info_Of_type():
    output_file = os.path.join(IMDB_OUTPUT, 'E_Movie_info_Of_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_INFO_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            info_id = row[0]  # id取别名为info_id
            info_type_id = row[ 2]  # 假设info_type_id在第4个位置

            processed_rows.append([info_id, info_type_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['info_id', 'info_type_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 9. Movie_infox_Of_type边表 (来自movie_info_idx)
def E_Movie_infox_Of_type():
    output_file = os.path.join(IMDB_OUTPUT, 'E_Movie_infox_Of_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(MOVIE_INFO_IDX_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            infox_id = row[0]  # id取别名为infox_id
            info_type_id = row[2]  # 假设info_type_id在第4个位置

            processed_rows.append([infox_id, info_type_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['infox_id', 'info_type_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 10. Person_info_of_type边表
def E_Person_info_of_type():
    output_file = os.path.join(IMDB_OUTPUT, 'E_Person_info_of_type.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = read_csv_file(PERSON_INFO_PATH, expected_columns=5)
    processed_rows = []

    for row in rows:
        if len(row) >= 5:
            info_id = row[0]  # id取别名为info_id
            info_type_id = row[2]  # info_type_id在第3个位置

            processed_rows.append([info_id, info_type_id])

    os.makedirs(IMDB_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['info_id', 'info_type_id'])

        for row in processed_rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


if __name__ == '__main__':
    # 创建实体表
    T_title()
    T_aka_title()
    T_name()
    T_aka_name()
    T_kind_type()
    T_link_type()
    T_char_name()
    T_comp_cast_type()
    T_complete_cast()
    T_company_name()
    T_company_type()
    T_info_type()
    T_keyword()
    T_movie_info()
    T_movie_info_idx()
    T_movie_link()
    T_person_info()
    T_role_type()
    T_participate_in()
    T_movie_companies()

    # 创建边表
    E_movie_info()
    E_movie_infox()
    E_person_info()
    E_Played()
    E_Has_role_type()
    E_In_movie()
    E_Movie_keyword()
    E_Movie_info_Of_type()
    E_Movie_infox_Of_type()
    E_Person_info_of_type()

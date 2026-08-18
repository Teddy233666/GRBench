import os
import csv
import json

MOOC_OUTPUT     = '../datasets/sf1/mooc/'

CONCEPT_PATH    = '../raw_data/MOOCCube/entities/concept.json'
COURSE_PATH     = '../raw_data/MOOCCube/entities/course.json'
PAPER_PATH      = '../raw_data/MOOCCube/entities/paper.json'
SCHOOL_PATH     = '../raw_data/MOOCCube/entities/school.json'
TEACHER_PATH    = '../raw_data/MOOCCube/entities/teacher.json'
USER_PATH       = '../raw_data/MOOCCube/entities/user.json'
VIDEO_PATH      = '../raw_data/MOOCCube/entities/video.json'

CONCEPT_PAPER_PATH  = '../raw_data/MOOCCube/relations/concept-paper.json'
SCHOOL_COURSE_PATH  = '../raw_data/MOOCCube/relations/school-course.json'
TEACHER_COURSE_PATH = '../raw_data/MOOCCube/relations/teacher-course.json'
VIDEO_CONCEPT_PATH  = '../raw_data/MOOCCube/relations/video-concept.json'
USER_COURSE_PATH    = '../raw_data/MOOCCube/relations/user-course.json'
FIELD_PATH          = '../raw_data/MOOCCube/relations/concept-field.json'
COURSE_CONCEPT_PATH = '../raw_data/MOOCCube/relations/course-concept.json'
COURSE_VIDEO_PATH   = '../raw_data/MOOCCube/relations/course-video.json'
USER_VIDEO_PATH     = '../raw_data/MOOCCube/relations/user-video.json'
SCHOOL_TEACHER_PATH = '../raw_data/MOOCCube/relations/school-teacher.json'


# remove the redundant LS and PS
def strip_unusual_lt(s: str) -> str:
    return s.translate(str.maketrans({
        '\u2028': '',  # LS
        '\u2029': '',  # PS
        '\n': '',
        '\r': '',
        '\t': ''
    }))


# 1. table: field(id, name), 24 tuples
def T_field():
    output_file = os.path.join(MOOC_OUTPUT, 'T_field.csv')
    seen = set()

    print(f"==== Start generating file: {output_file} ====")
    with open(FIELD_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue

            field_id = strip_unusual_lt(parts[1].strip())
            name_part = field_id.split('_', 3)
            if len(name_part) < 4:
                continue
            field_name = strip_unusual_lt(name_part[3])

            seen.add((field_id, field_name))

    os.makedirs(MOOC_OUTPUT, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name'])
        writer.writerows(sorted(seen))

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 2. table: paper(id, title. year, num_citation, doi, concept_id)
def T_paper():
    output_file = os.path.join(MOOC_OUTPUT, 'T_paper.csv')
    print(f"==== Start generating file: {output_file} ====")

    # Step 1: read concept-paper
    paper_to_concept = {}
    with open(CONCEPT_PAPER_PATH, 'r', encoding='utf-8') as fcp:
        for line in fcp:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            concept_id, paper_id = parts
            if paper_id not in paper_to_concept:
                paper_to_concept[paper_id] = strip_unusual_lt(concept_id)

    # Step 2: read paper.json
    rows = []
    with open(PAPER_PATH, 'r', encoding='utf-8') as fpaper:
        for line in fpaper:
            line = line.strip()
            if not line:
                continue
            try:
                paper = json.loads(line)
            except json.JSONDecodeError:
                continue

            pid   = strip_unusual_lt(paper.get('id', ''))
            title = strip_unusual_lt(paper.get('title', '').strip())
            year  = paper.get('year', '')
            num_citation = paper.get('num_citation', '')
            doi   = strip_unusual_lt(paper.get('doi', '').strip())
            concept_id = strip_unusual_lt(paper_to_concept.get(pid, ''))

            rows.append([pid, title, year, num_citation, doi, concept_id])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()
    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'title', 'year', 'num_citation', 'doi', 'concept_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 3. table: concept(id, name, en, explanation)
def T_concept():
    output_file = os.path.join(MOOC_OUTPUT, 'T_concept.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = []
    with open(CONCEPT_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                concept = json.loads(line)
            except json.JSONDecodeError:
                continue

            cid         = strip_unusual_lt(concept.get('id', '').strip())
            name        = strip_unusual_lt(concept.get('name', '').strip())
            en          = strip_unusual_lt(concept.get('en', '').strip()) if 'en' in concept else ''
            explanation = strip_unusual_lt(concept.get('explanation', '').strip()) if 'explanation' in concept else ''

            rows.append([cid, name, en, explanation])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name', 'en', 'explanation'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 4. table: course(id, name, school_id, teacher_id, about)
def T_course():
    output_file = os.path.join(MOOC_OUTPUT, 'T_course.csv')
    print(f"==== Start generating file: {output_file} ====")

    # Step 0: build mappings from relations
    course_to_school = {}
    if os.path.exists(SCHOOL_COURSE_PATH):
        with open(SCHOOL_COURSE_PATH, 'r', encoding='utf-8') as fsc:
            for line in fsc:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) != 2:
                    parts = line.split()
                    if len(parts) != 2:
                        continue
                school_id, course_id = parts
                course_id = course_id.strip()
                school_id = strip_unusual_lt(school_id.strip())
                if course_id not in course_to_school:
                    course_to_school[course_id] = school_id

    course_to_teacher = {}
    if os.path.exists(TEACHER_COURSE_PATH):
        with open(TEACHER_COURSE_PATH, 'r', encoding='utf-8') as ftc:
            for line in ftc:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) != 2:
                    parts = line.split()
                    if len(parts) != 2:
                        continue
                teacher_id, course_id = parts
                course_id = course_id.strip()
                teacher_id = strip_unusual_lt(teacher_id.strip())
                if course_id not in course_to_teacher:
                    course_to_teacher[course_id] = teacher_id

    # Step 1: read course.json and combine
    rows = []
    with open(COURSE_PATH, 'r', encoding='utf-8') as fcourse:
        for line in fcourse:
            line = line.strip()
            if not line:
                continue
            try:
                course = json.loads(line)
            except json.JSONDecodeError:
                continue

            cid = strip_unusual_lt(course.get('id', ''))
            name = strip_unusual_lt(course.get('name', ''))
            about = strip_unusual_lt(course.get('about', ''))

            # look up school_id and teacher_id by course id
            school_id = strip_unusual_lt(course_to_school.get(cid, ''))
            teacher_id = strip_unusual_lt(course_to_teacher.get(cid, ''))

            rows.append([cid, name, school_id, teacher_id, about])

    # Step 2: write csv with dedup
    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()
    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name', 'school_id', 'teacher_id', 'about'])
        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 5. table: school(id, name, about)
def T_school():
    output_file = os.path.join(MOOC_OUTPUT, 'T_school.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = []
    with open(SCHOOL_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                school = json.loads(line)
            except json.JSONDecodeError:
                continue

            sid   = strip_unusual_lt(school.get('id', '').strip())
            name  = strip_unusual_lt(school.get('name', '').strip())
            about = strip_unusual_lt(school.get('about', '').strip())

            rows.append([sid, name, about])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name', 'about'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 6. table: teacher(id, name, about)
def T_teacher():
    output_file = os.path.join(MOOC_OUTPUT, 'T_teacher.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = []
    with open(TEACHER_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                teacher = json.loads(line)
            except json.JSONDecodeError:
                continue

            tid   = strip_unusual_lt(teacher.get('id', '').strip())
            name  = strip_unusual_lt(teacher.get('name', '').strip())
            about = strip_unusual_lt(teacher.get('about', '').strip())

            rows.append([tid, name, about])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name', 'about'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 7. table: user(id, name)
def T_user():
    output_file = os.path.join(MOOC_OUTPUT, 'T_user.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = []
    with open(USER_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                user = json.loads(line)
            except json.JSONDecodeError:
                continue

            uid = strip_unusual_lt(user.get('id', ''))
            name = strip_unusual_lt(user.get('name', ''))
            rows.append([uid, name])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name'])
        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 8. table: video(id, name)
def T_video():
    output_file = os.path.join(MOOC_OUTPUT, 'T_video.csv')
    print(f"==== Start generating file: {output_file} ====")

    rows = []
    with open(VIDEO_PATH, 'r', encoding='utf-8') as fvideo:
        for line in fvideo:
            line = line.strip()
            if not line:
                continue
            try:
                video = json.loads(line)
            except json.JSONDecodeError:
                continue

            vid  = strip_unusual_lt(video.get('id', ''))
            name = strip_unusual_lt(video.get('name', '').strip())

            rows.append([vid, name])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()
    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['id', 'name'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 9. table: user_crouse_info(user_id, course_id)
def T_user_course_info():
    output_file = os.path.join(MOOC_OUTPUT, 'T_user_course_info.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(USER_COURSE_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            user_id, course_id = parts
            rows.append([user_id.strip(), course_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['user_id', 'course_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 10. table: video_concept_info(video_id, concept_id)
def T_video_concept_info():
    output_file = os.path.join(MOOC_OUTPUT, 'T_video_concept_info.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(VIDEO_CONCEPT_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            video_id, concept_id = parts
            rows.append([video_id.strip(), concept_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['video_id', 'concept_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 11. edge table: in_field(concept_id, field_id)
def E_in_field():
    output_file = os.path.join(MOOC_OUTPUT, 'E_in_field.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(FIELD_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            concept_id, field_id = parts
            rows.append([concept_id.strip(), field_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['concept_id', 'field_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 12. edge table: covers(course_id, concept_id)
def E_covers():
    output_file = os.path.join(MOOC_OUTPUT, 'E_covers.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(COURSE_CONCEPT_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            course_id, concept_id = parts
            rows.append([course_id.strip(), concept_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['course_id', 'concept_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 13. edge table: contains(course_id, video_id)
def E_contains():
    output_file = os.path.join(MOOC_OUTPUT, 'E_contains.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(COURSE_VIDEO_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            course_id, video_id = parts
            rows.append([course_id.strip(), video_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['course_id', 'video_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 14. edge table: watched(user_id, video_id)
def E_watched():
    output_file = os.path.join(MOOC_OUTPUT, 'E_watched.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(USER_VIDEO_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            user_id, video_id = parts
            rows.append([user_id.strip(), video_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['user_id', 'video_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


# 15. edge table: employs(school_id, teacher_id)
def E_employs():
    output_file = os.path.join(MOOC_OUTPUT, 'E_employs.csv')
    print(f"Start generating file: {output_file}")

    rows = []
    with open(SCHOOL_TEACHER_PATH, 'r', encoding='utf-8') as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            school_id, teacher_id = parts
            rows.append([school_id.strip(), teacher_id.strip()])

    os.makedirs(MOOC_OUTPUT, exist_ok=True)
    seen = set()

    with open(output_file, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        writer.writerow(['school_id', 'teacher_id'])

        for row in rows:
            row_tuple = tuple(row)
            if row_tuple not in seen:
                writer.writerow(row)
                seen.add(row_tuple)

    print(f"File generated: {output_file}")
    print(f"{len(seen)} unique records have been written.")


if __name__ == '__main__':
    T_field()
    T_paper()
    T_concept()
    T_school()
    T_teacher()
    T_course()
    T_user()
    T_video()
    T_user_course_info()
    T_video_concept_info()
    E_in_field()
    E_covers()
    E_contains()
    E_watched()
    E_employs()

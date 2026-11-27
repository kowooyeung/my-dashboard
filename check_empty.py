# check_empty.py : app.py에 '0건 안내'가 들어 있는지 검사하는 파일
# Claude Code가 app.py를 고칠 때마다 hook이 자동으로 실행함
# (json, sys, os는 파이썬에 기본으로 들어 있는 도구라 따로 설치할 필요 없음)

import json  # hook이 보내 주는 정보(JSON 글자)를 읽는 도구
import sys  # 검사 결과(통과/실패)를 Claude Code에 알려 주는 도구
import os  # 파일 위치를 찾는 도구

# 1) 방금 고친 파일이 app.py인지 확인 (다른 파일을 고쳤으면 검사 안 함)
try:
    hook_info = json.load(sys.stdin)  # hook이 넘겨준 정보 읽기
    edited_file = hook_info.get("tool_input", {}).get("file_path", "")  # 고친 파일 경로
except Exception:
    edited_file = "app.py"  # 정보가 없으면(직접 실행했을 때) 그냥 app.py를 검사

if not edited_file.endswith("app.py"):  # app.py가 아니면
    sys.exit(0)  # 검사 없이 통과 (0 = 문제없음)

# 2) app.py 읽기 (이 파일과 같은 폴더에 있는 app.py)
folder = os.path.dirname(os.path.abspath(__file__))  # check_empty.py가 있는 폴더
app_path = os.path.join(folder, "app.py")  # 그 폴더의 app.py 경로

try:
    with open(app_path, encoding="utf-8") as f:
        code = f.read()  # app.py 내용을 글자로 읽어 옴
except FileNotFoundError:
    print("app.py를 찾을 수 없어요. check_empty.py와 같은 폴더에 있는지 확인해 주세요.", file=sys.stderr)
    sys.exit(2)  # 2 = 문제 있음 → Claude에게 알림

# 3) 0건 안내가 있는지 검사
# 주의: 'menu_filtered.empty'나 주석 속 '0건' 글자에 속지 않도록 정확한 모양으로 찾음
checks = {
    "0건인지 검사하는 코드(if filtered.empty:)": "if filtered.empty:" in code,
    "0건 안내 문구('넓혀 보세요')": "넓혀 보세요" in code,
}
failed = [name for name, ok in checks.items() if not ok]  # 통과 못 한 항목만 모음

if failed:  # 하나라도 빠졌으면
    print("검사 실패: app.py에서 다음이 빠졌어요 → " + ", ".join(failed)
          + ". 조건에 맞는 데이터가 0건일 때 안내를 보여주는 코드를 다시 넣어 주세요.", file=sys.stderr)
    sys.exit(2)  # 2 = 문제 있음 → Claude Code가 이 메시지를 Claude에게 전달해 고치게 함

print("검사 통과: app.py에 0건 안내가 있어요.")  # 통과 메시지
sys.exit(0)  # 0 = 문제없음
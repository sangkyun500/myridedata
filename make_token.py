#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_token.py — 딱 한 번, 네 맥에서 실행하는 토큰 발급기.
가민 로그인 후 GitHub Secrets에 붙여넣을 토큰 문자열을 출력한다.

실행:
    pip install garminconnect
    python make_token.py
"""
import base64
from getpass import getpass

from garminconnect import Garmin

print("가민 커넥트 로그인 (이 정보는 가민 서버로만 전송됩니다)")
email = input("  이메일: ").strip()
password = getpass("  비밀번호: ")

g = Garmin(email=email, password=password, return_on_mfa=True)
r1, r2 = g.login()
if r1 == "needs_mfa":
    code = input("  MFA 인증 코드: ").strip()
    g.resume_login(r2, code)

token = base64.b64encode(g.garth.dumps().encode()).decode()

print("\n" + "=" * 60)
print("아래 한 덩어리 전체를 복사해서")
print("GitHub 저장소 → Settings → Secrets and variables → Actions")
print("→ New repository secret → Name: GARTH_TOKEN → Value에 붙여넣기")
print("=" * 60 + "\n")
print(token)
print("\n(이 토큰은 비밀번호 대신 쓰이는 열쇠입니다. 다른 곳에 올리지 마세요)")

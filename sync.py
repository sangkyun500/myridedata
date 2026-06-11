#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py — GitHub Actions에서 무인 실행되는 가민 수집기.
GARTH_TOKEN 환경변수(base64)로 로그인하고, 최근 2년 라이딩을
garmin_rides.csv 로 저장한다. 사람 입력 없음.
"""
import base64
import csv
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta

from garminconnect import Garmin

OUT_CSV = "garmin_rides.csv"
SUMMARY = "summary.txt"
YEARS = 2
PAGE = 100
RIDE_KEYS = ("cycling", "road_biking", "mountain_biking", "gravel_cycling",
             "virtual_ride", "indoor_cycling", "cyclocross", "track_cycling",
             "e_bike", "bmx", "recumbent_cycling")


def login():
    token_b64 = os.environ.get("GARTH_TOKEN")
    if not token_b64:
        sys.exit("GARTH_TOKEN 시크릿이 없습니다. README의 토큰 발급 단계를 확인하세요.")
    g = Garmin()
    g.garth.loads(base64.b64decode(token_b64).decode())
    # 토큰 유효성 확인 겸 프로필 조회
    g.display_name = g.garth.profile.get("displayName", "")
    return g


def fetch(g):
    cutoff = datetime.now() - timedelta(days=365 * YEARS)
    rides, start = [], 0
    while True:
        batch = g.get_activities(start, PAGE)
        if not batch:
            break
        stop = False
        for a in batch:
            t = ((a.get("activityType") or {}).get("typeKey") or "").lower()
            raw = a.get("startTimeLocal") or a.get("startTimeGMT") or ""
            try:
                dt = datetime.fromisoformat(str(raw).replace("T", " ").split(".")[0])
            except ValueError:
                continue
            if dt < cutoff:
                stop = True
                break
            if not any(k in t for k in RIDE_KEYS):
                continue
            dur = a.get("movingDuration") or a.get("duration") or 0
            if dur < 300:
                continue
            rides.append({
                "date": dt, "dur_sec": float(dur),
                "dist_km": round((a.get("distance") or 0) / 1000.0, 2),
                "avg_p": a.get("avgPower"),
                "np": a.get("normPower") or a.get("normalizedPower"),
                "max_p": a.get("maxPower"),
                "tss": a.get("trainingStressScore") or a.get("activityTrainingLoad"),
                "avg_hr": a.get("averageHR") or a.get("avgHr"),
                "name": a.get("activityName") or "",
            })
        if stop or len(batch) < PAGE:
            break
        start += PAGE
    rides.sort(key=lambda r: r["date"])
    return rides


def hms(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def analyze(rides):
    if not rides:
        return None
    now = datetime.now()
    age = lambda r: (now - r["date"]).days

    def best_np(lo, hi, win):
        c = [r["np"] for r in rides
             if r["np"] and lo <= r["dur_sec"] / 60 <= hi and age(r) <= win]
        return max(c) if c else None

    est, used_win = None, None
    for win in (90, 180, 365, 730):
        p20, p60, p90 = best_np(18, 32, win), best_np(40, 75, win), best_np(75, 120, win)
        cand = []
        if p60: cand.append(p60 * 1.00)
        if p20: cand.append(p20 * 0.95)
        if p90: cand.append(p90 * 1.02)
        if cand:
            est, used_win = round(max(cand)), win
            break
    if not est:
        return None

    def tss_of(r):
        if r["tss"]:
            return float(r["tss"])
        p = r["np"] or (r["avg_p"] * 1.05 if r["avg_p"] else None)
        if not p:
            return None
        if_ = p / est
        return (r["dur_sec"] / 3600) * if_ * if_ * 100

    day_tss = {}
    for r in rides:
        t = tss_of(r)
        if t:
            day_tss[r["date"].date()] = day_tss.get(r["date"].date(), 0) + t

    k_ctl, k_atl = 1 - math.exp(-1 / 42), 1 - math.exp(-1 / 7)
    ctl = atl = tsb = 0.0
    d = rides[0]["date"].date()
    while d <= now.date():
        load = day_tss.get(d, 0)
        tsb = ctl - atl
        ctl += (load - ctl) * k_ctl
        atl += (load - atl) * k_atl
        d += timedelta(days=1)
    return {"ftp": est, "win": used_win, "ctl": round(ctl, 1),
            "atl": round(atl, 1), "tsb": round(tsb, 1)}


def main():
    g = login()
    rides = fetch(g)
    if not rides:
        sys.exit("라이딩 활동이 없습니다.")

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["활동 유형", "날짜", "시간", "거리", "평균 파워",
                    "정규화 파워(NP)", "최대 파워",
                    "트레이닝 스트레스 점수(TSS)", "평균 심박수", "활동명"])
        for r in rides:
            w.writerow(["사이클링", r["date"].strftime("%Y-%m-%d %H:%M:%S"),
                        hms(r["dur_sec"]), r["dist_km"], r["avg_p"] or "",
                        r["np"] or "", r["max_p"] or "",
                        round(r["tss"], 1) if r["tss"] else "",
                        r["avg_hr"] or "", r["name"]])

    res = analyze(rides)
    with open(SUMMARY, "w", encoding="utf-8") as f:
        f.write(f"updated: {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"rides_2y: {len(rides)}\n")
        if res:
            f.write(f"est_ftp_w: {res['ftp']} (window {res['win']}d)\n")
            f.write(f"ctl: {res['ctl']}\natl: {res['atl']}\ntsb: {res['tsb']:+}\n")
    print(f"OK — {len(rides)} rides → {OUT_CSV}")


if __name__ == "__main__":
    main()

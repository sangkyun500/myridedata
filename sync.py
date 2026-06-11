#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64, csv, math, os, sys
from datetime import datetime, timedelta
import garth

OUT_CSV, SUMMARY, YEARS, PAGE = "garmin_rides.csv", "summary.txt", 2, 100
RIDE_KEYS = ("cycling", "biking", "ride", "cyclocross", "bmx")

def login():
    tok = os.environ.get("GARTH_TOKEN")
    if not tok:
        sys.exit("GARTH_TOKEN 시크릿이 없습니다.")
    garth.client.loads(base64.b64decode(tok).decode())

def fetch():
    cutoff = datetime.now() - timedelta(days=365 * YEARS)
    rides, start = [], 0
    while True:
        batch = garth.connectapi(
            "/activitylist-service/activities/search/activities",
            params={"start": start, "limit": PAGE})
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
            rides.append({"date": dt, "dur_sec": float(dur),
                "dist_km": round((a.get("distance") or 0) / 1000.0, 2),
                "avg_p": a.get("avgPower"),
                "np": a.get("normPower") or a.get("normalizedPower"),
                "max_p": a.get("maxPower"),
                "tss": a.get("trainingStressScore") or a.get("activityTrainingLoad"),
                "avg_hr": a.get("averageHR") or a.get("avgHr"),
                "name": a.get("activityName") or ""})
        if stop or len(batch) < PAGE:
            break
        start += PAGE
    rides.sort(key=lambda r: r["date"])
    return rides

def hms(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"

def analyze(rides):
    if not rides:
        return None
    now = datetime.now()
    age = lambda r: (now - r["date"]).days
    def best_np(lo, hi, win):
        c = [r["np"] for r in rides
             if r["np"] and lo <= r["dur_sec"] / 60 <= hi and age(r) <= win]
        return max(c) if c else None
    est, used = None, None
    for win in (90, 180, 365, 730):
        p20, p60, p90 = best_np(18, 32, win), best_np(40, 75, win), best_np(75, 120, win)
        cand = []
        if p60: cand.append(p60)
        if p20: cand.append(p20 * 0.95)
        if p90: cand.append(p90 * 1.02)
        if cand:
            est, used = round(max(cand)), win
            break
    if not est:
        return None
    def tss_of(r):
        if r["tss"]:
            return float(r["tss"])
        p = r["np"] or (r["avg_p"] * 1.05 if r["avg_p"] else None)
        if not p:
            return None
        i = p / est
        return (r["dur_sec"] / 3600) * i * i * 100
    day = {}
    for r in rides:
        t = tss_of(r)
        if t:
            day[r["date"].date()] = day.get(r["date"].date(), 0) + t
    kc, ka = 1 - math.exp(-1 / 42), 1 - math.exp(-1 / 7)
    ctl = atl = tsb = 0.0
    d = rides[0]["date"].date()
    while d <= now.date():
        load = day.get(d, 0)
        tsb = ctl - atl
        ctl += (load - ctl) * kc
        atl += (load - atl) * ka
        d += timedelta(days=1)
    return {"ftp": est, "win": used, "ctl": round(ctl, 1),
            "atl": round(atl, 1), "tsb": round(tsb, 1)}

def main():
    login()
    rides = fetch()
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
    print(f"OK — {len(rides)} rides")

if __name__ == "__main__":
    main()

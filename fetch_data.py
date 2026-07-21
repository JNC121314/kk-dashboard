#!/usr/bin/env python3
"""
批量提取多个月份看板数据
支持提取过去N个月的数据，按月保存
"""
import json
import urllib.request
import urllib.parse
import http.cookiejar
import time
import os
import calendar
from datetime import datetime

BASE = "https://kapi.likeduoduiyi.cn"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 从环境变量读取账号信息（JSON格式），必须通过 Secrets 注入
_accounts_json = os.environ.get("ACCOUNTS_JSON")
if _accounts_json:
    ACCOUNTS = json.loads(_accounts_json)
else:
    print("错误：未设置 ACCOUNTS_JSON 环境变量")
    print("请在 GitHub Secrets 中配置 ACCOUNTS_JSON")
    exit(1)


def get_month_range(year, month):
    """获取某月的起止时间"""
    first_day = f"{year}-{month:02d}-01 00:00:00"
    last_day_num = calendar.monthrange(year, month)[1]
    last_day = f"{year}-{month:02d}-{last_day_num:02d} 23:59:59"
    return first_day, last_day


def login(opener, username, password):
    login_data = json.dumps({"username": username, "password": password}).encode("utf-8")
    login_req = urllib.request.Request(
        f"{BASE}/endpoint/supplier/login",
        data=login_data,
        headers={"Content-Type": "application/json;charset=UTF-8"},
        method="POST"
    )
    resp = opener.open(login_req, timeout=30)
    body = resp.read().decode("utf-8")
    result = json.loads(body)
    if result.get("status") == 200:
        return result.get("data", {}).get("supplierName", "")
    return None


def fetch_month_data(opener, supplier_name, start_time, end_time):
    all_records = []
    page_current = 1
    page_size = 2000

    while True:
        params = {
            "belongChannel": "",
            "supplierName": supplier_name,
            "categorys": "",
            "supplierNames": "",
            "startTime": start_time,
            "endTime": end_time,
            "pageCurrent": str(page_current),
            "pageSize": str(page_size),
        }
        url = f"{BASE}/endpoint/supplier/detail?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, method="GET")
        resp = opener.open(req, timeout=60)
        body = resp.read().decode("utf-8")
        result = json.loads(body)
        data = result.get("data", {})
        records = data.get("records", [])
        total_pages = data.get("pages", 0)

        real_records = [r for r in records if r.get("date") != "总计"]
        all_records.extend(real_records)

        if page_current >= total_pages:
            break
        page_current += 1
        time.sleep(0.3)

    return all_records


def main():
    today = datetime.now()
    # 计算过去3个月（含当月）
    months = []
    for i in range(2, -1, -1):  # 2个月前, 1个月前, 当月
        d = datetime(today.year, today.month, 1)
        # 回退i个月
        for _ in range(i):
            if d.month == 1:
                d = datetime(d.year - 1, 12, 1)
            else:
                d = datetime(d.year, d.month - 1, 1)
        months.append((d.year, d.month))

    print(f"=== 批量提取多月数据 ===")
    print(f"目标月份: {', '.join(f'{y}-{m:02d}' for y, m in months)}")
    print(f"账号数量: {len(ACCOUNTS)}\n")

    for year, month in months:
        month_key = f"{year}-{month:02d}"
        start_time, end_time = get_month_range(year, month)

        # 检查是否已有数据文件
        output_path = os.path.join(OUTPUT_DIR, f"全部看板{month_key}数据_汇总.json")
        if os.path.exists(output_path):
            print(f"\n[{month_key}] 数据文件已存在，跳过")
            continue

        print(f"\n{'='*60}")
        print(f"[{month_key}] 日期范围: {start_time} ~ {end_time}")
        print(f"{'='*60}")

        all_account_data = []
        failed_accounts = []

        for i, acc in enumerate(ACCOUNTS, 1):
            label = acc["label"]
            username = acc["username"]
            password = acc["password"]
            print(f"\n  [{i}/{len(ACCOUNTS)}] {label} (账号:{username})")

            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

            try:
                supplier_name = login(opener, username, password)
                if not supplier_name:
                    print(f"    ✗ 登录失败")
                    failed_accounts.append({**acc, "reason": "登录失败"})
                    continue
                print(f"    ✓ 登录成功: {supplier_name}")
            except Exception as e:
                print(f"    ✗ 登录异常: {e}")
                failed_accounts.append({**acc, "reason": f"登录异常: {e}"})
                continue

            try:
                records = fetch_month_data(opener, supplier_name, start_time, end_time)
                print(f"    ✓ 获取 {len(records)} 条记录")

                acc_data = {
                    "label": label,
                    "username": username,
                    "supplier_name": supplier_name,
                    "record_count": len(records),
                    "records": records,
                }
                all_account_data.append(acc_data)
            except Exception as e:
                print(f"    ✗ 数据获取异常: {e}")
                failed_accounts.append({**acc, "reason": f"数据获取异常: {e}"})

            time.sleep(0.5)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "query_time": datetime.now().isoformat(),
                "month": month_key,
                "date_range": f"{start_time} ~ {end_time}",
                "total_accounts": len(ACCOUNTS),
                "success_accounts": len(all_account_data),
                "failed_accounts": failed_accounts,
                "accounts": all_account_data,
            }, f, ensure_ascii=False, indent=2)

        print(f"\n  [{month_key}] 完成: {len(all_account_data)}/{len(ACCOUNTS)} 个账号成功")
        print(f"  数据已保存: {output_path}")

    print(f"\n{'='*60}")
    print("全部月份提取完成!")


if __name__ == "__main__":
    main()

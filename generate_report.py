#!/usr/bin/env python3
"""
v6 今日昨日总览版报告：
1. 页面顶部新增"今日 vs 昨日"投放量级总览卡片
   - 华彩课包按leads排序，其他看板按加微排序
   - 一打开就能看到当日/前一日数据总量
2. 保留v5全部功能：多月筛选、深色模式、预警、R值、排序
3. 适配深色模式
"""
import json
import os
import glob
from collections import defaultdict
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUTPUT_DIR = SCRIPT_DIR

CONVERSION_DAYS = 10
TODAY = datetime.now()
CUTOFF_DATE = (TODAY - timedelta(days=CONVERSION_DAYS)).strftime("%Y-%m-%d")

ALERT_CONV_RATE = 70
ALERT_MATURE_LEADS = 50
R_VALUE_TARGET = 45
R_VALUE_MIN_MATURE = 50

HUACAI_LABEL = "华彩课包面板"
PIANO_LABEL = "通用钢琴面板"


# ========== Data Loading ==========

def get_available_months():
    """Scan for available month data files, return sorted list (newest first)"""
    months = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith("全部看板") and fname.endswith("数据_汇总.json"):
            key = fname.replace("全部看板", "").replace("数据_汇总.json", "")
            if len(key) == 7 and key[4] == "-":
                try:
                    y, m = int(key[:4]), int(key[5:])
                    months.append(key)
                except ValueError:
                    pass
    return sorted(months, reverse=True)


def load_month_data(month_key):
    path = os.path.join(DATA_DIR, f"全部看板{month_key}数据_汇总.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ========== Compute Functions (same as v4) ==========

def compute_cross_tabs(records):
    date_sku = defaultdict(lambda: defaultdict(lambda: {"leads": 0, "addwx": 0, "uv": 0, "pv": 0, "order": 0, "refund": 0}))
    sku_date = defaultdict(lambda: defaultdict(lambda: {"leads": 0, "addwx": 0, "uv": 0, "pv": 0, "order": 0, "refund": 0}))
    sku_meta = defaultdict(lambda: {"category": "", "platform": "", "goods": ""})
    for r in records:
        dt = r.get("date", "")
        label = r.get("dataLabel", "") or "未分类"
        if dt == "总计":
            continue
        for target in [date_sku[dt][label], sku_date[label][dt]]:
            target["leads"] += r.get("leadsCount", 0)
            target["addwx"] += r.get("addWx", 0)
            target["uv"] += r.get("pageUv", 0)
            target["pv"] += r.get("PagePv", 0)
            target["order"] += r.get("orderPrice", 0)
            target["refund"] += r.get("refundPrice", 0)
        if not sku_meta[label]["category"] and r.get("category"):
            sku_meta[label]["category"] = r["category"]
        if not sku_meta[label]["platform"] and r.get("platformType"):
            sku_meta[label]["platform"] = r["platformType"]
        if not sku_meta[label]["goods"] and r.get("goodsName"):
            sku_meta[label]["goods"] = r["goodsName"]
    return date_sku, sku_date, sku_meta


def compute_sku_conversion(sku_date, sku_meta):
    results = []
    for sku, dates in sku_date.items():
        total_leads = sum(d["leads"] for d in dates.values())
        if total_leads == 0:
            continue
        mature_leads = sum(d["leads"] for dt, d in dates.items() if dt <= CUTOFF_DATE)
        converting_leads = total_leads - mature_leads
        total_addwx = sum(d["addwx"] for d in dates.values())
        total_uv = sum(d["uv"] for d in dates.values())
        total_order = sum(d["order"] for d in dates.values())
        total_refund = sum(d["refund"] for d in dates.values())
        mature_addwx = sum(d["addwx"] for dt, d in dates.items() if dt <= CUTOFF_DATE)
        converting_addwx = total_addwx - mature_addwx
        mature_order = sum(d["order"] for dt, d in dates.items() if dt <= CUTOFF_DATE)
        converting_order = total_order - mature_order
        active_dates = sum(1 for d in dates.values() if d["leads"] > 0)
        if converting_leads == 0:
            status, status_class = "已转化完毕", "mature"
        elif mature_leads == 0:
            status, status_class = "转化中", "converting"
        else:
            status, status_class = "部分转化中", "partial"
        conv_rate = round(total_addwx / total_leads * 100, 1) if total_leads > 0 else 0
        r_by_leads = round(total_order / total_leads, 2) if total_leads > 0 else 0
        r_by_addwx = round(total_order / total_addwx, 2) if total_addwx > 0 else 0
        mature_r_by_leads = round(mature_order / mature_leads, 2) if mature_leads > 0 else 0
        mature_r_by_addwx = round(mature_order / mature_addwx, 2) if mature_addwx > 0 else 0
        converting_r_by_leads = round(converting_order / converting_leads, 2) if converting_leads > 0 else 0
        converting_r_by_addwx = round(converting_order / converting_addwx, 2) if converting_addwx > 0 else 0
        results.append({
            "label": sku, "category": sku_meta[sku]["category"], "platform": sku_meta[sku]["platform"],
            "goods": sku_meta[sku]["goods"], "total_leads": total_leads, "mature_leads": mature_leads,
            "converting_leads": converting_leads, "total_addwx": total_addwx, "total_uv": total_uv,
            "total_order": round(total_order, 2), "total_refund": round(total_refund, 2),
            "mature_addwx": mature_addwx, "converting_addwx": converting_addwx,
            "mature_order": round(mature_order, 2), "converting_order": round(converting_order, 2),
            "active_dates": active_dates, "conv_rate": conv_rate, "status": status, "status_class": status_class,
            "r_by_leads": r_by_leads, "r_by_addwx": r_by_addwx,
            "mature_r_by_leads": mature_r_by_leads, "mature_r_by_addwx": mature_r_by_addwx,
            "converting_r_by_leads": converting_r_by_leads, "converting_r_by_addwx": converting_r_by_addwx,
        })
    results.sort(key=lambda x: x["total_leads"], reverse=True)
    return results


def compute_alerts(conversion, check_conv_rate=False, check_r_value=False, is_huacai=False):
    alerts = []
    for s in conversion:
        cat = s.get("category", "") or "未分类"
        if check_conv_rate and s["total_leads"] > 0:
            if s["conv_rate"] < ALERT_CONV_RATE:
                alerts.append({
                    "type": "加微率偏低", "severity": "warning",
                    "sku": s["label"], "total_leads": s["total_leads"], "category": cat,
                    "detail": f"加微率 {s['conv_rate']}%（加微{s['total_addwx']}/leads{s['total_leads']}）",
                })
        if s["mature_leads"] > ALERT_MATURE_LEADS and s["total_order"] == 0:
            alerts.append({
                "type": "已转化无成交", "severity": "danger",
                "sku": s["label"], "total_leads": s["total_leads"], "category": cat,
                "detail": f"已转化 {s['mature_leads']} 个 leads 但成交金额为 0",
            })
        if check_r_value:
            if is_huacai:
                r_val = s["r_by_leads"]
                denom = s["total_leads"]
                mature_vol = s["mature_leads"]
                denom_label = "leads"
            else:
                r_val = s["r_by_addwx"]
                denom = s["total_addwx"]
                mature_vol = s["mature_addwx"]
                denom_label = "加微"
            if mature_vol >= R_VALUE_MIN_MATURE and r_val < R_VALUE_TARGET and denom > 0:
                alerts.append({
                    "type": "R值偏低", "severity": "warning",
                    "sku": s["label"], "total_leads": s["total_leads"], "category": cat,
                    "detail": f"R值 ¥{r_val}（目标¥{R_VALUE_TARGET}），GMV ¥{s['total_order']:,.0f} ÷ {denom:,} {denom_label}，已转化{mature_vol:,}",
                })
    return alerts


def prepare_r_details(conversion, is_huacai):
    denom_label = "leads" if is_huacai else "加微"
    mature_list = []
    converting_list = []
    for s in conversion:
        if is_huacai:
            m_denom = s["mature_leads"]
            m_r = s["mature_r_by_leads"]
            c_denom = s["converting_leads"]
            c_r = s["converting_r_by_leads"]
        else:
            m_denom = s["mature_addwx"]
            m_r = s["mature_r_by_addwx"]
            c_denom = s["converting_addwx"]
            c_r = s["converting_r_by_addwx"]
        if m_denom > 0:
            mature_list.append({
                "label": s["label"], "r": m_r, "gmv": s["mature_order"],
                "denom": m_denom, "denom_label": denom_label, "mature_vol": m_denom,
            })
        if c_denom > 0:
            converting_list.append({
                "label": s["label"], "r": c_r, "gmv": s["converting_order"],
                "denom": c_denom, "denom_label": denom_label,
            })
    mature_list.sort(key=lambda x: x["r"])
    converting_list.sort(key=lambda x: x["r"])
    return {"mature": mature_list, "converting": converting_list}


def compute_totals(records):
    return {
        "leads": sum(r.get("leadsCount", 0) for r in records),
        "addwx": sum(r.get("addWx", 0) for r in records),
        "uv": sum(r.get("pageUv", 0) for r in records),
        "pv": sum(r.get("PagePv", 0) for r in records),
        "order": round(sum(r.get("orderPrice", 0) for r in records), 2),
        "refund": round(sum(r.get("refundPrice", 0) for r in records), 2),
    }


def compute_daily(records):
    daily = defaultdict(lambda: {"leads": 0, "addwx": 0, "uv": 0, "pv": 0, "order": 0, "refund": 0})
    for r in records:
        dt = r.get("date", "")
        if dt and dt != "总计":
            daily[dt]["leads"] += r.get("leadsCount", 0)
            daily[dt]["addwx"] += r.get("addWx", 0)
            daily[dt]["uv"] += r.get("pageUv", 0)
            daily[dt]["pv"] += r.get("PagePv", 0)
            daily[dt]["order"] += r.get("orderPrice", 0)
            daily[dt]["refund"] += r.get("refundPrice", 0)
    result = [{"date": k, **v} for k, v in sorted(daily.items())]
    for d in result:
        d["order"] = round(d["order"], 2)
    return result


def compute_category_summary(records, is_huacai):
    """Compute per-category totals, daily, conversion summary, and R-values."""
    cats = sorted(set(r.get("category", "") or "未分类" for r in records))
    result = {}
    for cat in cats:
        cat_records = [r for r in records if (r.get("category", "") or "未分类") == cat]
        if not cat_records:
            continue
        totals = compute_totals(cat_records)
        daily = compute_daily(cat_records)
        cross = compute_cross_tabs(cat_records)
        conv = compute_sku_conversion(cross[1], cross[2])

        total_mature = sum(s["mature_leads"] for s in conv)
        total_converting = sum(s["converting_leads"] for s in conv)
        total_gmv = sum(s["total_order"] for s in conv)
        total_mature_addwx = sum(s["mature_addwx"] for s in conv)
        total_converting_addwx = sum(s["converting_addwx"] for s in conv)
        total_mature_order = sum(s["mature_order"] for s in conv)
        total_converting_order = sum(s["converting_order"] for s in conv)

        if is_huacai:
            r_denom = total_mature + total_converting
            r_mature = round(total_mature_order / total_mature, 2) if total_mature > 0 else 0
            r_converting = round(total_converting_order / total_converting, 2) if total_converting > 0 else 0
            r_total = round(total_gmv / r_denom, 2) if r_denom > 0 else 0
            r_mature_denom = total_mature
            r_converting_denom = total_converting
        else:
            r_denom = total_mature_addwx + total_converting_addwx
            r_mature = round(total_mature_order / total_mature_addwx, 2) if total_mature_addwx > 0 else 0
            r_converting = round(total_converting_order / total_converting_addwx, 2) if total_converting_addwx > 0 else 0
            r_total = round(total_gmv / r_denom, 2) if r_denom > 0 else 0
            r_mature_denom = total_mature_addwx
            r_converting_denom = total_converting_addwx

        result[cat] = {
            "totals": totals,
            "daily": daily,
            "conv": {
                "mature_leads": total_mature,
                "converting_leads": total_converting,
                "gmv": round(total_gmv, 2),
                "mature_addwx": total_mature_addwx,
                "converting_addwx": total_converting_addwx,
                "mature_order": round(total_mature_order, 2),
                "converting_order": round(total_converting_order, 2),
                "sku_count": len(conv),
            },
            "r": {
                "mature": r_mature,
                "converting": r_converting,
                "total": r_total,
                "mature_denom": r_mature_denom,
                "converting_denom": r_converting_denom,
                "total_denom": r_denom,
                "gmv": round(total_gmv, 2),
            },
        }
    return result


def prepare_js_data(panel_label, records):
    date_sku, sku_date, sku_meta = compute_cross_tabs(records)
    ds_js = {}
    for dt, skus in sorted(date_sku.items()):
        arr = [{"label": s, **m, "order": round(m["order"], 2)} for s, m in skus.items() if m["leads"] > 0 or m["order"] > 0 or m["addwx"] > 0]
        arr.sort(key=lambda x: x["leads"], reverse=True)
        ds_js[dt] = arr
    sd_js = {}
    for sku, dates in sku_date.items():
        arr = [{"date": dt, **m, "order": round(m["order"], 2)} for dt, m in sorted(dates.items()) if m["leads"] > 0 or m["order"] > 0]
        if arr:
            sd_js[sku] = arr
    return ds_js, sd_js, dict(sku_meta)


YESTERDAY = TODAY - timedelta(days=1)
YESTERDAY_STR = YESTERDAY.strftime("%Y-%m-%d")
TODAY_STR = TODAY.strftime("%Y-%m-%d")


def compute_account_daily_totals(accounts, reference_date_str=None):
    """Compute per-account daily totals for reference date and previous day."""
    if reference_date_str is None:
        reference_date_str = TODAY_STR
    ref = datetime.strptime(reference_date_str, "%Y-%m-%d")
    prev_str = (ref - timedelta(days=1)).strftime("%Y-%m-%d")
    cur_str = reference_date_str

    result = {}
    for acc in accounts:
        label = acc["label"]
        prev_stats = {"leads": 0, "addwx": 0, "uv": 0, "order": 0}
        cur_stats = {"leads": 0, "addwx": 0, "uv": 0, "order": 0}
        for r in acc["records"]:
            dt = r.get("date", "")
            if dt == prev_str:
                prev_stats["leads"] += r.get("leadsCount", 0)
                prev_stats["addwx"] += r.get("addWx", 0)
                prev_stats["uv"] += r.get("pageUv", 0)
                prev_stats["order"] += r.get("orderPrice", 0)
            elif dt == cur_str:
                cur_stats["leads"] += r.get("leadsCount", 0)
                cur_stats["addwx"] += r.get("addWx", 0)
                cur_stats["uv"] += r.get("pageUv", 0)
                cur_stats["order"] += r.get("orderPrice", 0)
        result[label] = {"prev": prev_stats, "cur": cur_stats,
                         "prev_str": prev_str, "cur_str": cur_str}
    return result

def generate_overview_html(accounts, account_daily):
    """Generate a compact 'Last 2 days' overview — two rows only:
    1. 华彩课包 leads (昨日→今日)
    2. 其他看板 加微 (昨日→今日, per-dashboard)
    """

    # Separate huacai vs others
    huacai_stats = account_daily.get(HUACAI_LABEL, {"prev": {}, "cur": {}})
    other_accounts = [(label, stats) for label, stats in account_daily.items()
                      if label != HUACAI_LABEL]
    other_accounts.sort(key=lambda x: max(x[1]["prev"]["addwx"], x[1]["cur"]["addwx"]), reverse=True)

    # Day labels
    dow_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    cur_str = huacai_stats.get("cur_str", TODAY_STR)
    prev_str = huacai_stats.get("prev_str", (TODAY - timedelta(days=1)).strftime("%Y-%m-%d"))

    def day_label(d_str):
        d = datetime.strptime(d_str, "%Y-%m-%d")
        return d_str[5:] + "(" + dow_names[d.weekday()] + ")"

    prev_display = day_label(prev_str)
    cur_display = day_label(cur_str)

    def delta_html(current_val, previous_val):
        if previous_val == 0 and current_val == 0:
            return ""
        if previous_val == 0:
            return '<span class="ov-delta ov-new">NEW</span>'
        pct = round((current_val - previous_val) / previous_val * 100)
        if pct > 0:
            return f'<span class="ov-delta ov-up">+{pct}%</span>'
        elif pct < 0:
            return f'<span class="ov-delta ov-down">{pct}%</span>'
        else:
            return '<span class="ov-delta ov-flat">0%</span>'

    # Huacai leads row
    hc_prev_leads = huacai_stats["prev"]["leads"]
    hc_cur_leads = huacai_stats["cur"]["leads"]
    hc_prev_addwx = huacai_stats["prev"]["addwx"]
    hc_cur_addwx = huacai_stats["cur"]["addwx"]
    hc_delta = delta_html(hc_cur_leads, hc_prev_leads)

    # Other accounts rows
    other_rows_html = ""
    for label, stats in other_accounts:
        prev_val = stats["prev"]["addwx"]
        cur_val = stats["cur"]["addwx"]
        delta = delta_html(cur_val, prev_val)
        row_class = "ov-row-active" if (prev_val > 0 or cur_val > 0) else "ov-row-zero"
        other_rows_html += f'''
        <div class="ov-table-row {row_class}">
          <span class="ov-cell-label">{label}</span>
          <span class="ov-cell-day">{prev_val:,}</span>
          <span class="ov-cell-delta">{delta}</span>
          <span class="ov-cell-day">{cur_val:,}</span>
        </div>'''

    # Other totals
    other_prev_total = sum(s["prev"]["addwx"] for _, s in other_accounts)
    other_cur_total = sum(s["cur"]["addwx"] for _, s in other_accounts)
    other_delta = delta_html(other_cur_total, other_prev_total)

    html = f'''
<div class="ov-section" id="overviewSection">
  <div class="ov-header">
    <span class="ov-title">📊 投放量级速览</span>
    <span class="ov-date-info">{prev_display} → {cur_display}</span>
  </div>

  <div class="ov-block">
    <div class="ov-block-title">🎬 华彩课包 · leads</div>
    <div class="ov-table-row ov-row-huacai">
      <span class="ov-cell-label">华彩课包面板</span>
      <span class="ov-cell-day">{hc_prev_leads:,}</span>
      <span class="ov-cell-delta">{hc_delta}</span>
      <span class="ov-cell-day">{hc_cur_leads:,}</span>
    </div>
    <div class="ov-block-sub">加微 {hc_prev_addwx:,}→{hc_cur_addwx:,}</div>
  </div>

  <div class="ov-block">
    <div class="ov-block-title">🎹 其他看板 · 加微</div>
    <div class="ov-table-header">
      <span class="ov-cell-label">看板</span>
      <span class="ov-cell-day">{prev_display}</span>
      <span class="ov-cell-delta">变化</span>
      <span class="ov-cell-day">{cur_display}</span>
    </div>
    {other_rows_html}
    <div class="ov-table-row ov-row-total">
      <span class="ov-cell-label">合计</span>
      <span class="ov-cell-day">{other_prev_total:,}</span>
      <span class="ov-cell-delta">{other_delta}</span>
      <span class="ov-cell-day">{other_cur_total:,}</span>
    </div>
  </div>
</div>'''

    return html

def generate_alert_html(alerts, panel_name, section_id):
    if not alerts:
        return '<div class="alert-box ok" data-alert-container><span class="alert-icon">✅</span><span>暂无预警，所有达人数据正常</span></div>'
    danger_count = sum(1 for a in alerts if a["severity"] == "danger")
    warning_count = sum(1 for a in alerts if a["severity"] == "warning")
    html = f'<div class="alert-box" data-alert-container>'
    html += f'<div class="alert-header"><span class="alert-icon">⚠️</span><span class="alert-title">{panel_name} · 预警提示</span>'
    html += f'<span class="alert-counts">'
    if danger_count:
        html += f'<span class="alert-tag danger" data-alert-count="danger">{danger_count} 项严重</span>'
    if warning_count:
        html += f'<span class="alert-tag warning" data-alert-count="warning">{warning_count} 项警告</span>'
    html += f'<span class="alert-tag" data-alert-count="total" style="background:#e8eaf6;color:#3f51b5">共 {len(alerts)} 项</span>'
    html += f'</span></div>'
    html += '<div class="alert-list">'
    for a in alerts:
        icon = "🔴" if a["severity"] == "danger" else "🟡"
        cat = a.get("category", "")
        html += f'<div class="alert-item {a["severity"]}" data-cat="{cat}">'
        html += f'<span class="alert-item-icon">{icon}</span>'
        html += f'<span class="alert-item-type">{a["type"]}</span>'
        html += f'<span class="alert-item-sku" onclick="showSkuDetail(\'{a["sku"]}\',\'{section_id}\')">{a["sku"]}</span>'
        html += f'<span class="alert-item-detail">{a["detail"]}</span>'
        html += f'</div>'
    html += '</div></div>'
    return html


# ========== Panel Section Generation ==========

def generate_panel_section(month_key, acc, conversion, alerts, daily, totals, is_huacai=False):
    panel_key = acc["label"]
    color = "#764ba2" if is_huacai else "#2980b9"
    check_conv = is_huacai
    section_id = "hc" if is_huacai else "piano"

    total_mature = sum(s["mature_leads"] for s in conversion)
    total_converting = sum(s["converting_leads"] for s in conversion)
    total_gmv = sum(s["total_order"] for s in conversion)
    total_mature_addwx = sum(s["mature_addwx"] for s in conversion)
    total_converting_addwx = sum(s["converting_addwx"] for s in conversion)
    total_mature_order = sum(s["mature_order"] for s in conversion)
    total_converting_order = sum(s["converting_order"] for s in conversion)
    if is_huacai:
        r_total_denom_val = total_mature + total_converting
        r_mature = round(total_mature_order / total_mature, 2) if total_mature > 0 else 0
        r_converting = round(total_converting_order / total_converting, 2) if total_converting > 0 else 0
        r_total = round(total_gmv / r_total_denom_val, 2) if r_total_denom_val > 0 else 0
        r_formula = "R值 = GMV ÷ leads"
    else:
        r_total_denom_val = total_mature_addwx + total_converting_addwx
        r_mature = round(total_mature_order / total_mature_addwx, 2) if total_mature_addwx > 0 else 0
        r_converting = round(total_converting_order / total_converting_addwx, 2) if total_converting_addwx > 0 else 0
        r_total = round(total_gmv / r_total_denom_val, 2) if r_total_denom_val > 0 else 0
        r_formula = "R值 = GMV ÷ 加微数"
    r_denom_label = "leads" if is_huacai else "加微"
    r_mature_denom = total_mature if is_huacai else total_mature_addwx
    r_converting_denom = total_converting if is_huacai else total_converting_addwx
    r_total_denom = r_total_denom_val
    emoji = "🎬" if is_huacai else "🎹"
    panel_title = "华彩课包" if is_huacai else "通用钢琴"

    html = f'''
<div class="section filterable" data-section="{section_id}" style="border:3px solid {color};">
  <div class="section-title" style="border-bottom-color:{color};color:{color};">
    <span>{emoji} {panel_title}面板 · 数据专区</span>
    <span class="hint" data-cat-kpi="header-totals">leads {totals['leads']:,} ｜ 加微 {totals['addwx']:,} ｜ 成交 ¥{totals['order']:,.0f}</span>
  </div>

  <div class="hc-hero">
    <div class="hc-hero-item"><div class="l">总 leads</div><div class="v" data-cat-kpi="kpi-leads">{totals['leads']:,}</div></div>
    <div class="hc-hero-item green"><div class="l">总加微</div><div class="v" data-cat-kpi="kpi-addwx">{totals['addwx']:,}</div></div>
    <div class="hc-hero-item gold"><div class="l">总成交金额</div><div class="v" data-cat-kpi="kpi-order">¥{totals['order']:,.0f}</div></div>
  </div>

  {generate_alert_html(alerts, panel_key, section_id)}

  <div class="conv-summary" style="margin:14px 0">
    <div class="conv-card mature">已转化 leads<br><span class="num" data-cat-kpi="conv-mature">{total_mature:,}</span></div>
    <div class="conv-card converting">转化中 leads<br><span class="num" data-cat-kpi="conv-converting">{total_converting:,}</span></div>
    <div class="conv-card gmv">总 GMV<br><span class="num" data-cat-kpi="conv-gmv">¥{total_gmv:,.0f}</span></div>
    <div class="conv-card" style="background:#e8eaf6;color:#3f51b5">有 leads 达人数<br><span class="num" data-cat-kpi="conv-sku-count">{len(conversion)}</span></div>
  </div>
  <div style="margin:14px 0;padding:14px;background:linear-gradient(135deg,#f5f7fa,#e8edf5);border-radius:10px;border:2px solid {color}">
    <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:10px">📊 R值分析 <span style="font-size:11px;font-weight:normal;color:#888">（{r_formula}）</span></div>
    <div style="display:flex;gap:12px;flex-wrap:wrap">
      <div class="r-card" style="background:#fff;border-radius:8px;padding:12px 20px;text-align:center;flex:1;min-width:140px;box-shadow:0 2px 6px rgba(0,0,0,0.06);cursor:pointer;transition:box-shadow 0.2s" onmouseenter="showRDetail('mature','{section_id}',event)" onmouseleave="hideRDetail()" onmouseover="this.style.boxShadow='0 4px 14px rgba(0,0,0,0.18)'" onmouseout="this.style.boxShadow='0 2px 6px rgba(0,0,0,0.06)'">
        <div style="font-size:12px;color:#888">已转化R值 <span style="font-size:9px;opacity:0.5">👆悬停查看</span></div>
        <div style="font-size:22px;font-weight:700;color:#155724" data-cat-kpi="r-mature-val">¥{r_mature}</div>
        <div style="font-size:10px;color:#aaa" data-cat-kpi="r-mature-formula">¥{total_mature_order:,.0f} ÷ {r_mature_denom:,} {r_denom_label}</div>
      </div>
      <div class="r-card" style="background:#fff;border-radius:8px;padding:12px 20px;text-align:center;flex:1;min-width:140px;box-shadow:0 2px 6px rgba(0,0,0,0.06);cursor:pointer;transition:box-shadow 0.2s" onmouseenter="showRDetail('converting','{section_id}',event)" onmouseleave="hideRDetail()" onmouseover="this.style.boxShadow='0 4px 14px rgba(0,0,0,0.18)'" onmouseout="this.style.boxShadow='0 2px 6px rgba(0,0,0,0.06)'">
        <div style="font-size:12px;color:#888">转化中R值 <span style="font-size:9px;opacity:0.5">👆悬停查看</span></div>
        <div style="font-size:22px;font-weight:700;color:#856404" data-cat-kpi="r-converting-val">¥{r_converting}</div>
        <div style="font-size:10px;color:#aaa" data-cat-kpi="r-converting-formula">¥{total_converting_order:,.0f} ÷ {r_converting_denom:,} {r_denom_label}</div>
      </div>
      <div class="r-card" style="background:#fff;border-radius:8px;padding:12px 20px;text-align:center;flex:1;min-width:140px;box-shadow:0 2px 6px rgba(0,0,0,0.06);border:2px solid {color}">
        <div style="font-size:12px;color:#888">总R值（含转化中）</div>
        <div style="font-size:22px;font-weight:700;color:{color}" data-cat-kpi="r-total-val">¥{r_total}</div>
        <div style="font-size:10px;color:#aaa" data-cat-kpi="r-total-formula">¥{total_gmv:,.0f} ÷ {r_total_denom:,} {r_denom_label}</div>
      </div>
    </div>
  </div>
  <div class="note" style="margin-bottom:10px">
    📌 转化周期{CONVERSION_DAYS}天，截止日{CUTOFF_DATE[5:]}。{CUTOFF_DATE[5:]}及之前的 leads 已进入成熟期（已转化），之后为转化中。已过滤 leads=0 的标签。
    {"加微率低于" + str(ALERT_CONV_RATE) + "%的达人标记为加微率异常。" if check_conv else ""}
    已转化超过{ALERT_MATURE_LEADS}个 leads 但无成交金额的达人标记为转化异常。
    R值低于¥{R_VALUE_TARGET}且已转化数据量≥{R_VALUE_MIN_MATURE}的达人标记为R值偏低。💡 悬停R值卡片可查看各达人R值明细。
  </div>

  <div class="chart-container" style="height:300px">
    <canvas id="{section_id}DailyChart-{month_key}"></canvas>
  </div>
  <p style="text-align:center;font-size:11px;color:#888;margin-top:-8px;margin-bottom:12px;">👆 点击图表数据点查看当天达人来源</p>

  <h4 style="margin-bottom:6px;color:{color};">📅 分日数据明细 <span style="font-size:10px;font-weight:normal;color:#999">💡 点击表头排序</span></h4>
  <div class="detail-table" style="max-height:300px">
    <table>
      <thead><tr><th class="sortable" data-sort-type="date" onclick="sortTable(this)">日期</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">leads数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">加微数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">成交金额</th><th>操作</th></tr></thead>
      <tbody>'''

    for d in reversed(daily):
        html += f'''
        <tr class="clickable" onclick="showDateDetail('{d["date"]}','{section_id}')">
          <td style="font-weight:600">{d['date']}</td>
          <td style="color:#e74c3c;font-weight:600">{d['leads']:,}</td>
          <td style="color:#2ecc71;font-weight:600">{d['addwx']:,}</td>
          <td style="color:#e67e22;font-weight:600">¥{d['order']:,.2f}</td>
          <td><span style="color:{color};font-size:11px">达人来源 →</span></td>
        </tr>'''

    html += f'''
        <tr class="total-row"><td>总计</td><td>{totals['leads']:,}</td><td>{totals['addwx']:,}</td><td>¥{totals['order']:,.2f}</td><td></td></tr>
      </tbody>
    </table>
  </div>

  <div style="margin-top:20px">
    <h4 style="margin-bottom:6px;color:{color};">🏷️ 达人标签明细（含转化状态{"、加微率" if check_conv else ""}） <span style="font-size:10px;font-weight:normal;color:#999">💡 点击表头排序</span></h4>
    <div class="detail-table" style="max-height:600px">
      <table>
        <thead><tr>
          <th data-sort-type="rank">排名</th><th class="sortable" data-sort-type="string" onclick="sortTable(this)">达人标签</th><th class="sortable" data-sort-type="string" onclick="sortTable(this)">品类</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">总leads</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">已转化</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">转化中</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">加微数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">加微率</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">GMV</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">GMV占比</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">活跃天数</th><th class="sortable" data-sort-type="string" onclick="sortTable(this)">转化状态</th>
        </tr></thead>
        <tbody>'''

    for idx, s in enumerate(conversion, 1):
        gmv_pct = round(s["total_order"] / total_gmv * 100, 1) if total_gmv > 0 else 0
        rate_style = ""
        rate_badge = ""
        if check_conv and s["conv_rate"] < ALERT_CONV_RATE:
            rate_style = "background:#fff3cd;font-weight:700;color:#856404"
            rate_badge = ' <span class="badge badge-converting" style="font-size:9px">低</span>'
        order_style = ""
        if s["mature_leads"] > ALERT_MATURE_LEADS and s["total_order"] == 0:
            order_style = "background:#fee;font-weight:700;color:#c0392b"
        html += f'''
          <tr class="clickable" data-cat="{s.get('category','')}" onclick="showSkuDetail('{s["label"]}','{section_id}')">
            <td>{idx}</td>
            <td style="text-align:left;font-weight:600;color:{color}">{s['label']}</td>
            <td>{s.get('category','')}</td>
            <td style="color:#e74c3c;font-weight:600">{s['total_leads']:,}</td>
            <td style="color:#155724">{s['mature_leads']:,}</td>
            <td style="color:#856404">{s['converting_leads']:,}</td>
            <td>{s['total_addwx']:,}</td>
            <td style="{rate_style}">{s['conv_rate']}%{rate_badge}</td>
            <td style="{order_style}">¥{s['total_order']:,.2f}</td>
            <td>{gmv_pct}%</td>
            <td>{s['active_dates']}</td>
            <td><span class="badge badge-{s['status_class']}">{s['status']}</span></td>
          </tr>'''

    html += f'''
        </tbody>
      </table>
    </div>
    <p style="margin-top:6px;color:#888;font-size:11px">共 {len(conversion)} 个达人标签（已过滤 leads=0）</p>
  </div>
</div>'''
    return html


# ========== Month Processing ==========

def process_month(raw_data):
    """Compute all data for one month"""
    accounts = raw_data["accounts"]
    acc_map = {a["label"]: a for a in accounts}

    huacai = acc_map.get(HUACAI_LABEL)
    piano = acc_map.get(PIANO_LABEL)
    free_panels = [a for a in accounts if a["label"] != HUACAI_LABEL]

    # HC
    hc_cross = compute_cross_tabs(huacai["records"])
    hc_ds, hc_sd, hc_meta = prepare_js_data(HUACAI_LABEL, huacai["records"])
    hc_conv = compute_sku_conversion(hc_cross[1], hc_cross[2])
    hc_alerts = compute_alerts(hc_conv, check_conv_rate=True, check_r_value=True, is_huacai=True)
    hc_daily = compute_daily(huacai["records"])
    hc_totals = compute_totals(huacai["records"])
    hc_cat = compute_category_summary(huacai["records"], is_huacai=True)

    # Piano
    pn_cross = compute_cross_tabs(piano["records"])
    pn_ds, pn_sd, pn_meta = prepare_js_data(PIANO_LABEL, piano["records"])
    pn_conv = compute_sku_conversion(pn_cross[1], pn_cross[2])
    pn_alerts = compute_alerts(pn_conv, check_conv_rate=False, check_r_value=True, is_huacai=False)
    pn_daily = compute_daily(piano["records"])
    pn_totals = compute_totals(piano["records"])
    pn_cat = compute_category_summary(piano["records"], is_huacai=False)

    # Free panels
    free_all_records = []
    for a in free_panels:
        free_all_records.extend(a["records"])
    free_daily = compute_daily(free_all_records)
    free_totals = compute_totals(free_all_records)

    free_panel_data = {}
    for a in free_panels:
        ds, sd, sm = compute_cross_tabs(a["records"])
        daily = compute_daily(a["records"])
        sku_list = []
        for sku, dates in sd.items():
            t_leads = sum(d["leads"] for d in dates.values())
            t_addwx = sum(d["addwx"] for d in dates.values())
            t_uv = sum(d["uv"] for d in dates.values())
            t_order = sum(d["order"] for d in dates.values())
            t_refund = sum(d["refund"] for d in dates.values())
            if t_leads > 0 or t_order > 0:
                sku_list.append({
                    "label": sku, "category": sm[sku]["category"], "platform": sm[sku]["platform"],
                    "leads": t_leads, "addwx": t_addwx, "uv": t_uv,
                    "order": round(t_order, 2), "refund": round(t_refund, 2),
                })
        sku_list.sort(key=lambda x: x["leads"], reverse=True)
        ds_js = {}
        for dt, skus in sorted(ds.items()):
            arr = [{"label": s, **m, "order": round(m["order"], 2)} for s, m in skus.items() if m["leads"] > 0 or m["order"] > 0 or m["addwx"] > 0]
            arr.sort(key=lambda x: x["leads"], reverse=True)
            ds_js[dt] = arr
        sd_js = {}
        for sku, dates in sd.items():
            arr = [{"date": dt, **m, "order": round(m["order"], 2)} for dt, m in sorted(dates.items()) if m["leads"] > 0 or m["order"] > 0]
            if arr:
                sd_js[sku] = arr
        free_panel_data[a["label"]] = {
            "daily": daily, "sku": sku_list, "date_sku": ds_js, "sku_date": sd_js,
            "totals": compute_totals(a["records"]),
        }

    # Category summary
    category_data = defaultdict(lambda: {"leads": 0, "addwx": 0, "uv": 0, "order": 0})
    for acc in accounts:
        for r in acc["records"]:
            cat = r.get("category", "") or "未分类"
            category_data[cat]["leads"] += r.get("leadsCount", 0)
            category_data[cat]["addwx"] += r.get("addWx", 0)
            category_data[cat]["uv"] += r.get("pageUv", 0)
            category_data[cat]["order"] += r.get("orderPrice", 0)
    category_summary = [{"category": k, **v} for k, v in sorted(category_data.items(), key=lambda x: x[1]["leads"], reverse=True)]
    for c in category_summary:
        c["order"] = round(c["order"], 2)

    grand = {
        "leads": hc_totals["leads"] + free_totals["leads"],
        "addwx": hc_totals["addwx"] + free_totals["addwx"],
        "uv": hc_totals["uv"] + free_totals["uv"],
        "order": round(hc_totals["order"] + free_totals["order"], 2),
    }

    return {
        "accounts": accounts,
        "hc": {"acc": huacai, "conv": hc_conv, "alerts": hc_alerts, "daily": hc_daily, "totals": hc_totals,
                "ds": hc_ds, "sd": hc_sd, "meta": hc_meta, "r_details": prepare_r_details(hc_conv, True),
                "cat": hc_cat},
        "piano": {"acc": piano, "conv": pn_conv, "alerts": pn_alerts, "daily": pn_daily, "totals": pn_totals,
                  "ds": pn_ds, "sd": pn_sd, "meta": pn_meta, "r_details": prepare_r_details(pn_conv, False),
                  "cat": pn_cat},
        "free": {"panels": free_panels, "panel_data": free_panel_data, "daily": free_daily, "totals": free_totals},
        "category": category_summary,
        "grand": grand,
    }


# ========== Month HTML Generation ==========

def generate_month_html(month_key, md, is_current):
    hc_section = generate_panel_section(month_key, md["hc"]["acc"], md["hc"]["conv"], md["hc"]["alerts"], md["hc"]["daily"], md["hc"]["totals"], is_huacai=True)
    pn_section = generate_panel_section(month_key, md["piano"]["acc"], md["piano"]["conv"], md["piano"]["alerts"], md["piano"]["daily"], md["piano"]["totals"], is_huacai=False)

    # Free panel section
    free_panels = md["free"]["panels"]
    free_panel_data = md["free"]["panel_data"]
    free_daily = md["free"]["daily"]
    free_totals = md["free"]["totals"]

    free_table_rows = ""
    for p in sorted(free_panels, key=lambda x: free_panel_data[x["label"]]["totals"]["leads"], reverse=True):
        t = free_panel_data[p["label"]]["totals"]
        if t["order"] > 1000:
            badge = '<span class="badge badge-high">高成交</span>'
        elif t["order"] > 0:
            badge = '<span class="badge badge-mid">有成交</span>'
        elif t["addwx"] > 0:
            badge = '<span class="badge badge-low">有加微</span>'
        else:
            badge = '<span class="badge badge-zero">无数据</span>'
        if p["label"] == PIANO_LABEL:
            badge += ' <span class="badge badge-partial">📌 有独立专区</span>'
        pk = p["label"]
        free_table_rows += f'''
      <tr class="clickable" onclick="toggleFreeDetail('{pk}',this)">
        <td><span class="expand-icon">▶</span></td>
        <td style="text-align:left;font-weight:600">{p['label']}</td><td>{p['username']}</td>
        <td style="color:#e74c3c;font-weight:600">{t['leads']:,}</td>
        <td style="color:#2ecc71;font-weight:600">{t['addwx']:,}</td>
        <td>{t['uv']:,}</td>
        <td style="color:#e67e22">¥{t['order']:,.2f}</td>
        <td>{badge}</td>
      </tr>
      <tr class="detail-row" id="free-detail-{month_key}-{pk}" style="display:none"><td colspan="8"><div class="detail-content" id="free-content-{month_key}-{pk}"></div></td></tr>'''

    free_daily_rows = ""
    for d in reversed(free_daily):
        free_daily_rows += f"""
        <tr>
          <td style="font-weight:600">{d['date']}</td>
          <td style="color:#e74c3c;font-weight:600">{d['leads']:,}</td>
          <td style="color:#2ecc71;font-weight:600">{d['addwx']:,}</td>
          <td>{d['uv']:,}</td>
          <td>{d['pv']:,}</td>
          <td style="color:#e67e22">¥{d['order']:,.2f}</td>
        </tr>"""

    cat_rows = ""
    for c in md["category"]:
        cat_rows += f"""
        <tr data-cat="{c['category']}">
          <td style="text-align:left;font-weight:600">{c['category']}</td>
          <td style="color:#e74c3c;font-weight:600">{c['leads']:,}</td>
          <td style="color:#2ecc71">{c['addwx']:,}</td>
          <td>{c['uv']:,}</td>
          <td style="color:#e67e22">¥{c['order']:,.2f}</td>
        </tr>"""

    display = "" if is_current else "display:none"
    free_section = f'''
<div class="section filterable" data-section="free" style="border:3px solid #27ae60;">
  <div class="section-title" style="border-bottom-color:#27ae60;color:#27ae60;">
    <span>🎁 开开华彩0元数据汇总</span>
    <span class="hint">{len(free_panels)} 个看板（含通用钢琴）｜ 💡 点击行展开分日数据 & 达人标签</span>
  </div>
  <div class="note" style="margin-bottom:10px;font-size:11px">
    📌 本汇总已包含通用钢琴面板数据。通用钢琴同时有独立专区（上方），可查看转化状态、预警等详细分析。
  </div>
  <h4 style="margin-bottom:6px;color:#27ae60;">📋 各看板汇总 <span style="font-size:10px;font-weight:normal;color:#999">💡 点击表头排序</span></h4>
  <div class="detail-table" style="max-height:500px">
    <table>
      <thead><tr><th></th><th class="sortable" data-sort-type="string" onclick="sortTable(this)">看板名称</th><th class="sortable" data-sort-type="string" onclick="sortTable(this)">账号</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">leads数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">加微数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">UV</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">成交金额</th><th class="sortable" data-sort-type="string" onclick="sortTable(this)">状态</th></tr></thead>
      <tbody>
{free_table_rows}
        <tr class="total-row"><td></td><td>总计</td><td></td><td>{free_totals['leads']:,}</td><td>{free_totals['addwx']:,}</td><td>{free_totals['uv']:,}</td><td>¥{free_totals['order']:,.2f}</td><td></td></tr>
      </tbody>
    </table>
  </div>
  <div style="margin-top:20px">
    <h4 style="margin-bottom:6px;color:#27ae60;">📅 0元 · 分日数据汇总 <span style="font-size:10px;font-weight:normal;color:#999">💡 点击表头排序</span></h4>
    <div class="detail-table" style="max-height:400px">
      <table>
        <thead><tr><th class="sortable" data-sort-type="date" onclick="sortTable(this)">日期</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">leads数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">加微数</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">UV</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">PV</th><th class="sortable" data-sort-type="number" onclick="sortTable(this)">成交金额</th></tr></thead>
        <tbody>
{free_daily_rows}
        <tr class="total-row"><td>总计</td><td>{free_totals['leads']:,}</td><td>{free_totals['addwx']:,}</td><td>{free_totals['uv']:,}</td><td>{free_totals['pv']:,}</td><td>¥{free_totals['order']:,.2f}</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="section filterable" data-section="free" style="border:3px solid #e67e22;">
  <div class="section-title" style="border-bottom-color:#e67e22;color:#e67e22;">
    <span>📊 品类汇总</span>
  </div>
  <div class="detail-table">
    <table>
      <thead><tr><th style="text-align:left">品类</th><th>leads数</th><th>加微数</th><th>UV</th><th>成交金额</th></tr></thead>
      <tbody>
{cat_rows}
      </tbody>
    </table>
  </div>
</div>'''

    return f'''<div class="month-section" data-month="{month_key}" style="{display}">{hc_section}<div class="divider filterable-divider"></div>{pn_section}<div class="divider filterable-divider"></div>{free_section}</div>'''


# ========== Full HTML Generation ==========

def generate_full_html(months, all_months_data):
    current_month = months[0]
    current_md = all_months_data[current_month]
    grand = current_md["grand"]
    accounts = current_md["accounts"]

    # Compute today/yesterday overview
    account_daily = compute_account_daily_totals(accounts)
    overview_html = generate_overview_html(accounts, account_daily)

    # Month filter buttons
    month_buttons = ""
    for mk in months:
        y, m = mk.split("-")
        label = f"{y}年{int(m)}月"
        active = " active" if mk == current_month else ""
        month_buttons += f'<button class="month-btn{active}" data-month="{mk}" onclick="switchMonth(\'{mk}\')">{label}</button>'

    # Month sections
    month_sections = ""
    for mk in months:
        is_cur = mk == current_month
        month_sections += generate_month_html(mk, all_months_data[mk], is_cur)

    # JS data for ALL_MONTHS
    all_months_js = {}
    for mk in months:
        md = all_months_data[mk]
        # 收集该月份所有有数据的日期（去重，倒序）
        available_dates = set()
        for acc in md["accounts"]:
            for r in acc.get("records", []):
                dt = r.get("date", "")
                if dt and dt != "总计":
                    available_dates.add(dt)
        available_dates = sorted(available_dates, reverse=True)
        # 计算每个可用日期作为参考日期的 account_daily
        account_daily_by_date = {}
        for d_str in available_dates:
            account_daily_by_date[d_str] = compute_account_daily_totals(md["accounts"], d_str)
        all_months_js[mk] = {
            "hc": {"date_sku": md["hc"]["ds"], "sku_date": md["hc"]["sd"], "sku_meta": md["hc"]["meta"], "r_details": md["hc"]["r_details"], "cat": md["hc"]["cat"]},
            "piano": {"date_sku": md["piano"]["ds"], "sku_date": md["piano"]["sd"], "sku_meta": md["piano"]["meta"], "r_details": md["piano"]["r_details"], "cat": md["piano"]["cat"]},
            "free": md["free"]["panel_data"],
            "chart_data": {"hc_daily": md["hc"]["daily"], "pn_daily": md["piano"]["daily"]},
            "categories": [c["category"] for c in md["category"]],
            "available_dates": available_dates,
            "account_daily": account_daily_by_date,
        }

    # Date filter options for current month
    current_dates = all_months_js.get(current_month, {}).get("available_dates", [])
    default_date = TODAY_STR if TODAY_STR in current_dates else (current_dates[0] if current_dates else TODAY_STR)
    date_options = ""
    for d in current_dates:
        selected = " selected" if d == default_date else ""
        date_options += f'<option value="{d}"{selected}>{d}</option>'

    months_json = json.dumps(all_months_js, ensure_ascii=False)

    # CSS
    css = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f0f2f5; color:#333; padding:20px; }
.container { max-width:1400px; margin:0 auto; }
h1 { text-align:center; color:#1a1a2e; margin:20px 0 10px; font-size:26px; }
.subtitle { text-align:center; color:#666; margin-bottom:16px; font-size:13px; }
.top-bar { display:flex; align-items:center; gap:6px; flex-wrap:wrap; position:sticky; top:0; z-index:100; background:#f0f2f5; padding:6px 0; }
.month-filter { display:flex; gap:4px; }
.date-filter { display:flex; }
.date-filter select { padding:4px 10px; border-radius:14px; border:2px solid #ddd; background:#fff; cursor:pointer; font-size:11px; font-weight:600; color:#666; outline:none; }
.date-filter select:hover { border-color:#4472C4; color:#4472C4; }
.month-btn { padding:4px 12px; border-radius:14px; border:2px solid #ddd; background:#fff; cursor:pointer; font-size:11px; font-weight:600; color:#666; transition:all 0.2s; }
.month-btn:hover { border-color:#4472C4; color:#4472C4; }
.month-btn.active { background:#4472C4; color:#fff; border-color:#4472C4; }
.filter-bar { display:flex; justify-content:center; gap:4px; flex-wrap:wrap; flex:1; }
.filter-btn { padding:5px 14px; border-radius:16px; border:2px solid #ddd; background:#fff; cursor:pointer; font-size:12px; font-weight:600; color:#666; transition:all 0.2s; }
.filter-btn:hover { border-color:#4472C4; color:#4472C4; }
.filter-btn.active { background:#4472C4; color:#fff; border-color:#4472C4; }
.cat-filter { display:none; justify-content:center; gap:4px; flex-wrap:wrap; width:100%; padding-top:4px; }
.cat-filter.show { display:flex; }
.cat-btn { padding:3px 10px; border-radius:12px; border:2px solid #e8d5b0; background:#fff8ed; cursor:pointer; font-size:11px; font-weight:600; color:#8a6d3b; transition:all 0.2s; }
.cat-btn:hover { border-color:#e67e22; color:#e67e22; }
.cat-btn.active { background:#e67e22; color:#fff; border-color:#e67e22; }
.cat-btn .cat-count { font-size:9px; opacity:0.7; margin-left:2px; }
.cat-toggle { padding:5px 10px; border-radius:14px; border:2px solid #e8d5b0; background:#fff8ed; cursor:pointer; font-size:11px; font-weight:600; color:#8a6d3b; transition:all 0.2s; white-space:nowrap; }
.cat-toggle:hover { border-color:#e67e22; color:#e67e22; }
.cat-toggle.active { background:#e67e22; color:#fff; border-color:#e67e22; }
.filter-btn.active[data-filter="hc"] { background:#764ba2; border-color:#764ba2; }
.filter-btn.active[data-filter="piano"] { background:#2980b9; border-color:#2980b9; }
.filter-btn.active[data-filter="free"] { background:#27ae60; border-color:#27ae60; }
.theme-toggle { width:38px; height:38px; border-radius:50%; border:2px solid #ddd; background:#fff; cursor:pointer; font-size:16px; display:flex; align-items:center; justify-content:center; transition:all 0.2s; flex-shrink:0; }
.theme-toggle:hover { border-color:#ffc107; }
.theme-toggle::after { content:'\\1F319'; }
body.dark .theme-toggle::after { content:'\\2600\\FE0F'; }
.section { background:#fff; border-radius:12px; padding:24px; margin-bottom:24px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.section-title { font-size:17px; font-weight:600; margin-bottom:14px; padding-bottom:10px; border-bottom:2px solid #4472C4; color:#1a1a2e; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }
.section-title .hint { font-size:11px; color:#888; font-weight:normal; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { background:#4472C4; color:#fff; padding:9px 6px; text-align:center; font-weight:600; white-space:nowrap; position:sticky; top:0; z-index:1; }
td { padding:7px 6px; text-align:center; border-bottom:1px solid #eee; }
tr:hover td { background:#f8f9ff; }
tr.total-row td { background:#fff8e1; font-weight:600; }
.clickable { cursor:pointer; transition:background 0.15s; }
.clickable:hover { background:#e8f0fe !important; }
tr.expanded .expand-icon { transform:rotate(90deg); }
.expand-icon { display:inline-block; width:14px; text-align:center; transition:transform 0.2s; }
.chart-container { position:relative; height:300px; margin:16px 0; }
.detail-table { max-height:450px; overflow-y:auto; border:1px solid #eee; border-radius:6px; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-mature { background:#d4edda; color:#155724; }
.badge-converting { background:#fff3cd; color:#856404; }
.badge-partial { background:#d1ecf1; color:#0c5460; }
.badge-high { background:#fee; color:#c0392b; }
.badge-mid { background:#fef9e7; color:#e67e22; }
.badge-low { background:#eafaf1; color:#27ae60; }
.badge-zero { background:#f0f0f0; color:#999; }
.detail-row td { padding:0; border:none; }
.detail-content { padding:14px 20px; background:#f8f9ff; border:2px solid #d4e4fc; border-radius:8px; margin:6px; }
.detail-tabs { display:flex; gap:6px; margin-bottom:10px; flex-wrap:wrap; }
.detail-tab { padding:5px 14px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600; border:2px solid #ddd; background:#fff; }
.detail-tab.active { background:#4472C4; color:#fff; border-color:#4472C4; }
.detail-pane { display:none; }
.detail-pane.active { display:block; }
.modal-overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:9999; justify-content:center; align-items:flex-start; padding:40px 20px; overflow-y:auto; }
.modal-overlay.show { display:flex; }
.modal-box { background:#fff; border-radius:12px; max-width:900px; width:100%; box-shadow:0 8px 32px rgba(0,0,0,0.2); overflow:hidden; }
.modal-header { background:linear-gradient(135deg,#4472C4,#764ba2); color:#fff; padding:16px 24px; font-size:16px; font-weight:600; display:flex; justify-content:space-between; align-items:center; }
.modal-close { cursor:pointer; font-size:22px; opacity:0.8; }
.modal-close:hover { opacity:1; }
.modal-body { padding:20px 24px; max-height:70vh; overflow-y:auto; }
.modal-body table { font-size:12px; }
.hc-hero { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; margin-bottom:16px; }
.hc-hero-item { background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; border-radius:10px; padding:14px; text-align:center; }
.hc-hero-item .v { font-size:22px; font-weight:700; margin-top:2px; }
.hc-hero-item .l { font-size:11px; opacity:0.9; }
.hc-hero-item.gold { background:linear-gradient(135deg,#f6d365,#fda085); }
.hc-hero-item.green { background:linear-gradient(135deg,#84fab0,#8fd3f4); color:#1a1a2e; }
.hc-hero-item.blue { background:linear-gradient(135deg,#a18cd1,#fbc2eb); color:#1a1a2e; }
.conv-summary { display:flex; gap:12px; flex-wrap:wrap; }
.conv-card { padding:10px 18px; border-radius:8px; font-size:13px; }
.conv-card.mature { background:#d4edda; color:#155724; }
.conv-card.converting { background:#fff3cd; color:#856404; }
.conv-card.gmv { background:#fde8f0; color:#c0392b; }
.conv-card .num { font-size:20px; font-weight:700; }
.note { background:#fff8e1; border-left:4px solid #ffc107; padding:10px 14px; margin:12px 0; border-radius:4px; font-size:12px; color:#666; }
.divider { height:3px; background:linear-gradient(90deg,transparent,#4472C4,transparent); margin:32px 0; border-radius:2px; }
.alert-box { border-radius:8px; margin:14px 0; overflow:hidden; }
.alert-box.ok { background:#d4edda; padding:12px 16px; color:#155724; font-size:13px; }
.alert-box:not(.ok) { border:2px solid #ffc107; }
.alert-header { background:#fff3cd; padding:10px 16px; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.alert-icon { font-size:16px; }
.alert-title { font-weight:700; font-size:14px; color:#856404; }
.alert-counts { margin-left:auto; }
.alert-tag { display:inline-block; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; margin-left:4px; }
.alert-tag.danger { background:#fee; color:#c0392b; }
.alert-tag.warning { background:#fff3cd; color:#856404; }
.alert-list { background:#fffbea; }
.alert-item { padding:8px 16px; border-bottom:1px solid #ffeaa7; display:flex; align-items:center; gap:8px; font-size:12px; }
.alert-item.danger { background:#fff5f5; }
.alert-item-icon { font-size:14px; }
.alert-item-type { font-weight:700; min-width:80px; color:#c0392b; }
.alert-item.danger .alert-item-type { color:#c0392b; }
.alert-item.warning .alert-item-type { color:#856404; }
.alert-item-sku { font-weight:600; color:#4472C4; cursor:pointer; text-decoration:underline; min-width:100px; }
.alert-item-detail { color:#555; }
.alert-item:hover { background:#fff3cd; }
.r-tooltip { display:none; position:fixed; z-index:10001; background:#fff; border-radius:10px; box-shadow:0 8px 28px rgba(0,0,0,0.2); padding:14px; max-width:520px; max-height:420px; overflow-y:auto; border:2px solid #4472C4; }
.r-tooltip table { width:100%; font-size:11px; border-collapse:collapse; }
.r-tooltip th { background:#4472C4; color:#fff; padding:5px 8px; text-align:center; font-weight:600; white-space:nowrap; }
.r-tooltip td { padding:4px 8px; text-align:center; border-bottom:1px solid #eee; }
.r-tooltip tr:hover td { background:#f8f9ff; }
th.sortable { cursor:pointer; user-select:none; }
th.sortable:hover { background:#5a82d4; }
th.sortable::after { content:' \\21C5'; font-size:10px; opacity:0.4; }
th.sortable.sort-asc::after { content:' \\2191'; opacity:1; font-weight:bold; }
th.sortable.sort-desc::after { content:' \\2193'; opacity:1; font-weight:bold; }
/* Dark Mode */
body.dark { background:#0f0f1e; color:#e0e0e0; }
body.dark h1 { color:#e0e0e0; }
body.dark .subtitle { color:#999; }
body.dark .top-bar { background:rgba(15,15,30,0.95); }
body.dark .month-btn { background:#1e1e3a; color:#ccc; border-color:#333; }
body.dark .month-btn:hover { border-color:#4472C4; color:#6e8aff; }
body.dark .month-btn.active { background:#4472C4; color:#fff; border-color:#4472C4; }
body.dark .filter-btn { background:#1e1e3a; color:#ccc; border-color:#333; }
body.dark .filter-btn:hover { border-color:#4472C4; color:#6e8aff; }
body.dark .filter-btn.active { background:#4472C4; color:#fff; }
body.dark .cat-btn { background:#2a2210; color:#daa520; border-color:#443818; }
body.dark .cat-btn:hover { border-color:#e67e22; color:#f0a050; }
body.dark .cat-btn.active { background:#e67e22; color:#fff; border-color:#e67e22; }
body.dark .cat-toggle { background:#2a2210; color:#daa520; border-color:#443818; }
body.dark .cat-toggle:hover { border-color:#e67e22; color:#f0a050; }
body.dark .cat-toggle.active { background:#e67e22; color:#fff; border-color:#e67e22; }
body.dark .filter-btn.active[data-filter="hc"] { background:#764ba2; }
body.dark .filter-btn.active[data-filter="piano"] { background:#2980b9; }
body.dark .filter-btn.active[data-filter="free"] { background:#27ae60; }
body.dark .theme-toggle { background:#1e1e3a; border-color:#333; }
body.dark .section { background:#1a1a2e; box-shadow:0 2px 8px rgba(0,0,0,0.3); }
body.dark .section-title { color:#e0e0e0; }
body.dark table th { background:#2d3561; }
body.dark td { border-bottom-color:#2a2a4a; }
body.dark tr:hover td { background:#252545; }
body.dark tr.total-row td { background:#252545; }
body.dark .clickable:hover { background:#252545 !important; }
body.dark .detail-content { background:#1e1e3a; border-color:#2d3561; }
body.dark .detail-tab { background:#1e1e3a; border-color:#333; color:#ccc; }
body.dark .detail-tab.active { background:#4472C4; color:#fff; }
body.dark .detail-table { border-color:#2a2a4a; }
body.dark .modal-box { background:#1a1a2e; }
body.dark .modal-body { background:#1a1a2e; }
body.dark .note { background:#2d2818; color:#aaa; border-left-color:#ffc107; }
body.dark .alert-box.ok { background:#1a3d1a; color:#6abe6a; }
body.dark .alert-box:not(.ok) { border-color:#555; }
body.dark .alert-header { background:#3d3520; }
body.dark .alert-title { color:#daa520; }
body.dark .alert-list { background:#1e1e3a; }
body.dark .alert-item { border-bottom-color:#333; color:#ccc; }
body.dark .alert-item.danger { background:#2d1a1a; }
body.dark .alert-item:hover { background:#2d2535; }
body.dark .alert-item-sku { color:#6e8aff; }
body.dark .alert-item-detail { color:#999; }
body.dark .alert-tag.danger { background:#3d1a1a; color:#ff6b6b; }
body.dark .alert-tag.warning { background:#3d3520; color:#daa520; }
body.dark .badge-mature { background:#1a3d1a; color:#6abe6a; }
body.dark .badge-converting { background:#3d3520; color:#daa520; }
body.dark .badge-partial { background:#1a2d3d; color:#5dade2; }
body.dark .badge-high { background:#3d1a1a; color:#ff6b6b; }
body.dark .badge-mid { background:#3d2d1a; color:#f0a050; }
body.dark .badge-low { background:#1a3d2a; color:#6abe6a; }
body.dark .badge-zero { background:#2a2a2a; color:#666; }
body.dark .conv-card.mature { background:#1a3d1a; color:#6abe6a; }
body.dark .conv-card.converting { background:#3d3520; color:#daa520; }
body.dark .conv-card.gmv { background:#3d1a2a; color:#ff6b6b; }
body.dark .r-tooltip { background:#1a1a2e; border-color:#4472C4; }
body.dark .r-tooltip td { border-bottom-color:#2a2a4a; }
body.dark .r-tooltip tr:hover td { background:#252545; }
body.dark .r-card { background:#1a1a2e !important; }
body.dark [style*="background:#fff"] { background-color:#1a1a2e !important; }
body.dark [style*="background:#f8f9ff"] { background-color:#1e1e3a !important; }
body.dark [style*="background:#f5f7fa"] { background-color:#0f0f1e !important; }
/* Overview Section - compact table style */
.ov-section { background:#fff; border-radius:12px; padding:20px 24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.ov-header { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:16px; }
.ov-title { font-size:18px; font-weight:700; color:#1a1a2e; }
.ov-date-info { font-size:13px; color:#888; }
.ov-block { margin-bottom:12px; }
.ov-block-title { font-size:14px; font-weight:600; color:#555; margin-bottom:6px; padding-left:4px; }
.ov-block-sub { font-size:12px; color:#999; margin-top:4px; padding-left:4px; }
.ov-table-header { display:flex; gap:8px; padding:4px 8px; font-size:12px; color:#999; font-weight:600; border-bottom:1px solid #e0e0e0; margin-bottom:2px; }
.ov-table-row { display:flex; gap:8px; padding:6px 8px; border-radius:6px; font-size:13px; align-items:center; transition:background 0.2s; }
.ov-table-row:hover { background:#f5f5f5; }
.ov-row-huacai { background:#f0e8ff; font-weight:600; }
.ov-row-active { }
.ov-row-zero { color:#bbb; }
.ov-row-total { background:#e8f4e8; font-weight:700; border-top:2px solid #2ecc71; margin-top:4px; padding:8px 8px; }
.ov-cell-label { flex:1; font-weight:600; min-width:120px; }
.ov-cell-day { flex:0 0 70px; text-align:right; color:#155724; font-weight:700; }
.ov-cell-delta { flex:0 0 70px; text-align:right; }
.ov-delta { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:700; }
.ov-delta.ov-up { background:#d4edda; color:#155724; }
.ov-delta.ov-down { background:#fee; color:#c0392b; }
.ov-delta.ov-flat { background:#f0f0f0; color:#999; }
.ov-delta.ov-new { background:#d1ecf1; color:#0c5460; }
/* Dark mode */
body.dark .ov-section { background:#1a1a2e; }
body.dark .ov-title { color:#e0e0e0; }
body.dark .ov-date-info { color:#888; }
body.dark .ov-block-title { color:#bbb; }
body.dark .ov-block-sub { color:#777; }
body.dark .ov-table-header { color:#888; border-bottom-color:#333; }
body.dark .ov-table-row:hover { background:#252540; }
body.dark .ov-row-huacai { background:#2d1a4d; }
body.dark .ov-row-active { color:#ddd; }
body.dark .ov-row-zero { color:#555; }
body.dark .ov-row-total { background:#1a3d1a; border-top-color:#6abe6a; color:#ddd; }
body.dark .ov-cell-day { color:#6abe6a; }
body.dark .ov-delta.ov-up { background:#1a3d1a; color:#6abe6a; }
body.dark .ov-delta.ov-down { background:#3d1a1a; color:#ff6b6b; }
body.dark .ov-delta.ov-flat { background:#2a2a2a; color:#666; }
body.dark .ov-delta.ov-new { background:#1a2d3d; color:#5dade2; }
/* Mobile responsive - compact top bar */
@media (max-width: 768px) {
  body { padding:10px; }
  h1 { font-size:20px; margin:10px 0 6px; }
  .subtitle { font-size:11px; margin-bottom:8px; }
  .top-bar { padding:4px 0; gap:4px; }
  .month-btn { padding:3px 10px; font-size:10px; }
  .filter-btn { padding:4px 10px; font-size:11px; }
  .cat-btn { padding:3px 8px; font-size:10px; }
  .cat-toggle { padding:4px 8px; font-size:10px; }
  .theme-toggle { width:32px; height:32px; font-size:14px; }
  .section { padding:14px; }
  .section-title { font-size:15px; }
  .hc-hero-item .v { font-size:18px; }
  .hc-hero-item .l { font-size:10px; }
  .conv-card { padding:8px 12px; font-size:12px; }
  .conv-card .num { font-size:16px; }
  .ov-section { padding:14px 16px; margin-bottom:12px; }
  .ov-title { font-size:15px; }
  .ov-date-info { font-size:11px; }
  .ov-table-row { font-size:12px; padding:4px 6px; }
  .ov-cell-label { min-width:80px; font-size:12px; }
  .ov-cell-day { flex:0 0 55px; font-size:12px; }
  .ov-cell-delta { flex:0 0 50px; }
  .ov-delta { font-size:9px; padding:1px 4px; }
  table { font-size:11px; }
  th { padding:6px 4px; }
  td { padding:5px 4px; }
}
"""

    # Core JS (before CDN)
    js_core = f"""
const ALL_MONTHS = {months_json};
let CURRENT_MONTH = '{current_month}';
let ALL_DATA = ALL_MONTHS['{current_month}'];
let CURRENT_DATE = '{default_date}';
const CUTOFF = '{CUTOFF_DATE}';
const TODAY_STR = '{TODAY.strftime("%Y-%m-%d")}';
let CHART_INSTANCES = {{}};
let initChartsFn = function(mk) {{}};
let CURRENT_CAT = 'all';
const DOW_NAMES = ['周一','周二','周三','周四','周五','周六','周日'];

function getPanelData(sectionId) {{
  const mData = ALL_MONTHS[CURRENT_MONTH];
  const panelCat = mData[sectionId]?.cat || {{}};
  if (CURRENT_CAT === 'all') {{
    let t = {{leads:0, addwx:0, order:0}};
    let c = {{mature_leads:0, converting_leads:0, gmv:0, sku_count:0, mature_addwx:0, converting_addwx:0, mature_order:0, converting_order:0}};
    Object.values(panelCat).forEach(cat => {{
      t.leads += cat.totals.leads; t.addwx += cat.totals.addwx; t.order += cat.totals.order;
      c.mature_leads += cat.conv.mature_leads; c.converting_leads += cat.conv.converting_leads;
      c.gmv += cat.conv.gmv; c.sku_count += cat.conv.sku_count;
      c.mature_addwx += cat.conv.mature_addwx; c.converting_addwx += cat.conv.converting_addwx;
      c.mature_order += cat.conv.mature_order; c.converting_order += cat.conv.converting_order;
    }});
    const isHc = sectionId === 'hc';
    const rDenom = isHc ? c.mature_leads + c.converting_leads : c.mature_addwx + c.converting_addwx;
    const rMD = isHc ? c.mature_leads : c.mature_addwx;
    const rCD = isHc ? c.converting_leads : c.converting_addwx;
    return {{totals:t, conv:c, r:{{
      mature: rMD>0 ? Math.round(c.mature_order/rMD*100)/100 : 0,
      converting: rCD>0 ? Math.round(c.converting_order/rCD*100)/100 : 0,
      total: rDenom>0 ? Math.round(c.gmv/rDenom*100)/100 : 0,
      mature_denom:rMD, converting_denom:rCD, total_denom:rDenom, gmv:c.gmv
    }}}};
  }}
  return panelCat[CURRENT_CAT] || {{totals:{{leads:0,addwx:0,order:0}}, conv:{{mature_leads:0,converting_leads:0,gmv:0,sku_count:0}}, r:{{mature:0,converting:0,total:0,mature_denom:0,converting_denom:0,total_denom:0,gmv:0}}}};
}}

function updatePanelKPIs(sectionId) {{
  const section = document.querySelector('.month-section[data-month="' + CURRENT_MONTH + '"]');
  if (!section) return;
  const panelEl = section.querySelector('[data-section="' + sectionId + '"]');
  if (!panelEl) return;
  const d = getPanelData(sectionId);
  const isHc = sectionId === 'hc';
  const rLabel = isHc ? 'leads' : '加微';
  const fmtN = n => (n||0).toLocaleString();
  const fmtY = n => '¥' + Math.round(n||0).toLocaleString();
  const fmtR = n => '¥' + (Math.round((n||0)*100)/100);
  panelEl.querySelectorAll('[data-cat-kpi]').forEach(el => {{
    const k = el.dataset.catKpi;
    switch(k) {{
      case 'kpi-leads': el.textContent = fmtN(d.totals.leads); break;
      case 'kpi-addwx': el.textContent = fmtN(d.totals.addwx); break;
      case 'kpi-order': el.textContent = fmtY(d.totals.order); break;
      case 'header-totals': el.textContent = 'leads ' + fmtN(d.totals.leads) + ' ｜ 加微 ' + fmtN(d.totals.addwx) + ' ｜ 成交 ' + fmtY(d.totals.order); break;
      case 'conv-mature': el.textContent = fmtN(d.conv.mature_leads); break;
      case 'conv-converting': el.textContent = fmtN(d.conv.converting_leads); break;
      case 'conv-gmv': el.textContent = fmtY(d.conv.gmv); break;
      case 'conv-sku-count': el.textContent = fmtN(d.conv.sku_count); break;
      case 'r-mature-val': el.textContent = fmtR(d.r.mature); break;
      case 'r-mature-formula': el.textContent = fmtY(d.r.gmv ? (isHc ? d.conv.mature_order : d.conv.mature_order) : 0) + ' ÷ ' + fmtN(d.r.mature_denom) + ' ' + rLabel; break;
      case 'r-converting-val': el.textContent = fmtR(d.r.converting); break;
      case 'r-converting-formula': el.textContent = fmtY(isHc ? d.conv.converting_order : d.conv.converting_order) + ' ÷ ' + fmtN(d.r.converting_denom) + ' ' + rLabel; break;
      case 'r-total-val': el.textContent = fmtR(d.r.total); break;
      case 'r-total-formula': el.textContent = fmtY(d.r.gmv) + ' ÷ ' + fmtN(d.r.total_denom) + ' ' + rLabel; break;
    }}
  }});
}}

let refreshChartsForCatFn = function() {{}};

function buildCatFilter(monthKey) {{
  const cats = ALL_MONTHS[monthKey]?.categories || [];
  const container = document.getElementById('catFilter');
  if (!container) return;
  let html = '<button class="cat-btn active" data-cat="all" onclick="filterCategory(\\'all\\',this)">🏷️ 全部品类</button>';
  const catEmoji = {{'书法':'✍️','声乐':'🎤','声乐-月课':'🎵','朗诵':'📖','钢琴':'🎹'}};
  cats.forEach(c => {{
    const emoji = catEmoji[c] || '📌';
    html += '<button class="cat-btn" data-cat="' + c + '" onclick="filterCategory(\\'' + c + '\\',this)">' + emoji + ' ' + c + '</button>';
  }});
  container.innerHTML = html;
  CURRENT_CAT = 'all';
}}

function filterCategory(cat, btn) {{
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  CURRENT_CAT = cat;
  applyCategoryFilter();
}}

function applyCategoryFilter() {{
  const section = document.querySelector('.month-section[data-month="' + CURRENT_MONTH + '"]');
  if (!section) return;
  const catRows = section.querySelectorAll('tr[data-cat]');
  catRows.forEach(row => {{
    if (CURRENT_CAT === 'all') {{
      row.style.display = '';
    }} else {{
      row.style.display = row.dataset.cat === CURRENT_CAT ? '' : 'none';
    }}
  }});
  section.querySelectorAll('tr.total-row').forEach(r => r.style.display = '');

  // Filter alert items by category
  const alertItems = section.querySelectorAll('.alert-item[data-cat]');
  let visDanger = 0, visWarning = 0, visTotal = 0;
  alertItems.forEach(item => {{
    if (CURRENT_CAT === 'all') {{
      item.style.display = '';
    }} else {{
      item.style.display = item.dataset.cat === CURRENT_CAT ? '' : 'none';
    }}
    if (item.style.display !== 'none') {{
      visTotal++;
      if (item.classList.contains('danger')) visDanger++;
      if (item.classList.contains('warning')) visWarning++;
    }}
  }});
  // Update alert counts
  section.querySelectorAll('[data-alert-count="danger"]').forEach(el => el.textContent = visDanger + ' 项严重');
  section.querySelectorAll('[data-alert-count="warning"]').forEach(el => el.textContent = visWarning + ' 项警告');
  section.querySelectorAll('[data-alert-count="total"]').forEach(el => el.textContent = '共 ' + visTotal + ' 项');
  // Hide alert-counts tags with 0 count
  section.querySelectorAll('[data-alert-count="danger"]').forEach(el => el.style.display = visDanger > 0 ? '' : 'none');
  section.querySelectorAll('[data-alert-count="warning"]').forEach(el => el.style.display = visWarning > 0 ? '' : 'none');

  updatePanelKPIs('hc');
  updatePanelKPIs('piano');
  refreshChartsForCatFn();
}}

function openModal(title, bodyHtml) {{ document.getElementById('modalTitle').textContent = title; document.getElementById('modalBody').innerHTML = bodyHtml; document.getElementById('modal').classList.add('show'); }}
function closeModal() {{ document.getElementById('modal').classList.remove('show'); }}
function fmt(n) {{ return (n||0).toLocaleString(); }}

const R_TARGET = {R_VALUE_TARGET};
function showRDetail(type, section, event) {{
  const data = ALL_DATA[section]?.r_details?.[type];
  if (!data || data.length === 0) return;
  const title = type === 'mature' ? '已转化R值明细' : '转化中R值明细';
  const dLabel = section === 'hc' ? 'leads' : '加微';
  let h = '<div style="font-weight:700;margin-bottom:8px;font-size:13px;color:#333">' + title + '（目标¥' + R_TARGET + '）</div>';
  h += '<table><thead><tr><th style="text-align:left">达人标签</th><th>R值</th><th>GMV</th><th>' + dLabel + '</th><th>状态</th></tr></thead><tbody>';
  data.forEach(d => {{
    const isLow = d.r < R_TARGET;
    const c = isLow ? '#c0392b' : '#27ae60';
    const st = isLow ? '🔴低于目标' : '🟢达标';
    h += '<tr><td style="text-align:left;font-weight:600">' + d.label + '</td><td style="color:' + c + ';font-weight:700">¥' + d.r + '</td><td>¥' + d.gmv.toFixed(0) + '</td><td>' + d.denom + '</td><td style="color:' + c + '">' + st + '</td></tr>';
  }});
  h += '</tbody></table>';
  const tip = document.getElementById('rTooltip');
  tip.innerHTML = h;
  tip.style.display = 'block';
  const rect = event.currentTarget.getBoundingClientRect();
  let left = rect.left;
  let top = rect.bottom + 8;
  if (left + 540 > window.innerWidth) left = window.innerWidth - 560;
  if (left < 10) left = 10;
  if (top + 430 > window.innerHeight) top = rect.top - 440;
  if (top < 10) top = 10;
  tip.style.left = left + 'px';
  tip.style.top = top + 'px';
}}
function hideRDetail() {{ document.getElementById('rTooltip').style.display = 'none'; }}

function switchMonth(key) {{
  CURRENT_MONTH = key;
  ALL_DATA = ALL_MONTHS[key];
  document.querySelectorAll('.month-section').forEach(el => {{
    el.style.display = el.dataset.month === key ? '' : 'none';
  }});
  document.querySelectorAll('.month-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.dataset.month === key);
  }});
  buildDateFilter(key);
  buildCatFilter(key);
  CURRENT_CAT = 'all';
  filterData('all', document.querySelector('.filter-btn[data-filter="all"]'));
  initChartsFn(key);
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function buildDateFilter(monthKey) {{
  const dates = ALL_MONTHS[monthKey]?.available_dates || [];
  const select = document.getElementById('dateFilter');
  if (!select || dates.length === 0) return;
  let html = '';
  dates.forEach(d => {{
    html += '<option value="' + d + '"' + (d === CURRENT_DATE ? ' selected' : '') + '>' + d + '</option>';
  }});
  select.innerHTML = html;
  if (!dates.includes(CURRENT_DATE)) {{
    CURRENT_DATE = dates[0];
    select.value = CURRENT_DATE;
  }}
  updateOverview(CURRENT_DATE);
}}

function changeDate(dateStr) {{
  CURRENT_DATE = dateStr;
  updateOverview(dateStr);
}}

function fmt(n) {{ return (n || 0).toLocaleString(); }}

function deltaHtml(current, previous) {{
  if (previous === 0 && current === 0) return '';
  if (previous === 0) return '<span class="ov-delta ov-new">NEW</span>';
  const pct = Math.round((current - previous) / previous * 100);
  if (pct > 0) return '<span class="ov-delta ov-up">+' + pct + '%</span>';
  if (pct < 0) return '<span class="ov-delta ov-down">' + pct + '%</span>';
  return '<span class="ov-delta ov-flat">0%</span>';
}}

function dayLabel(dStr) {{
  const d = new Date(dStr + 'T00:00:00');
  return dStr.slice(5) + '(' + DOW_NAMES[d.getDay() === 0 ? 6 : d.getDay() - 1] + ')';
}}

function updateOverview(dateStr) {{
  const section = document.getElementById('overviewSection');
  if (!section) return;
  const accountDaily = ALL_MONTHS[CURRENT_MONTH]?.account_daily?.[dateStr];
  if (!accountDaily) return;
  const huacaiLabel = '华彩课包面板';
  const huacai = accountDaily[huacaiLabel] || {{prev:{{leads:0,addwx:0}},cur:{{leads:0,addwx:0}}}};
  let others = Object.entries(accountDaily).filter(([k]) => k !== huacaiLabel);
  others.sort((a,b) => Math.max(b[1].prev.addwx,b[1].cur.addwx) - Math.max(a[1].prev.addwx,a[1].cur.addwx));

  const prevStr = huacai.prev_str || new Date(new Date(dateStr + 'T00:00:00').getTime() - 86400000).toISOString().slice(0,10);
  const curStr = huacai.cur_str || dateStr;

  const prevDisplay = dayLabel(prevStr);
  const curDisplay = dayLabel(curStr);

  const hcDelta = deltaHtml(huacai.cur.leads, huacai.prev.leads);

  let otherRows = '';
  others.forEach(([label, stats]) => {{
    const pv = stats.prev.addwx, cv = stats.cur.addwx;
    const active = (pv > 0 || cv > 0) ? 'ov-row-active' : 'ov-row-zero';
    otherRows += '<div class="ov-table-row ' + active + '"><span class="ov-cell-label">' + label + '</span><span class="ov-cell-day">' + fmt(pv) + '</span><span class="ov-cell-delta">' + deltaHtml(cv, pv) + '</span><span class="ov-cell-day">' + fmt(cv) + '</span></div>';
  }});

  const otherPrevTotal = others.reduce((s,[,x]) => s + x.prev.addwx, 0);
  const otherCurTotal = others.reduce((s,[,x]) => s + x.cur.addwx, 0);

  const html = '<div class="ov-section" id="overviewSection"><div class="ov-header"><span class="ov-title">📊 投放量级速览</span><span class="ov-date-info">' + prevDisplay + ' → ' + curDisplay + '</span></div>' +
    '<div class="ov-block"><div class="ov-block-title">🎬 华彩课包 · leads</div><div class="ov-table-row ov-row-huacai"><span class="ov-cell-label">华彩课包面板</span><span class="ov-cell-day">' + fmt(huacai.prev.leads) + '</span><span class="ov-cell-delta">' + hcDelta + '</span><span class="ov-cell-day">' + fmt(huacai.cur.leads) + '</span></div>' +
    '<div class="ov-block-sub">加微 ' + fmt(huacai.prev.addwx) + '→' + fmt(huacai.cur.addwx) + '</div></div>' +
    '<div class="ov-block"><div class="ov-block-title">🎹 其他看板 · 加微</div><div class="ov-table-header"><span class="ov-cell-label">看板</span><span class="ov-cell-day">' + prevDisplay + '</span><span class="ov-cell-delta">变化</span><span class="ov-cell-day">' + curDisplay + '</span></div>' + otherRows +
    '<div class="ov-table-row ov-row-total"><span class="ov-cell-label">合计</span><span class="ov-cell-day">' + fmt(otherPrevTotal) + '</span><span class="ov-cell-delta">' + deltaHtml(otherCurTotal, otherPrevTotal) + '</span><span class="ov-cell-day">' + fmt(otherCurTotal) + '</span></div></div></div>';

  section.outerHTML = html;
}}



function filterData(type, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const section = document.querySelector('.month-section[data-month="' + CURRENT_MONTH + '"]');
  if (!section) return;
  const items = section.querySelectorAll('.filterable');
  const dividers = section.querySelectorAll('.filterable-divider');
  const overview = document.getElementById('overviewSection');
  if (type === 'all') {{
    items.forEach(s => s.style.display = '');
    dividers.forEach(d => d.style.display = '');
    if (overview) overview.style.display = '';
  }} else {{
    items.forEach(s => {{ s.style.display = s.dataset.section === type ? '' : 'none'; }});
    dividers.forEach(d => d.style.display = 'none');
    if (overview) overview.style.display = 'none';
  }}
  applyCategoryFilter();
}}

function toggleTheme() {{
  const isDark = document.body.classList.toggle('dark');
  localStorage.setItem('kk-theme', isDark ? 'dark' : 'light');
}}
function toggleCatFilter() {{
  const cf = document.getElementById('catFilter');
  const btn = document.getElementById('catToggle');
  cf.classList.toggle('show');
  btn.classList.toggle('active');
}}
(function() {{
  if (localStorage.getItem('kk-theme') === 'dark') document.body.classList.add('dark');
  buildDateFilter(CURRENT_MONTH);
  buildCatFilter(CURRENT_MONTH);
}})();

function showDateDetail(date, section) {{
  let skus;
  if (section === 'hc') skus = ALL_DATA.hc.date_sku[date] || [];
  else if (section === 'piano') skus = ALL_DATA.piano.date_sku[date] || [];
  else skus = ALL_DATA.free[section]?.date_sku[date] || [];
  if (!skus || skus.length === 0) {{ openModal('📅 ' + date + ' 达人来源', '<p style="text-align:center;color:#999;padding:20px">该日期暂无达人数据</p>'); return; }}
  const tL = skus.reduce((s,x)=>s+x.leads,0), tO = skus.reduce((s,x)=>s+x.order,0);
  let h = '<div style="margin-bottom:10px;font-size:13px;color:#666">当日共 <b>'+skus.length+'</b> 个达人贡献，leads '+fmt(tL)+'，成交 ¥'+tO.toFixed(2)+'</div>';
  const showUV = !(section === 'hc' || section === 'piano');
  h += '<div class="detail-table"><table><thead><tr><th>排名</th><th>达人标签</th><th>leads数</th><th>加微数</th>'+(showUV?'<th>UV</th>':'')+'<th>成交金额</th><th>leads占比</th></tr></thead><tbody>';
  skus.forEach((s,i)=>{{ const pct=tL>0?(s.leads/tL*100).toFixed(1):0; h+='<tr class="clickable" onclick="showSkuDetail(\\''+s.label+'\\',\\''+section+'\\')"><td>'+(i+1)+'</td><td style="text-align:left;font-weight:600;color:#4472C4">'+s.label+'</td><td style="color:#e74c3c;font-weight:600">'+fmt(s.leads)+'</td><td style="color:#2ecc71">'+fmt(s.addwx)+'</td>'+(showUV?'<td>'+fmt(s.uv)+'</td>':'')+'<td style="color:#e67e22">¥'+s.order.toFixed(2)+'</td><td>'+pct+'%</td></tr>'; }});
  h += '</tbody></table></div><p style="margin-top:8px;font-size:11px;color:#4472C4">💡 点击达人行查看日量级数据和 GMV 贡献</p>';
  openModal('📅 ' + date + ' · 当日达人来源', h);
}}

function showSkuDetail(sku, section) {{
  let daily, meta={{}};
  if (section === 'hc') {{ daily = ALL_DATA.hc.sku_date[sku] || []; meta = ALL_DATA.hc.sku_meta[sku] || {{}}; }}
  else if (section === 'piano') {{ daily = ALL_DATA.piano.sku_date[sku] || []; meta = ALL_DATA.piano.sku_meta[sku] || {{}}; }}
  else {{ daily = ALL_DATA.free[section]?.sku_date[sku] || []; }}
  if (!daily || daily.length === 0) {{ openModal('🏷️ ' + sku, '<p style="text-align:center;color:#999;padding:20px">暂无日量级数据</p>'); return; }}
  const tL = daily.reduce((s,x)=>s+x.leads,0), tA = daily.reduce((s,x)=>s+x.addwx,0), tO = daily.reduce((s,x)=>s+x.order,0), tU = daily.reduce((s,x)=>s+x.uv,0);
  const mL = daily.filter(d=>d.date<=CUTOFF).reduce((s,x)=>s+x.leads,0), cL = tL - mL;
  const cR = tL > 0 ? (tA/tL*100).toFixed(1) : 0;
  const showUV = !(section === 'hc' || section === 'piano');
  let sB; if (cL===0) sB='<span class="badge badge-mature">已转化完毕</span>'; else if (mL===0) sB='<span class="badge badge-converting">转化中</span>'; else sB='<span class="badge badge-partial">部分转化中</span>';
  let h = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:14px">';
  h += sc('总 leads', tL, '#e74c3c'); h += sc('已转化', mL, '#155724'); h += sc('转化中', cL, '#856404');
  h += sc('加微数', tA, '#2ecc71'); h += sc('加微率', cR+'%', '#3498db'); h += sc('总 GMV', '¥'+tO.toFixed(0), '#e67e22');
  if (showUV) h += sc('总 UV', tU, '#9b59b6'); h += sc('活跃天数', daily.length, '#666');
  h += '</div><div style="margin-bottom:10px;font-size:13px">转化状态：'+sB+' ｜ 品类：'+(meta.category||'-')+'</div>';
  h += '<div class="detail-table"><table><thead><tr><th>日期</th><th>距今天数</th><th>leads</th><th>加微</th>'+(showUV?'<th>UV</th>':'')+'<th>成交金额</th><th>GMV累计</th><th>转化阶段</th></tr></thead><tbody>';
  let cum=0; daily.forEach(d=>{{ cum+=d.order; const diff=Math.floor((new Date(TODAY_STR)-new Date(d.date))/86400000); const st=d.date<=CUTOFF?'<span style="color:#155724">已转化</span>':'<span style="color:#856404">转化中</span>'; h+='<tr><td>'+d.date+'</td><td>'+diff+'天前</td><td style="color:#e74c3c;font-weight:600">'+fmt(d.leads)+'</td><td style="color:#2ecc71">'+fmt(d.addwx)+'</td>'+(showUV?'<td>'+fmt(d.uv)+'</td>':'')+'<td style="color:#e67e22;font-weight:600">¥'+d.order.toFixed(2)+'</td><td>¥'+cum.toFixed(2)+'</td><td>'+st+'</td></tr>'; }});
  h += '<tr class="total-row"><td>总计</td><td></td><td>'+fmt(tL)+'</td><td>'+fmt(tA)+'</td>'+(showUV?'<td>'+fmt(tU)+'</td>':'')+'<td>¥'+tO.toFixed(2)+'</td><td></td><td></td></tr>';
  h += '</tbody></table></div>';
  openModal('🏷️ ' + sku + ' · 日量级 & GMV 贡献', h);
}}
function sc(l,v,c) {{ return '<div style="background:#f8f9ff;border-radius:8px;padding:10px;text-align:center;border:1px solid #e0e0ff"><div style="font-size:11px;color:#888">'+l+'</div><div style="font-size:18px;font-weight:700;color:'+c+'">'+v+'</div></div>'; }}

function toggleFreeDetail(pk, rowEl) {{
  const dr = document.getElementById('free-detail-'+CURRENT_MONTH+'-'+pk), c = document.getElementById('free-content-'+CURRENT_MONTH+'-'+pk);
  if (dr.style.display === 'none') {{ rowEl.classList.add('expanded'); dr.style.display=''; if(!c.innerHTML) c.innerHTML=renderFreeDetail(pk); }}
  else {{ rowEl.classList.remove('expanded'); dr.style.display='none'; }}
}}
function renderFreeDetail(pk) {{
  const od = ALL_DATA.free[pk]; if(!od) return '<p>无数据</p>'; const t = od.totals;
  let h = '<div class="detail-tabs"><div class="detail-tab active" onclick="switchTab(this,\\'daily\\')">📅 分日数据('+od.daily.length+'天) · 点击查看达人</div><div class="detail-tab" onclick="switchTab(this,\\'sku\\')">🏷️ 达人标签('+od.sku.length+'个) · 点击查看日量级</div></div>';
  h += '<div class="detail-pane active" data-pane="daily"><div class="detail-table"><table><thead><tr><th>日期</th><th>leads</th><th>加微</th><th>UV</th><th>成交金额</th><th>操作</th></tr></thead><tbody>';
  od.daily.forEach(d=>{{ h+='<tr class="clickable" onclick="showDateDetail(\\''+d.date+'\\',\\''+pk+'\\')"><td style="font-weight:600">'+d.date+'</td><td style="color:#e74c3c;font-weight:600">'+fmt(d.leads)+'</td><td style="color:#2ecc71">'+fmt(d.addwx)+'</td><td>'+fmt(d.uv)+'</td><td style="color:#e67e22">¥'+d.order.toFixed(2)+'</td><td><span style="color:#4472C4;font-size:11px">达人→</span></td></tr>'; }});
  h += '<tr class="total-row"><td>总计</td><td>'+fmt(t.leads)+'</td><td>'+fmt(t.addwx)+'</td><td>'+fmt(t.uv)+'</td><td>¥'+t.order.toFixed(2)+'</td><td></td></tr></tbody></table></div></div>';
  h += '<div class="detail-pane" data-pane="sku"><div class="detail-table" style="max-height:400px"><table><thead><tr><th>排名</th><th>达人</th><th>leads</th><th>加微</th><th>UV</th><th>成交</th><th>操作</th></tr></thead><tbody>';
  od.sku.forEach((s,i)=>{{ h+='<tr class="clickable" onclick="showSkuDetail(\\''+s.label+'\\',\\''+pk+'\\')"><td>'+(i+1)+'</td><td style="text-align:left;font-weight:600;color:#4472C4">'+s.label+'</td><td style="color:#e74c3c;font-weight:600">'+fmt(s.leads)+'</td><td style="color:#2ecc71">'+fmt(s.addwx)+'</td><td>'+fmt(s.uv)+'</td><td style="color:#e67e22">¥'+s.order.toFixed(2)+'</td><td><span style="color:#4472C4;font-size:11px">日量→</span></td></tr>'; }});
  h += '</tbody></table></div></div>';
  return h;
}}
function switchTab(tabEl, pn) {{ const c=tabEl.parentElement.parentElement; c.querySelectorAll('.detail-tab').forEach(t=>t.classList.remove('active')); tabEl.classList.add('active'); c.querySelectorAll('.detail-pane').forEach(p=>p.classList.remove('active')); c.querySelector('[data-pane="'+pn+'"]').classList.add('active'); }}

function sortTable(th) {{
  const table = th.closest('table');
  const tbody = table.querySelector('tbody');
  const theadRow = th.closest('tr');
  const ths = theadRow.querySelectorAll('th');
  const colIdx = Array.from(ths).indexOf(th);
  const sortType = th.dataset.sortType || 'string';
  const isAsc = th.classList.contains('sort-asc');
  const dir = isAsc ? -1 : 1;
  theadRow.querySelectorAll('th').forEach(t => {{ t.classList.remove('sort-asc','sort-desc'); }});
  th.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
  const allRows = Array.from(tbody.children);
  const totalRows = allRows.filter(r => r.classList.contains('total-row'));
  const nonTotalRows = allRows.filter(r => !r.classList.contains('total-row'));
  const units = [];
  for (let i = 0; i < nonTotalRows.length; i++) {{
    const row = nonTotalRows[i];
    if (row.classList.contains('detail-row')) {{
      if (units.length > 0) units[units.length-1].detailRow = row;
    }} else {{
      units.push({{ row: row, detailRow: null }});
    }}
  }}
  units.sort((a, b) => {{
    const cA = a.row.children[colIdx], cB = b.row.children[colIdx];
    let vA, vB;
    if (sortType === 'number') {{
      vA = parseFloat((cA.textContent||'').replace(/[¥,%\\s]/g,'')) || 0;
      vB = parseFloat((cB.textContent||'').replace(/[¥,%\\s]/g,'')) || 0;
    }} else if (sortType === 'date') {{
      vA = new Date(cA.textContent.trim()); vB = new Date(cB.textContent.trim());
    }} else {{
      vA = (cA.textContent||'').trim(); vB = (cB.textContent||'').trim();
    }}
    if (vA < vB) return -1*dir;
    if (vA > vB) return 1*dir;
    return 0;
  }});
  nonTotalRows.forEach(r => r.remove());
  const ref = totalRows.length > 0 ? totalRows[0] : null;
  units.forEach(u => {{ tbody.insertBefore(u.row, ref); if (u.detailRow) tbody.insertBefore(u.detailRow, ref); }});
  const firstTh = ths[0];
  if (firstTh && firstTh.dataset.sortType === 'rank') {{
    let rank = 1;
    units.forEach(u => {{ const rc = u.row.children[0]; if (rc) rc.textContent = rank++; }});
  }}
}}
"""

    # Chart JS (after CDN)
    js_charts = """
try {
  const chartOpts = function(daily, section) {
    return {
      type: 'line',
      data: { labels: daily.map(d=>d.date), datasets: [
        { label:'leads数', data:daily.map(d=>d.leads), borderColor:'#e74c3c', backgroundColor:'rgba(231,76,60,0.1)', tension:0.3, pointRadius:5, pointHoverRadius:8 },
        { label:'加微数', data:daily.map(d=>d.addwx), borderColor:'#2ecc71', backgroundColor:'rgba(46,204,113,0.1)', tension:0.3, pointRadius:5, pointHoverRadius:8 },
        { label:'成交金额', data:daily.map(d=>d.order), borderColor:'#e67e22', backgroundColor:'rgba(230,126,34,0.1)', tension:0.3, pointRadius:5, pointHoverRadius:8, yAxisID:'y1' }
      ]},
      options: { responsive:true, maintainAspectRatio:false, onClick:(e,el)=>{ if(el.length>0) showDateDetail(daily[el[0].index].date,section); }, onHover:(e,el)=>{ e.native.target.style.cursor=el.length>0?'pointer':'default'; }, plugins:{ legend:{position:'top',labels:{font:{size:11}}}, tooltip:{callbacks:{afterLabel:()=>'点击查看达人来源'}}}, scales:{ x:{ticks:{font:{size:9},maxRotation:45}}, y:{type:'linear',position:'left',title:{display:true,text:'人数',font:{size:10}}}, y1:{type:'linear',position:'right',title:{display:true,text:'金额¥',font:{size:10}},grid:{drawOnChartArea:false}}}}
    };
  };

  function getDailyForCat(sectionId) {
    const mData = ALL_MONTHS[CURRENT_MONTH];
    if (!mData) return [];
    if (CURRENT_CAT === 'all') {
      return sectionId === 'hc' ? (mData.chart_data.hc_daily||[]) : (mData.chart_data.pn_daily||[]);
    }
    const catData = mData[sectionId] && mData[sectionId].cat && mData[sectionId].cat[CURRENT_CAT];
    return catData ? catData.daily : [];
  }

  function renderCharts(monthKey) {
    Object.values(CHART_INSTANCES).forEach(c => { if (c) c.destroy(); });
    CHART_INSTANCES = {};
    const hcCanvas = document.getElementById('hcDailyChart-'+monthKey);
    const hcDaily = getDailyForCat('hc');
    if (hcCanvas && hcDaily.length > 0) {
      CHART_INSTANCES.hc = new Chart(hcCanvas, chartOpts(hcDaily, 'hc'));
    }
    const pnCanvas = document.getElementById('pianoDailyChart-'+monthKey);
    const pnDaily = getDailyForCat('piano');
    if (pnCanvas && pnDaily.length > 0) {
      CHART_INSTANCES.piano = new Chart(pnCanvas, chartOpts(pnDaily, 'piano'));
    }
  }

  initChartsFn = function(monthKey) { renderCharts(monthKey); };
  refreshChartsForCatFn = function() { renderCharts(CURRENT_MONTH); };
  initChartsFn(CURRENT_MONTH);
} catch(e) { console.error('Chart.js init failed:', e); }
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>开开华彩数据看板</title>
<style>
{css}
</style>
</head>
<body>
<div class="container">
<h1>开开华彩数据看板</h1>
<p class="subtitle">数据范围：{months[-1]} ~ {months[0]} ｜ 转化周期{CONVERSION_DAYS}天 ｜ 共 {len(current_md['accounts'])} 个看板</p>

<div class="top-bar">
  <div class="month-filter">{month_buttons}</div>
  <div class="date-filter">
    <select id="dateFilter" onchange="changeDate(this.value)">
      {date_options}
    </select>
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all" onclick="filterData('all',this)">📊 全部</button>
    <button class="filter-btn" data-filter="hc" onclick="filterData('hc',this)">🎬 课包</button>
    <button class="filter-btn" data-filter="piano" onclick="filterData('piano',this)">🎹 钢琴</button>
    <button class="filter-btn" data-filter="free" onclick="filterData('free',this)">🎁 0元</button>
  </div>
  <button class="cat-toggle" id="catToggle" onclick="toggleCatFilter()">🏷️ 品类</button>
  <button class="theme-toggle" onclick="toggleTheme()"></button>
  <div class="cat-filter" id="catFilter"></div>
</div>

{overview_html}

{month_sections}

<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-box">
    <div class="modal-header"><span id="modalTitle"></span><span class="modal-close" onclick="closeModal()">✕</span></div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>
<div class="r-tooltip" id="rTooltip"></div>

<script>
{js_core}
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
{js_charts}
</script>
</body>
</html>"""

    return html


# ========== Main ==========

def generate_push_summary(months, all_months_data):
    """生成微信推送简报内容，写入 push_content.txt"""
    current_month = months[0]
    md = all_months_data[current_month]
    accounts = md["accounts"]

    # 找最新有数据的日期
    all_dates = set()
    for acc in accounts:
        for r in acc["records"]:
            dt = r.get("date", "")
            if dt and dt != "总计":
                all_dates.add(dt)
    latest_date = max(all_dates) if all_dates else TODAY_STR

    # 各看板当日数据 + 按 dataLabel 聚合
    panels = []
    total_leads = 0
    total_addwx = 0
    sku_stats = {}

    for acc in accounts:
        label = acc["label"]
        acc_leads = 0
        acc_addwx = 0
        for r in acc["records"]:
            if r.get("date") == latest_date:
                leads = r.get("leadsCount", 0)
                addwx = r.get("addWx", 0)
                acc_leads += leads
                acc_addwx += addwx
                dl = r.get("dataLabel", "") or "未分类"
                if dl not in sku_stats:
                    sku_stats[dl] = {"leads": 0, "addwx": 0, "panel": label}
                sku_stats[dl]["leads"] += leads
                sku_stats[dl]["addwx"] += addwx
        panels.append({"label": label, "leads": acc_leads, "addwx": acc_addwx})
        total_leads += acc_leads
        total_addwx += acc_addwx

    # 量级 TOP1（按 leads）
    top_sku = None
    if sku_stats:
        top_label = max(sku_stats, key=lambda k: sku_stats[k]["leads"])
        top = sku_stats[top_label]
        if top["leads"] > 0:
            top_sku = {"label": top_label, "panel": top["panel"],
                       "leads": top["leads"], "addwx": top["addwx"]}

    panels.sort(key=lambda x: x["leads"], reverse=True)

    update_time = TODAY.strftime("%Y-%m-%d %H:%M")
    content = f"📅 数据日期：{latest_date[5:]}<br>🕐 更新时间：{update_time}<br><br>"

    if top_sku:
        content += "🏆 量级TOP1<br>"
        content += f"课包/主播：{top_sku['label']}<br>"
        content += f"来源看板：{top_sku['panel']}<br>"
        content += f"leads：{top_sku['leads']} | 加微：{top_sku['addwx']}<br><br>"

    content += "📈 各看板概览<br>"
    for p in panels:
        if p["leads"] > 0 or p["addwx"] > 0:
            content += f"{p['label']}：leads {p['leads']} | 加微 {p['addwx']}<br>"
    content += f"<br>合计：leads {total_leads} | 加微 {total_addwx}<br><br>"
    content += "🔗 <a href=https://kk-dashboard-85x.pages.dev/>查看完整看板</a>"

    push_path = os.path.join(OUTPUT_DIR, "push_content.txt")
    with open(push_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"推送简报已保存: {push_path}")


def main():
    months = get_available_months()
    if not months:
        print("未找到月份数据文件!")
        return

    print(f"=== 生成开开华彩数据看板 ===")
    print(f"可用月份: {', '.join(months)}")

    all_months_data = {}
    for mk in months:
        raw = load_month_data(mk)
        if raw:
            all_months_data[mk] = process_month(raw)
            md = all_months_data[mk]
            hc_alerts = md["hc"]["alerts"]
            pn_alerts = md["piano"]["alerts"]
            print(f"  [{mk}] 处理完成: {len(md['accounts'])} 个看板, 华彩预警{len(hc_alerts)}项, 钢琴预警{len(pn_alerts)}项")

    html = generate_full_html(months, all_months_data)

    html_path = os.path.join(OUTPUT_DIR, "开开华彩数据看板.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n报告已保存: {html_path}")

    # 生成微信推送简报
    generate_push_summary(months, all_months_data)


if __name__ == "__main__":
    main()

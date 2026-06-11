# services/report.py — 岗位报告生成 + 邮件发送
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def generate_report_html(jobs, candidate_name="", scan_date=None):
    """生成岗位匹配报告的 HTML 内容"""
    if scan_date is None:
        scan_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    total = len(jobs)
    avg_score = sum(j.get("score", 0) for j in jobs) / max(total, 1)

    # 按分数降序
    sorted_jobs = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)

    rows = ""
    for i, job in enumerate(sorted_jobs, 1):
        score = job.get("score", 0)
        title = job.get("title", "未知岗位")
        city = job.get("city", "未知")
        salary = job.get("salary_text", "面议")
        reason = job.get("reason", "")[:60]

        badge = ""
        if score >= 80:
            badge = "高匹配"
            color = "#22c55e"
        elif score >= 60:
            badge = "中匹配"
            color = "#eab308"
        else:
            badge = "一般"
            color = "#94a3b8"

        rows += """<tr>
    <td style="text-align:center">%d</td>
    <td><strong>%s</strong></td>
    <td style="text-align:center"><span style="background:%s;color:#fff;padding:2px 8px;border-radius:4px">%s</span></td>
    <td style="text-align:center">%d分</td>
    <td style="text-align:center">%s</td>
    <td style="text-align:center">%s</td>
    <td style="font-size:13px;color:#555">%s</td>
</tr>""" % (i, title, color, badge, score, city, salary, reason)

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>猎头匹配报告</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:900px;margin:0 auto;padding:20px;background:#f8fafc">
    <div style="background:linear-gradient(135deg,#1e293b,#334155);color:#fff;padding:30px;border-radius:12px;margin-bottom:24px">
        <h1 style="margin:0 0 8px">岗位匹配分析报告</h1>
        <p style="margin:0;opacity:0.8;font-size:14px">%s | 生成时间: %s</p>
    </div>

    <div style="display:flex;gap:16px;margin-bottom:24px">
        <div style="flex:1;background:#fff;padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);text-align:center">
            <div style="font-size:32px;font-weight:bold;color:#3b82f6">%d</div>
            <div style="font-size:13px;color:#64748b">匹配岗位数</div>
        </div>
        <div style="flex:1;background:#fff;padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);text-align:center">
            <div style="font-size:32px;font-weight:bold;color:#22c55e">%d</div>
            <div style="font-size:13px;color:#64748b">平均匹配度</div>
        </div>
    </div>

    <div style="background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden">
        <table style="width:100%%;border-collapse:collapse">
            <thead>
                <tr style="background:#f1f5f9">
                    <th style="padding:12px 16px;font-size:13px;color:#475569">#</th>
                    <th style="padding:12px 16px;font-size:13px;color:#475569">岗位名称</th>
                    <th style="padding:12px 16px;font-size:13px;color:#475569">匹配等级</th>
                    <th style="padding:12px 16px;font-size:13px;color:#475569">得分</th>
                    <th style="padding:12px 16px;font-size:13px;color:#475569">城市</th>
                    <th style="padding:12px 16px;font-size:13px;color:#475569">薪资</th>
                    <th style="padding:12px 16px;font-size:13px;color:#475569">猎头点评</th>
                </tr>
            </thead>
            <tbody>
                %s
            </tbody>
        </table>
    </div>

    <div style="text-align:center;margin-top:24px;font-size:12px;color:#94a3b8">
        ZenHunter 猎头助手
    </div>
</body></html>
""" % (candidate_name, scan_date, total, int(avg_score), rows)

    return html


def send_report_via_email(html_content, smtp_config):
    """通过 SMTP 发送报告到指定邮箱"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "ZenHunter 岗位匹配报告 - " + datetime.now().strftime("%Y-%m-%d")
    msg["From"] = smtp_config.get("from_email", "")
    msg["To"] = smtp_config.get("to_email", "")
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        smtp_config.get("host", "smtp.qq.com"),
        int(smtp_config.get("port", 465)),
        context=context
    ) as server:
        server.login(
            smtp_config.get("username", ""),
            smtp_config.get("password", "")
        )
        server.send_message(msg)

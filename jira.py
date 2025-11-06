import time
import requests
import json
import os
import webbrowser
from PyQt5 import QtWidgets, QtGui, QtCore
import sys

# ----------------- تنظیمات -----------------
JIRA_DOMAIN = "xxxxx"
USERNAME = "xxxxxx"
PASSWORD = "xxxxx"
JQL = "assignee = currentUser() ORDER BY updated DESC"
CHECK_INTERVAL = 300  # 5 دقیقه
CACHE_FILE = "issues_cache.json"
# --------------------------------------------


def get_issues():
    url = f"{JIRA_DOMAIN}/rest/api/2/search"
    response = requests.get(
        url,
        params={"jql": JQL, "fields": "summary,status,updated"},
        auth=(USERNAME, PASSWORD)
    )
    if response.status_code != 200:
        return None
    return response.json()["issues"]


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return None   # تغییر مهم: None = اولین اجرا


def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)


class AlertWindow(QtWidgets.QDialog):
    def __init__(self, key, status, summary):
        super().__init__()
        self.setWindowTitle(f"Jira Update: {key}")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setFixedSize(450, 220)

        layout = QtWidgets.QVBoxLayout()

        label_title = QtWidgets.QLabel(f"<b>Issue:</b> {key}")
        label_status = QtWidgets.QLabel(f"<b>Status:</b> {status}")
        label_summary = QtWidgets.QLabel(f"<b>Summary:</b> {summary}")

        label_title.setStyleSheet("font-size: 16px;")
        label_status.setStyleSheet("font-size: 14px; color: #0078d7;")
        label_summary.setStyleSheet("font-size: 13px;")

        layout.addWidget(label_title)
        layout.addWidget(label_status)
        layout.addWidget(label_summary)

        btn = QtWidgets.QPushButton("Open in Browser")
        btn.clicked.connect(lambda: webbrowser.open(f"{JIRA_DOMAIN}/browse/{key}"))
        layout.addWidget(btn)

        self.setLayout(layout)


def show_alert(key, status, summary):
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    window = AlertWindow(key, status, summary)
    window.show()
    app.exec_()


def main():
    print("🚀 Jira Monitor started ...")

    # -------------------------
    last_snapshot = load_cache()
    first_run = last_snapshot is None
    # -------------------------

    if first_run:
        print("✅ First run detected: caching issues, no alerts will show.")
        last_snapshot = {}

    while True:
        try:
            issues = get_issues()
            if issues is None:
                show_alert("Error", "Connection Failed", "Cannot connect to Jira Server")
                time.sleep(CHECK_INTERVAL)
                continue

            current_snapshot = {}

            for issue in issues:
                key = issue['key']
                summary = issue['fields']['summary']
                status = issue['fields']['status']['name']
                updated = issue['fields']['updated']

                current_snapshot[key] = {
                    "status": status,
                    "summary": summary,
                    "updated": updated
                }

                if not first_run:  # ✅ هشدار فقط بعد از اجرای اول
                    if key in last_snapshot:
                        if last_snapshot[key]["updated"] != updated:
                            show_alert(key, status, summary)
                    else:
                        # issue جدید
                        show_alert(key, status, summary)

            save_cache(current_snapshot)
            last_snapshot = current_snapshot

            # پس از اولین حلقه دیگر first_run نیست
            first_run = False

            time.sleep(CHECK_INTERVAL)

        except Exception as ex:
            show_alert("Error", "Script Error", str(ex))
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()


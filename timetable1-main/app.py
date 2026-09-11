import os
import pdfplumber
import pytesseract
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, session
from scheduler import generate_timetable
from flask import Response

import csv
import io

app = Flask(__name__)
app.secret_key = "timetable_secret"

DEFAULT_ID = "Arunai"
DEFAULT_PASS = "12345678"

FREE_SLOTS = ["free", "library", "lib", "seminar"]

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")

        if user_id == DEFAULT_ID and password == DEFAULT_PASS:
            session["user"] = user_id
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid Login ID or Password")

    return render_template("login.html")


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")


# ================= GENERATE =================
@app.route("/generate", methods=["GET", "POST"])
def generate():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        theory_subjects = []
        lab_subjects = []

        num_theory = int(request.form.get("num_theory", 0))
        num_lab = int(request.form.get("num_lab", 0))

        for i in range(num_theory):
            name = request.form.get(f"name_{i}")
            hours = request.form.get(f"hours_{i}")
            if name and hours:
                theory_subjects.append((name.strip(), hours.strip()))

        for i in range(num_lab):
            name = request.form.get(f"lab_name_{i}")
            hours = request.form.get(f"lab_hours_{i}")
            if name and hours:
                lab_subjects.append((name.strip(), hours.strip()))

        timetable = generate_timetable(theory_subjects, lab_subjects)
        session['last_tt'] = timetable

        return render_template("timetable.html", timetable=timetable)

    return render_template("index.html")


# ================= TEXT EXTRACTION =================



def extract_text(file):
    filename = file.filename.lower()

    # ✅ CSV SUPPORT
    if filename.endswith(".csv"):
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        reader = csv.reader(stream)
        lines = []
        for row in reader:
            lines.append(" ".join(row))
        return "\n".join(lines)

    elif filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text

    elif filename.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(file)
        return pytesseract.image_to_string(image)

    elif filename.endswith(".txt"):
        return file.read().decode("utf-8")

    return ""



# ================= TEXT TO DICT =================
def text_to_dict(text):
    timetable = {}

    for line in text.split("\n"):
        parts = line.strip().split()

        if len(parts) >= 3:
            day = parts[0].capitalize()
            period = parts[1].upper()
            subject = " ".join(parts[2:]).strip().lower()

            timetable.setdefault(day, {})
            timetable[day][period] = subject

    return timetable


# ================= CLASH PAGE =================
@app.route("/clash")
def clash():
    return render_template("clash.html")


# ================= CHECK CLASH =================

@app.route("/check_clash", methods=["POST"])
def check_clash():

    tt1_file = request.files.get("tt1_file")
    tt2_file = request.files.get("tt2_file")

    code1 = request.form.get("code1").lower().strip()
    code2 = request.form.get("code2").lower().strip()

    # Load timetables
    if tt1_file.filename.endswith(".csv"):
        tt1 = csv_to_dict(tt1_file)
    else:
        text1 = extract_text(tt1_file)
        tt1 = text_to_dict(text1)

    if tt2_file.filename.endswith(".csv"):
        tt2 = csv_to_dict(tt2_file)
    else:
        text2 = extract_text(tt2_file)
        tt2 = text_to_dict(text2)

    PERIODS = ["P1","P2","P3","P4","P5","P6","P7"]

    clash_list = []
    resolution = []

    for day in tt1:
        for p in PERIODS:

            sub1 = tt1.get(day, {}).get(p, "").lower()
            sub2 = tt2.get(day, {}).get(p, "").lower()

            # 🎯 CHECK USING SUBJECT CODES
            if code1 in sub1 and code2 in sub2:
                clash_list.append(f"{day} {p}")

                # 🔄 AUTO SHIFT TT2 SUBJECT
                for new_p in PERIODS:
                    if tt2[day].get(new_p, "") == "" and tt1[day].get(new_p, "") == "":
                        tt2[day][new_p] = sub2
                        tt2[day][p] = "Free"

                        resolution.append(
                            f"{day} {p} → moved to {new_p}"
                        )
                        break

    # ✅ RESULT
    if clash_list:
        message = "⚠️ Staff Clash Detected & Fixed"
    else:
        message = "✅ No Clash Found"

    return render_template(
        "clash.html",
        message=message,
        clashes=clash_list,
        resolution=resolution,
        timetable1=tt1,
        timetable2=tt2
    )


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))




# ✅ PASTE CSV CODE HERE
@app.route("/download_csv")
def download_csv():
    timetable = session.get("last_tt")

    if not timetable:
        return "No timetable found!"

    def generate():
        output = []

        header = ["Day", "P1", "P2", "Break", "P3", "P4", "Lunch", "P5", "P6", "P7"]
        output.append(",".join(header))

        for day, periods in timetable.items():
            row = [
                day,
                periods.get("P1", ""),
                periods.get("P2", ""),
                "Break",
                periods.get("P3", ""),
                periods.get("P4", ""),
                "Lunch",
                periods.get("P5", ""),
                periods.get("P6", ""),
                periods.get("P7", "")
            ]
            output.append(",".join(row))

        return "\n".join(output)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=timetable.csv"}
    )


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
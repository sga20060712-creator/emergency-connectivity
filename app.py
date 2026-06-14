from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = "quick_rescue_secret_key"
DB = "hospital.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS services(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT NOT NULL,
        item TEXT NOT NULL,
        location TEXT,
        quantity INTEGER DEFAULT 0,
        status TEXT,
        contact TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        module TEXT,
        item TEXT,
        patient TEXT,
        phone TEXT,
        address TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # default users
    cur.execute("SELECT id FROM users WHERE email=?", ("admin@gmail.com",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,?)",
                    ("Admin", "admin@gmail.com", "9999999999", "admin123", "admin"))

    cur.execute("SELECT id FROM users WHERE email=?", ("user@gmail.com",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,?)",
                    ("User", "user@gmail.com", "8888888888", "user123", "user"))

    # sample services
    count = cur.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    if count == 0:
        services = [
            ("Blood", "A+ Blood", "Central Medical Hub", 18, "Available", "9876543210"),
            ("Blood", "O- Blood", "Metro Red Cross", 2, "Critical", "9876543211"),
            ("Blood", "B+ Blood", "City General Hospital", 32, "Available", "9876543212"),
            ("Blood", "AB- Blood", "Royal Heart Institute", 0, "Out of Stock", "9876543213"),

            ("Oxygen", "Liquid Medical Oxygen", "City Medical Center", 45, "Available", "9876543214"),
            ("Oxygen", "B-Type Cylinder", "St. Jude Trauma Care", 12, "Low Stock", "9876543215"),
            ("Oxygen", "Oxygen Concentrator", "Metro General Hospital", 0, "Out of Stock", "9876543216"),
            ("Oxygen", "D-Type Cylinder", "Apex Heart Institute", 31, "Available", "9876543217"),

            ("Ambulance", "Cardiac Ambulance", "Central Hub", 5, "Available", "9876543218"),
            ("Ambulance", "Trauma Ambulance", "West Freeway", 3, "Available", "9876543219"),
            ("Ambulance", "Air Ambulance", "North Terrace", 1, "Available", "9876543220"),

            ("Organs", "Kidney", "St. Mary Renal Center", 2, "Available", "9876543221"),
            ("Organs", "Liver", "Apex Liver Institute", 1, "Available", "9876543222"),
            ("Organs", "Heart", "City Trauma Center", 1, "Urgent", "9876543223"),

            ("ICU", "Ventilator", "City Medical Center", 8, "Available", "9876543224"),
            ("ICU", "Dialysis Machine", "Metro Nephro Center", 5, "Available", "9876543225"),
            ("ICU", "Defibrillator", "Apex Heart Institute", 1, "Critical", "9876543226"),
            ("ICU", "Crash Cart", "Emergency Block", 4, "Available", "9876543227"),
        ]
        cur.executemany("INSERT INTO services(module,item,location,quantity,status,contact) VALUES(?,?,?,?,?,?)", services)

    conn.commit()
    conn.close()


init_db()


# ---------------- AUTH ----------------
@app.route("/")
def home():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=? AND password=? AND role='user'",
                        (email, password)).fetchone()
    conn.close()

    if user:
        session.clear()
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = "user"
        return redirect("/dashboard")
    return render_template("login.html", error="Invalid user email or password")


@app.route("/admin_login", methods=["POST"])
def admin_login():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    admin = conn.execute("SELECT * FROM users WHERE email=? AND password=? AND role='admin'",
                         (email, password)).fetchone()
    conn.close()

    if admin:
        session.clear()
        session["admin_id"] = admin["id"]
        session["name"] = admin["name"]
        session["role"] = "admin"
        return redirect("/admin/dashboard")
    return render_template("login.html", error="Invalid admin email or password")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        try:
            conn = get_db()
            conn.execute("INSERT INTO users(name,email,phone,password,role) VALUES(?,?,?,?,?)",
                         (name, email, phone, password, "user"))
            conn.commit()
            conn.close()
            return redirect("/")
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Email already exists")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- USER PAGES ----------------
def user_required():
    return session.get("role") == "user"


@app.route("/dashboard")
def dashboard():
    if not user_required():
        return redirect("/")

    conn = get_db()
    data = {
        "blood": conn.execute("SELECT COUNT(*) FROM services WHERE module='Blood'").fetchone()[0],
        "oxygen": conn.execute("SELECT COUNT(*) FROM services WHERE module='Oxygen'").fetchone()[0],
        "ambulance": conn.execute("SELECT COUNT(*) FROM services WHERE module='Ambulance'").fetchone()[0],
        "organs": conn.execute("SELECT COUNT(*) FROM services WHERE module='Organs'").fetchone()[0],
        "icu": conn.execute("SELECT COUNT(*) FROM services WHERE module='ICU'").fetchone()[0],
        "requests": conn.execute("SELECT COUNT(*) FROM requests WHERE user_id=?", (session["user_id"],)).fetchone()[0],
    }
    conn.close()
    return render_template("dashboard.html", **data)


def service_page(module):
    if not user_required():
        return redirect("/")
    conn = get_db()
    services = conn.execute("SELECT * FROM services WHERE module=? ORDER BY id DESC", (module,)).fetchall()
    conn.close()
    return render_template("services.html", services=services, module=module)


@app.route("/blood")
@app.route("/blood.html")
def blood():
    return service_page("Blood")


@app.route("/oxygen")
@app.route("/oxygen.html")
def oxygen():
    return service_page("Oxygen")


@app.route("/ambulance")
@app.route("/ambulence")
@app.route("/ambulence.html")
def ambulance():
    return service_page("Ambulance")


@app.route("/organs")
@app.route("/organs.html")
def organs():
    return service_page("Organs")


@app.route("/icu")
@app.route("/icv")
@app.route("/icv.html")
def icu():
    return service_page("ICU")


@app.route("/request_service", methods=["POST"])
def request_service():
    if not user_required():
        return redirect("/")

    conn = get_db()
    conn.execute("""
        INSERT INTO requests(user_id,module,item,patient,phone,address,status,created_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (
        session["user_id"],
        request.form.get("module"),
        request.form.get("item"),
        request.form.get("patient"),
        request.form.get("phone"),
        request.form.get("address"),
        "Pending",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()
    return redirect("/my_requests")


@app.route("/my_requests")
def my_requests():
    if not user_required():
        return redirect("/")
    conn = get_db()
    requests = conn.execute("SELECT * FROM requests WHERE user_id=? ORDER BY id DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("my_requests.html", requests=requests)


@app.route("/contact")
@app.route("/contact.html")
def contact():
    if not user_required():
        return redirect("/")
    return render_template("contact.html")


# ---------------- ADMIN PAGES ----------------
def admin_required():
    return session.get("role") == "admin"


@app.route("/admin")
def admin_home():
    return redirect("/admin/dashboard")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not admin_required():
        return redirect("/")
    conn = get_db()
    data = {
        "users": conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        "services": conn.execute("SELECT COUNT(*) FROM services").fetchone()[0],
        "pending": conn.execute("SELECT COUNT(*) FROM requests WHERE status='Pending'").fetchone()[0],
        "total_requests": conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
    }
    conn.close()
    return render_template("admin_dashboard.html", **data)


@app.route("/admin/services")
def admin_services():
    if not admin_required():
        return redirect("/")
    conn = get_db()
    services = conn.execute("SELECT * FROM services ORDER BY module, id DESC").fetchall()
    conn.close()
    return render_template("admin_services.html", services=services)


@app.route("/admin/add_service", methods=["POST"])
def add_service():
    if not admin_required():
        return redirect("/")
    conn = get_db()
    conn.execute("INSERT INTO services(module,item,location,quantity,status,contact) VALUES(?,?,?,?,?,?)", (
        request.form.get("module"),
        request.form.get("item"),
        request.form.get("location"),
        request.form.get("quantity"),
        request.form.get("status"),
        request.form.get("contact"),
    ))
    conn.commit()
    conn.close()
    return redirect("/admin/services")


@app.route("/admin/delete_service/<int:id>")
def delete_service(id):
    if not admin_required():
        return redirect("/")
    conn = get_db()
    conn.execute("DELETE FROM services WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/services")


@app.route("/admin/requests")
def admin_requests():
    if not admin_required():
        return redirect("/")
    conn = get_db()
    rows = conn.execute("""
        SELECT requests.*, users.name AS username
        FROM requests
        LEFT JOIN users ON users.id = requests.user_id
        ORDER BY requests.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_requests.html", requests=rows)


@app.route("/admin/update_request/<int:id>/<status>")
def update_request(id, status):
    if not admin_required():
        return redirect("/")
    allowed = ["Pending", "Approved", "Rejected", "Completed", "Success"]
    if status not in allowed:
        return "Invalid status"
    conn = get_db()
    conn.execute("UPDATE requests SET status=? WHERE id=?", (status, id))
    conn.commit()
    conn.close()
    return redirect("/admin/requests")


@app.route("/admin/users")
def admin_users():
    if not admin_required():
        return redirect("/")
    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE role='user' ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


@app.route("/admin/delete_user/<int:id>")
def delete_user(id):
    if not admin_required():
        return redirect("/")
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=? AND role='user'", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/users")


# ---------------- OTP DEMO ----------------
otp_store = {}

@app.route("/send_otp", methods=["POST"])
def send_otp():
    phone = request.form.get("phone")
    otp = str(random.randint(1000, 9999))
    otp_store[phone] = otp
    return {"otp": otp, "message": "OTP generated successfully"}


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    phone = request.form.get("phone")
    otp = request.form.get("otp")
    if otp_store.get(phone) == otp:
        return {"status": "success", "message": "OTP verified"}
    return {"status": "failed", "message": "Invalid OTP"}


if __name__ == "__main__":
    app.run(debug=True)

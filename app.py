from flask import Flask, render_template, request, redirect,session
import psycopg2
import os

app = Flask(__name__)
app.secret_key="campusshare_secret_key"


# =========================
# DATABASE CONNECTION
# =========================

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require"
    )

# =========================
# WELCOME PAGE
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# LOGIN PAGE
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users
            (full_name, username, email, password)
            VALUES (%s, %s, %s, %s)
        """, (full_name, username, email, password))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("register.html")
# =========================
# LOGIN PAGE
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, password, is_blocked
            FROM users
            WHERE username = %s OR email = %s
        """, (username, username))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user is None:
            return "<script>alert('Username or Email not found'); window.location.href='/login';</script>"

        if user[3]:
            return "<script>alert('Your account is blocked. Contact the administrator.'); window.location.href='/login';</script>"

        if user[2] != password:
            return "<script>alert('Incorrect password'); window.location.href='/login';</script>"

        session["user_id"] = user[0]
        session["username"] = user[1]

        return redirect("/personal-info")

    return render_template("login.html")
# =========================
# PERSONAL INFORMATION
# =========================

# =========================
# PERSONAL INFORMATION
# =========================

@app.route("/personal-info", methods=["GET", "POST"])
def personal_info():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        full_name = request.form["full_name"]
        city = request.form["city"]
        course = request.form["course"]
        year = request.form["year"]
        contact = request.form["contact"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET full_name = %s,
                city = %s,
                course = %s,
                year = %s,
                contact = %s
            WHERE id = %s
        """, (
            full_name,
            city,
            course,
            year,
            contact,
            session["user_id"]
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/dashboard")

    return render_template(
        "personal_info.html",
        username=session["username"]
    )


# =========================
# PREFERENCES
# =========================

@app.route("/preferences")
def preferences():
    return render_template("preferences.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM items ORDER BY id DESC")
    items = cur.fetchall()

    cur.execute("""
        SELECT score
        FROM trust_scores
        WHERE user_id = %s
    """, (session["user_id"],))

    trust = cur.fetchone()

    if trust:
        trust_score = trust[0]
    else:
        trust_score = 50

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        items=items,
        trust_score=trust_score
    )
@app.route("/need-it-now", methods=["GET", "POST"])
def need_it_now():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":

        item_name = request.form["item_name"]
        category = request.form["category"]
        department = request.form["department"]
        description = request.form["description"]

        cur.execute("""
            INSERT INTO item_needs
            (user_id, item_name, category, department, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            item_name,
            category,
            department,
            description
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/need-it-now")

    cur.execute("""
        SELECT
            n.id,
            n.item_name,
            n.category,
            n.department,
            n.description,
            u.username
        FROM item_needs n
        JOIN users u ON n.user_id = u.id
        ORDER BY n.id DESC
    """)

    needs = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "need_it_now.html",
        needs=needs
    )
@app.route("/help-need/<int:need_id>", methods=["POST"])
def help_need(need_id):

    if "user_id" not in session:
        return redirect("/login")

    message = request.form["message"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO need_help
        (need_id, helper_id, message)
        VALUES (%s, %s, %s)
    """, (
        need_id,
        session["user_id"],
        message
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/need-it-now")
@app.route("/help-responses")
def help_responses():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            nh.id,
            n.item_name,
            nh.message,
            u.username,
            nh.created_at
        FROM need_help nh
        JOIN item_needs n
            ON nh.need_id = n.id
        JOIN users u
            ON nh.helper_id = u.id
        WHERE n.user_id = %s
        ORDER BY nh.id DESC
    """, (session["user_id"],))

    responses = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "help_responses.html",
        responses=responses
    )
@app.route("/admin")
def admin_panel():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT role FROM users WHERE id = %s",
        (session["user_id"],)
    )
    admin = cur.fetchone()

    if not admin or admin[0] != "admin":
        cur.close()
        conn.close()
        return "Access denied: Admin only", 403

    cur.execute("""
        SELECT id, username, email, role, is_blocked
        FROM users
        ORDER BY id DESC
    """)
    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin.html", users=users)
# =========================
# ADD ITEM
# =========================

@app.route("/add-item", methods=["GET", "POST"])
def add_item():
    if "user_id" not in session:
        return redirect("/login")
    if request.method == "POST":

        item_name = request.form["item_name"]
        category = request.form["category"]
        department = request.form["department"]
        condition = request.form["condition"]
        availability = request.form["availability"]
        description = request.form["description"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO items
            (owner_id, item_name, category, department,
             description, condition, availability)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            item_name,
            category,
            department,
            description,
            condition,
            availability
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_item.html")


# =========================
# MY ITEMS
# =========================

@app.route("/my-items")
def my_items():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM items WHERE owner_id = %s ORDER BY id DESC""",(session["user_id"],))
    items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("my_items.html", items=items)


# =========================
# ITEM DETAILS
# =========================

@app.route("/item/<int:item_id>")
def item_details(item_id):

    conn = get_db_connection()
    cur = conn.cursor()

    # Get item
    cur.execute(
        "SELECT * FROM items WHERE id = %s",
        (item_id,)
    )

    item = cur.fetchone()

    if item is None:
        cur.close()
        conn.close()
        return "Item not found", 404

    # Get reviews for this item
    cur.execute("""
        SELECT
            r.rating,
            r.review,
            r.created_at,
            u.username
        FROM ratings r
        JOIN users u
            ON r.reviewer_id = u.id
        JOIN borrow_requests br
            ON r.request_id = br.id
        WHERE br.item_id = %s
        ORDER BY r.created_at DESC
    """, (item_id,))

    reviews = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "item_details.html",
        item=item,
        reviews=reviews
    )


# =========================
# BORROW REQUEST
# =========================
@app.route("/request-borrow/<int:item_id>", methods=["POST"])
def request_borrow(item_id):

    return_date = request.form["return_date"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Check item availability
    cur.execute(
        "SELECT availability FROM items WHERE id = %s",
        (item_id,)
    )

    item = cur.fetchone()

    if item is None:
        cur.close()
        conn.close()
        return "Item not found", 404

    if item[0] != "Available":
        cur.close()
        conn.close()
        return "This item is currently unavailable."

    # Current test user
    # Later this will come from login/session
    borrower_id = session["user_id"]

    cur.execute("""
        INSERT INTO borrow_requests
        (item_id, borrower_id, status, return_date)
        VALUES (%s, %s, %s, %s)
    """, (
        item_id,
        borrower_id,
        "Pending",
        return_date
    ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/dashboard")


# =========================
# ITEMS TEST ROUTE
# =========================

@app.route("/items")
def items():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM items")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return str(data)


# =========================
# RUN APPLICATION
# =========================

@app.route("/my-requests")
def my_requests():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            br.id,
            i.item_name,
            i.category,
            i.department,
            br.status,
            br.return_date
        FROM borrow_requests br
        JOIN items i
        ON br.item_id = i.id
        WHERE br.borrower_id = %s
        ORDER BY br.id DESC
    """,(session["user_id"],))

    requests = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("my_requests.html", requests=requests)
@app.route("/owner-requests")
def owner_requests():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            br.id,
            i.item_name,
            u.username,
            i.category,
            i.department,
            br.status,
            br.return_date
        FROM borrow_requests br
        JOIN items i
            ON br.item_id = i.id
        JOIN users u
            ON br.borrower_id = u.id
        WHERE i.owner_id = %s
        ORDER BY br.id DESC
    """,(session["user_id"],))

    requests = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "owner_requests.html",
        requests=requests
    )
@app.route("/accept-request/<int:request_id>",methods=["POST"])
def accept_request(request_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE borrow_requests
        SET status = 'Accepted'
        WHERE id = %s
    """, (request_id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/owner-requests")
@app.route("/reject-request/<int:request_id>", methods=["POST"])
def reject_request(request_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE borrow_requests
        SET status = 'Rejected'
        WHERE id = %s
    """, (request_id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/owner-requests")
@app.route("/return-item/<int:request_id>", methods=["GET", "POST"])
def return_item(request_id):

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "GET":

        cur.execute("""
            SELECT i.*
            FROM borrow_requests br
            JOIN items i ON br.item_id = i.id
            WHERE br.id = %s
        """, (request_id,))

        item = cur.fetchone()

        cur.close()
        conn.close()

        if item is None:
            return "Request not found", 404

        return render_template(
            "return_item.html",
            item=item,
            request_id=request_id
        )

    # POST = confirm return

    cur.execute("""
        UPDATE borrow_requests
        SET status = 'Returned'
        WHERE id = %s
    """, (request_id,))

    cur.execute("""
        UPDATE items
        SET availability = 'Available'
        WHERE id = (
            SELECT item_id
            FROM borrow_requests
            WHERE id = %s
        )
    """, (request_id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/my-requests")
@app.route("/rate/<int:request_id>")
def rate_item(request_id):
    return render_template(
        "rating.html",
        request_id=request_id
    )
@app.route("/submit-rating/<int:request_id>", methods=["POST"])
def submit_rating(request_id):

    rating = int(request.form["rating"])
    review = request.form["review"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Save rating
    cur.execute("""
        INSERT INTO ratings
        (request_id, reviewer_id, rating, review)
        VALUES (%s, %s, %s, %s)
    """, (
        request_id,
        session["user_id"],
        rating,
        review
    ))

    # Find item owner
    cur.execute("""
        SELECT i.owner_id
        FROM borrow_requests br
        JOIN items i ON br.item_id = i.id
        WHERE br.id = %s
    """, (request_id,))

    owner = cur.fetchone()

    if owner:
        owner_id = owner[0]

        # Calculate owner's average rating
        cur.execute("""
            SELECT AVG(r.rating)
            FROM ratings r
            JOIN borrow_requests br
                ON r.request_id = br.id
            JOIN items i
                ON br.item_id = i.id
            WHERE i.owner_id = %s
        """, (owner_id,))

        average = cur.fetchone()[0]

        if average is not None:
            trust_score = round(float(average) * 20)

            # Create or update Trust Score
            cur.execute("""
                INSERT INTO trust_scores (user_id, score)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    score = EXCLUDED.score,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                owner_id,
                trust_score
            ))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/my-requests")
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/admin/toggle-block/<int:user_id>", methods=["POST"])
def toggle_block(user_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check current user's admin role
        cur.execute(
            "SELECT role FROM users WHERE id = %s",
            (session["user_id"],)
        )
        admin = cur.fetchone()

        if not admin or admin[0] != "admin":
            conn.rollback()
            return "Access denied", 403

        # Prevent changing own account
        if user_id == session["user_id"]:
            conn.rollback()
            return "You cannot block your own account", 400

        # Get target user's current status
        cur.execute(
            "SELECT role, is_blocked FROM users WHERE id = %s",
            (user_id,)
        )
        target = cur.fetchone()

        if not target:
            conn.rollback()
            return "User not found", 404

        # Never block or unblock another admin here
        if target[0] == "admin":
            conn.rollback()
            return "Admin accounts cannot be blocked here", 400

        # If currently active, block and delete only their items
        if not target[1]:
            cur.execute(
                "DELETE FROM items WHERE owner_id = %s",
                (user_id,)
            )
            cur.execute(
                "UPDATE users SET is_blocked = TRUE WHERE id = %s",
                (user_id,)
            )
        else:
            # Unblock only; do not delete anything
            cur.execute(
                "UPDATE users SET is_blocked = FALSE WHERE id = %s",
                (user_id,)
            )

        conn.commit()
        return redirect("/admin")

    except Exception:
        conn.rollback()
        app.logger.exception("Failed to change user block status")
        return "Could not update account. Please check application logs.", 500

    finally:
        cur.close()
        conn.close()
if __name__ == "__main__":
    app.run(debug=True)
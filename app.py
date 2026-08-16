
from flask import Flask, render_template, request, redirect, url_for, session
from database import init_db, get_db_connection
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = "lost-found-secret-key"


# =========================================================
# IMAGE UPLOAD SETTINGS
# =========================================================

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE INITIALIZE
# =========================================================

init_db()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")

# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # =====================================================
        # GET FORM DATA
        # =====================================================

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # =====================================================
        # BASIC VALIDATION
        # =====================================================

        if not name:

            return "Full name is required!"

        if not email:

            return "Email is required!"

        if not phone:

            return "Phone number is required!"

        if not password:

            return "Password is required!"


        # =====================================================
        # PHONE VALIDATION
        # =====================================================

        if not phone.isdigit():

            return "Phone number must contain only digits!"

        if len(phone) != 10:

            return "Phone number must contain exactly 10 digits!"


        # =====================================================
        # PASSWORD VALIDATION
        # =====================================================

        if len(password) < 6:

            return "Password must contain at least 6 characters!"


        # =====================================================
        # PROFILE PHOTO
        # =====================================================

        profile_photo = request.files.get(
            "profile_photo"
        )

        if not profile_photo:

            return "Please select a profile photo!"

        if not profile_photo.filename:

            return "Please select a profile photo!"


        # =====================================================
        # CHECK PHOTO FORMAT
        # =====================================================

        if not allowed_file(
            profile_photo.filename
        ):

            return (
                "Invalid profile photo format! "
                "Only PNG, JPG, JPEG and WEBP are allowed."
            )


        # =====================================================
        # DATABASE CONNECTION
        # =====================================================

        connection = get_db_connection()


        # =====================================================
        # CHECK EMAIL
        # =====================================================

        existing_email = connection.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        if existing_email:

            connection.close()

            return "Email already registered!"


        # =====================================================
        # CHECK PHONE
        # =====================================================

        existing_phone = connection.execute(
            """
            SELECT id
            FROM users
            WHERE phone = ?
            """,
            (phone,)
        ).fetchone()

        if existing_phone:

            connection.close()

            return "Phone number already registered!"


        # =====================================================
        # SAVE PROFILE PHOTO
        # =====================================================

        original_name = secure_filename(
            profile_photo.filename
        )

        extension = os.path.splitext(
            original_name
        )[1].lower()

        profile_filename = (
            "profile_"
            + uuid.uuid4().hex
            + extension
        )

        profile_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            profile_filename
        )

        profile_photo.save(
            profile_path
        )


        # =====================================================
        # HASH PASSWORD
        # =====================================================

        hashed_password = generate_password_hash(
            password
        )


        # =====================================================
        # INSERT USER
        # =====================================================

        try:

            connection.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    phone,
                    password,
                    profile_photo
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    phone,
                    hashed_password,
                    profile_filename
                )
            )

            connection.commit()

        except Exception as error:

            connection.close()

            # Agar database mein problem aaye,
            # to uploaded photo bhi delete kar do.

            if os.path.exists(profile_path):

                os.remove(profile_path)

            print(
                "Registration Error:",
                error
            )

            return "Account could not be created!"

        connection.close()


        # =====================================================
        # REGISTRATION SUCCESS
        # =====================================================

        return redirect(
            url_for("login")
        )


    # =====================================================
    # SHOW REGISTER PAGE
    # =====================================================

    return render_template(
        "register.html"
    )



# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # =====================================================
        # GET LOGIN DATA
        # =====================================================

        login_value = request.form.get(
            "login",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # =====================================================
        # VALIDATION
        # =====================================================

        if not login_value:

            return "Please enter your email or phone number!"

        if not password:

            return "Please enter your password!"


        # =====================================================
        # DATABASE CONNECTION
        # =====================================================

        connection = get_db_connection()


        # =====================================================
        # FIND USER BY EMAIL OR PHONE
        # =====================================================

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = ?
            OR phone = ?
            """,
            (
                login_value.lower(),
                login_value
            )
        ).fetchone()


        # =====================================================
        # USER NOT FOUND
        # =====================================================

        if not user:

            connection.close()

            return "Invalid email/phone or password!"


        # =====================================================
        # CHECK PASSWORD
        # =====================================================

        stored_password = user["password"]

        password_valid = False


        try:

            password_valid = check_password_hash(
                stored_password,
                password
            )

        except Exception:

            password_valid = False


        # =====================================================
        # OLD PASSWORD SUPPORT
        # =====================================================
        # Agar purane account ka password plain text mein
        # stored tha to usko automatically secure hash mein
        # convert kar denge.

        if not password_valid:

            if stored_password == password:

                password_valid = True

                new_hash = generate_password_hash(
                    password
                )

                connection.execute(
                    """
                    UPDATE users
                    SET password = ?
                    WHERE id = ?
                    """,
                    (
                        new_hash,
                        user["id"]
                    )
                )

                connection.commit()


        # =====================================================
        # LOGIN SUCCESS
        # =====================================================

        if password_valid:

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]

            session["user_phone"] = user["phone"]

            session["profile_photo"] = user["profile_photo"]

            connection.close()

            return redirect(
                url_for("dashboard")
            )


        # =====================================================
        # LOGIN FAILED
        # =====================================================

        connection.close()

        return "Invalid email/phone or password!"


    # =====================================================
    # SHOW LOGIN PAGE
    # =====================================================

    return render_template(
        "login.html"
    )



# =========================================================
# REPORT ITEM
# =========================================================

@app.route("/report", methods=["GET", "POST"])
def report():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        item_type = request.form.get(
            "item_type",
            ""
        ).strip()

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        item_date = request.form.get(
            "item_date",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not item_type:

            return "Please select Lost or Found!"

        if not item_name:

            return "Item name is required!"

        if not category:

            return "Category is required!"

        if not location:

            return "Location is required!"

        if not item_date:

            return "Date is required!"

        if item_type not in ["Lost", "Found"]:

            return "Invalid item type!"

        # =====================================================
        # IMAGE UPLOAD
        # =====================================================

        image = request.files.get("image")

        image_filename = None

        if image and image.filename:

            if not allowed_file(image.filename):

                return (
                    "Invalid image format! "
                    "Only PNG, JPG, JPEG and WEBP are allowed."
                )

            original_name = secure_filename(
                image.filename
            )

            extension = os.path.splitext(
                original_name
            )[1].lower()

            image_filename = (
                uuid.uuid4().hex
                + extension
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_filename
            )

            image.save(image_path)

        # =====================================================
        # SAVE REPORT
        # =====================================================

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO items
            (
                user_id,
                item_type,
                item_name,
                category,
                description,
                location,
                item_date,
                image
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                item_type,
                item_name,
                category,
                description,
                location,
                item_date,
                image_filename
            )
        )

        connection.commit()

        connection.close()

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "report.html"
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    search = request.args.get(
        "search",
        ""
    ).strip()

    item_type = request.args.get(
        "type",
        ""
    ).strip()

    connection = get_db_connection()

    # Lost count
    lost_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM items
        WHERE item_type = 'Lost'
        """
    ).fetchone()[0]

    # Found count
    found_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM items
        WHERE item_type = 'Found'
        """
    ).fetchone()[0]

    # Total count
    total_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM items
        """
    ).fetchone()[0]

    # Recovered count
    recovered_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM items
        WHERE status = 'recovered'
        """
    ).fetchone()[0]

    # =====================================================
    # ITEMS QUERY
    # =====================================================

    query = """
        SELECT *
        FROM items
        WHERE 1=1
    """

    params = []

    if item_type in ["Lost", "Found"]:

        query += """
            AND item_type = ?
        """

        params.append(item_type)

    if search:

        query += """
            AND (
                item_name LIKE ?
                OR category LIKE ?
                OR location LIKE ?
                OR description LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    query += """
        ORDER BY id DESC
        LIMIT 50
    """

    items = connection.execute(
        query,
        params
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        lost_count=lost_count,
        found_count=found_count,
        total_count=total_count,
        recovered_count=recovered_count,
        items=items,
        search=search
    )


# =========================================================
# MY REPORTS
# =========================================================

@app.route("/my-reports")
def my_reports():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    items = connection.execute(
        """
        SELECT *
        FROM items
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    connection.close()

    return render_template(
        "my_reports.html",
        items=items
    )


# =========================================================
# EDIT REPORT
# =========================================================

@app.route(
    "/edit-report/<int:item_id>",
    methods=["GET", "POST"]
)
def edit_report(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute(
        """
        SELECT *
        FROM items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    ).fetchone()

    if not item:

        connection.close()

        return "Report not found!"

    if request.method == "POST":

        item_type = request.form.get(
            "item_type",
            ""
        ).strip()

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        item_date = request.form.get(
            "item_date",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if item_type not in ["Lost", "Found"]:

            connection.close()

            return "Invalid item type!"

        connection.execute(
            """
            UPDATE items
            SET
                item_type = ?,
                item_name = ?,
                category = ?,
                location = ?,
                item_date = ?,
                description = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                item_type,
                item_name,
                category,
                location,
                item_date,
                description,
                item_id,
                session["user_id"]
            )
        )

        connection.commit()

        connection.close()

        return redirect(
            url_for("my_reports")
        )

    connection.close()

    return render_template(
        "edit_report.html",
        item=item
    )


# =========================================================
# REPORT DETAILS
# =========================================================

@app.route("/report-details/<int:item_id>")
def report_details(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute(
        """
        SELECT
            items.*,
            users.name AS reporter_name
        FROM items

        JOIN users
            ON items.user_id = users.id

        WHERE items.id = ?
        """,
        (item_id,)
    ).fetchone()

    connection.close()

    if not item:

        return "Report not found!"

    return render_template(
        "report_details.html",
        item=item
    )


# =========================================================
# SMART POSSIBLE MATCHES
# =========================================================

@app.route("/matches/<int:item_id>")
def matches(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute(
        """
        SELECT *
        FROM items
        WHERE id = ?
        """,
        (item_id,)
    ).fetchone()

    if not item:

        connection.close()

        return "Report not found!"

    # Opposite item type
    if item["item_type"] == "Lost":

        opposite_type = "Found"

    else:

        opposite_type = "Lost"

    possible_items = connection.execute(
        """
        SELECT *
        FROM items
        WHERE item_type = ?
        AND id != ?
        AND status != 'recovered'
        """,
        (
            opposite_type,
            item_id
        )
    ).fetchall()

    connection.close()

    current_name = (
        item["item_name"] or ""
    ).lower().strip()

    current_category = (
        item["category"] or ""
    ).lower().strip()

    current_location = (
        item["location"] or ""
    ).lower().strip()

    current_description = (
        item["description"] or ""
    ).lower().strip()

    matched_items = []

    for match in possible_items:

        score = 0

        reasons = []

        match_name = (
            match["item_name"] or ""
        ).lower().strip()

        match_category = (
            match["category"] or ""
        ).lower().strip()

        match_location = (
            match["location"] or ""
        ).lower().strip()

        match_description = (
            match["description"] or ""
        ).lower().strip()

        # =====================================================
        # ITEM NAME
        # =====================================================

        if current_name and match_name:

            if current_name == match_name:

                score += 40

                reasons.append(
                    "Item name is exactly the same"
                )

            elif (
                current_name in match_name
                or match_name in current_name
            ):

                score += 30

                reasons.append(
                    "Item names are similar"
                )

        # =====================================================
        # CATEGORY
        # =====================================================

        if current_category and match_category:

            if current_category == match_category:

                score += 30

                reasons.append(
                    "Category is the same"
                )

        # =====================================================
        # LOCATION
        # =====================================================

        if current_location and match_location:

            if current_location == match_location:

                score += 20

                reasons.append(
                    "Location is the same"
                )

            elif (
                current_location in match_location
                or match_location in current_location
            ):

                score += 15

                reasons.append(
                    "Location is similar"
                )

        # =====================================================
        # DESCRIPTION
        # =====================================================

        if current_description and match_description:

            current_words = set(
                current_description.split()
            )

            match_words = set(
                match_description.split()
            )

            common_words = (
                current_words & match_words
            )

            useful_words = {
                word
                for word in common_words
                if len(word) > 3
            }

            if useful_words:

                score += 10

                reasons.append(
                    "Description contains similar words"
                )

        # =====================================================
        # ADD MATCH
        # =====================================================

        if score >= 20:

            match_data = dict(match)

            match_data["match_score"] = min(
                score,
                100
            )

            match_data["match_reasons"] = reasons

            matched_items.append(
                match_data
            )

    matched_items.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )

    matched_items = matched_items[:20]

    return render_template(
        "matches.html",
        item=item,
        matched_items=matched_items
    )


# =========================================================
# CLAIM ITEM
# =========================================================

@app.route(
    "/claim/<int:item_id>",
    methods=["GET", "POST"]
)
def claim_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute(
        """
        SELECT
            items.*,
            users.name AS reporter_name
        FROM items

        JOIN users
            ON items.user_id = users.id

        WHERE items.id = ?
        """,
        (item_id,)
    ).fetchone()

    if not item:

        connection.close()

        return "Item not found!"

    if item["user_id"] == session["user_id"]:

        connection.close()

        return "You cannot claim your own report!"

    if item["item_type"] != "Found":

        connection.close()

        return "Only found items can be claimed!"

    if item["status"] == "recovered":

        connection.close()

        return "This item has already been recovered!"

    if request.method == "POST":

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not message:

            connection.close()

            return "Please enter a claim message!"

        if len(message) < 10:

            connection.close()

            return (
                "Claim message must contain "
                "at least 10 characters!"
            )

        existing_claim = connection.execute(
            """
            SELECT *
            FROM claims
            WHERE item_id = ?
            AND claimant_id = ?
            AND status = 'pending'
            """,
            (
                item_id,
                session["user_id"]
            )
        ).fetchone()

        if existing_claim:

            connection.close()

            return (
                "You have already submitted "
                "a claim for this item!"
            )

        connection.execute(
            """
            INSERT INTO claims
            (
                item_id,
                claimant_id,
                message,
                status
            )
            VALUES (?, ?, ?, 'pending')
            """,
            (
                item_id,
                session["user_id"],
                message
            )
        )

        connection.commit()

        connection.close()

        return redirect(
            url_for("my_claims")
        )

    connection.close()

    return render_template(
        "claim.html",
        item=item
    )


# =========================================================
# MY CLAIMS
# =========================================================

@app.route("/my-claims")
def my_claims():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    claims = connection.execute(
        """
        SELECT
            claims.id,
            claims.item_id,
            claims.message,
            claims.status,
            claims.created_at,

            items.item_name,
            items.item_type,
            items.category,
            items.location,
            items.image,

            users.name AS reporter_name,
            users.email AS reporter_email

        FROM claims

        JOIN items
            ON claims.item_id = items.id

        JOIN users
            ON items.user_id = users.id

        WHERE claims.claimant_id = ?

        ORDER BY claims.id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    connection.close()

    return render_template(
        "my_claims.html",
        claims=claims
    )


# =========================================================
# RECEIVED CLAIMS
# =========================================================

@app.route("/claims")
def claims():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    claims = connection.execute(
        """
        SELECT
            claims.id,
            claims.item_id,
            claims.message,
            claims.status,
            claims.created_at,

            items.item_name,
            items.item_type,
            items.category,
            items.location,
            items.image,

            users.name AS claimant_name,
            users.email AS claimant_email

        FROM claims

        JOIN items
            ON claims.item_id = items.id

        JOIN users
            ON claims.claimant_id = users.id

        WHERE items.user_id = ?

        ORDER BY claims.id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    connection.close()

    return render_template(
        "claims.html",
        claims=claims
    )


# =========================================================
# ACCEPT CLAIM
# =========================================================

@app.route(
    "/claim/<int:claim_id>/accept",
    methods=["POST"]
)
def accept_claim(claim_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    claim = connection.execute(
        """
        SELECT
            claims.id,
            claims.item_id,
            claims.status,
            items.user_id AS owner_id,
            items.status AS item_status

        FROM claims

        JOIN items
            ON claims.item_id = items.id

        WHERE claims.id = ?
        AND items.user_id = ?
        """,
        (
            claim_id,
            session["user_id"]
        )
    ).fetchone()

    if not claim:

        connection.close()

        return "Claim not found!"

    if claim["status"] != "pending":

        connection.close()

        return "This claim has already been processed!"

    if claim["item_status"] == "recovered":

        connection.close()

        return "This item has already been recovered!"

    connection.execute(
        """
        UPDATE claims
        SET status = 'accepted'
        WHERE id = ?
        """,
        (claim_id,)
    )

    connection.execute(
        """
        UPDATE items
        SET status = 'recovered'
        WHERE id = ?
        """,
        (claim["item_id"],)
    )

    connection.execute(
        """
        UPDATE claims
        SET status = 'rejected'
        WHERE item_id = ?
        AND id != ?
        AND status = 'pending'
        """,
        (
            claim["item_id"],
            claim_id
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("claims")
    )


# =========================================================
# REJECT CLAIM
# =========================================================

@app.route(
    "/claim/<int:claim_id>/reject",
    methods=["POST"]
)
def reject_claim(claim_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    claim = connection.execute(
        """
        SELECT
            claims.id,
            claims.status

        FROM claims

        JOIN items
            ON claims.item_id = items.id

        WHERE claims.id = ?
        AND items.user_id = ?
        """,
        (
            claim_id,
            session["user_id"]
        )
    ).fetchone()

    if not claim:

        connection.close()

        return "Claim not found!"

    if claim["status"] != "pending":

        connection.close()

        return "This claim has already been processed!"

    connection.execute(
        """
        UPDATE claims
        SET status = 'rejected'
        WHERE id = ?
        """,
        (claim_id,)
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("claims")
    )


# =========================================================
# MARK REPORT AS RECOVERED
# =========================================================

@app.route(
    "/recover-report/<int:item_id>",
    methods=["POST"]
)
def recover_report(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute(
        """
        SELECT id
        FROM items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    ).fetchone()

    if not item:

        connection.close()

        return "Report not found!"

    connection.execute(
        """
        UPDATE items
        SET status = 'recovered'
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    )

    connection.execute(
        """
        UPDATE claims
        SET status = 'rejected'
        WHERE item_id = ?
        AND status = 'pending'
        """,
        (item_id,)
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("my_reports")
    )


# =========================================================
# DELETE REPORT
# =========================================================

@app.route(
    "/delete-report/<int:item_id>",
    methods=["POST"]
)
def delete_report(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute(
        """
        SELECT image
        FROM items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    ).fetchone()

    if not item:

        connection.close()

        return "Report not found!"

    # Delete messages
    connection.execute(
        """
        DELETE FROM messages
        WHERE item_id = ?
        """,
        (item_id,)
    )

    # Delete claims
    connection.execute(
        """
        DELETE FROM claims
        WHERE item_id = ?
        """,
        (item_id,)
    )

    # Delete item
    connection.execute(
        """
        DELETE FROM items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    )

    connection.commit()

    connection.close()

    # Delete image
    if item["image"]:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            item["image"]
        )

        if os.path.exists(image_path):

            os.remove(image_path)

    return redirect(
        url_for("my_reports")
    )


# =========================================================
# PRIVATE CHAT
# =========================================================

@app.route(
    "/chat/<int:item_id>/<int:match_id>",
    methods=["GET", "POST"]
)
def private_chat(item_id, match_id):

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    # =====================================================
    # GET CURRENT REPORT
    # =====================================================

    current_item = connection.execute(
        """
        SELECT
            items.*,
            users.name AS reporter_name
        FROM items

        JOIN users
            ON items.user_id = users.id

        WHERE items.id = ?
        """,
        (item_id,)
    ).fetchone()

    # =====================================================
    # GET MATCH REPORT
    # =====================================================

    match_item = connection.execute(
        """
        SELECT
            items.*,
            users.name AS reporter_name
        FROM items

        JOIN users
            ON items.user_id = users.id

        WHERE items.id = ?
        """,
        (match_id,)
    ).fetchone()

    # =====================================================
    # CHECK REPORTS
    # =====================================================

    if not current_item or not match_item:

        connection.close()

        return "Chat report not found!"

    current_user_id = session["user_id"]

    user1_id = current_item["user_id"]

    user2_id = match_item["user_id"]

    # =====================================================
    # ONLY REPORT OWNERS CAN CHAT
    # =====================================================

    if current_user_id not in [
        user1_id,
        user2_id
    ]:

        connection.close()

        return "You are not allowed to access this chat!"

    # =====================================================
    # SAME USER CHECK
    # =====================================================

    if user1_id == user2_id:

        connection.close()

        return "You cannot chat with yourself!"

    # =====================================================
    # FIND OTHER USER
    # =====================================================

    if current_user_id == user1_id:

        other_user_id = user2_id

        other_user_name = match_item["reporter_name"]

    else:

        other_user_id = user1_id

        other_user_name = current_item["reporter_name"]

    # =====================================================
    # CANONICAL CHAT ITEM
    # =====================================================

    chat_item_id = min(
        item_id,
        match_id
    )

    # =====================================================
    # SEND MESSAGE
    # =====================================================

    if request.method == "POST":

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not message:

            connection.close()

            return redirect(
                url_for(
                    "private_chat",
                    item_id=item_id,
                    match_id=match_id
                )
            )

        if len(message) > 2000:

            connection.close()

            return "Message is too long!"

        connection.execute(
            """
            INSERT INTO messages
            (
                item_id,
                sender_id,
                receiver_id,
                message
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                chat_item_id,
                current_user_id,
                other_user_id,
                message
            )
        )

        connection.commit()

        connection.close()

        return redirect(
            url_for(
                "private_chat",
                item_id=item_id,
                match_id=match_id
            )
        )

    # =====================================================
    # GET CHAT MESSAGES
    # =====================================================

    messages = connection.execute(
        """
        SELECT
            messages.*,
            users.name AS sender_name

        FROM messages

        JOIN users
            ON messages.sender_id = users.id

        WHERE messages.item_id = ?

        AND
        (
            (
                messages.sender_id = ?
                AND messages.receiver_id = ?
            )

            OR

            (
                messages.sender_id = ?
                AND messages.receiver_id = ?
            )
        )

        ORDER BY messages.id ASC
        """,
        (
            chat_item_id,
            current_user_id,
            other_user_id,
            other_user_id,
            current_user_id
        )
    ).fetchall()

    # =====================================================
    # MARK RECEIVED MESSAGES AS READ
    # =====================================================

    connection.execute(
        """
        UPDATE messages

        SET is_read = 1

        WHERE item_id = ?

        AND sender_id = ?

        AND receiver_id = ?

        AND is_read = 0
        """,
        (
            chat_item_id,
            other_user_id,
            current_user_id
        )
    )

    connection.commit()

    connection.close()

    return render_template(
        "chat.html",
        messages=messages,
        current_user_id=current_user_id,
        other_user_name=other_user_name,
        current_item=current_item,
        match_item=match_item,
        item_id=item_id,
        match_id=match_id
    )


# =========================================================
# START CHAT FROM MATCH
# =========================================================

@app.route(
    "/start-chat/<int:item_id>/<int:match_id>"
)
def start_chat(item_id, match_id):

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    # =====================================================
    # GET CURRENT REPORT
    # =====================================================

    current_item = connection.execute(
        """
        SELECT user_id
        FROM items
        WHERE id = ?
        """,
        (item_id,)
    ).fetchone()

    # =====================================================
    # GET MATCH REPORT
    # =====================================================

    match_item = connection.execute(
        """
        SELECT user_id
        FROM items
        WHERE id = ?
        """,
        (match_id,)
    ).fetchone()

    connection.close()

    # =====================================================
    # CHECK REPORTS
    # =====================================================

    if not current_item or not match_item:

        return "Report not found!"

    # =====================================================
    # USER MUST OWN ONE REPORT
    # =====================================================

    if session["user_id"] not in [
        current_item["user_id"],
        match_item["user_id"]
    ]:

        return "You cannot start this chat!"

    # =====================================================
    # SAME USER CHECK
    # =====================================================

    if current_item["user_id"] == match_item["user_id"]:

        return "You cannot chat with yourself!"

    # =====================================================
    # OPEN PRIVATE CHAT
    # =====================================================

    return redirect(
        url_for(
            "private_chat",
            item_id=item_id,
            match_id=match_id
        )
    )
# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # =====================================================
    # DATABASE CONNECTION
    # =====================================================

    connection = get_db_connection()


    # =====================================================
    # GET LOGGED-IN USER
    # =====================================================

    user = connection.execute(
        """
        SELECT
            id,
            name,
            email,
            phone,
            profile_photo,
            created_at
        FROM users
        WHERE id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()


    connection.close()


    # =====================================================
    # USER NOT FOUND
    # =====================================================

    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )


    # =====================================================
    # SHOW PROFILE
    # =====================================================

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )


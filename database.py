
import sqlite3


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = sqlite3.connect("lost_found.db")

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    connection = get_db_connection()


    # =====================================================
    # USERS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # =====================================================
    # SAFE MIGRATION FOR EXISTING DATABASE
    # =====================================================
    # Ye check karega ki phone aur profile_photo
    # columns already hain ya nahi.
    #
    # Agar nahi hain to automatically add karega.
    #
    # IMPORTANT:
    # Existing users delete nahi honge.
    # Existing reports delete nahi honge.
    # Existing claims delete nahi honge.
    # Existing chats delete nahi hongi.

    user_columns = connection.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in user_columns
    ]


    # =====================================================
    # ADD PHONE COLUMN
    # =====================================================

    if "phone" not in column_names:

        connection.execute("""
            ALTER TABLE users
            ADD COLUMN phone TEXT
        """)


    # =====================================================
    # ADD PROFILE PHOTO COLUMN
    # =====================================================

    if "profile_photo" not in column_names:

        connection.execute("""
            ALTER TABLE users
            ADD COLUMN profile_photo TEXT
        """)


    # =====================================================
    # ITEMS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            item_type TEXT NOT NULL,

            item_name TEXT NOT NULL,

            category TEXT NOT NULL,

            description TEXT,

            location TEXT NOT NULL,

            item_date TEXT NOT NULL,

            image TEXT,

            status TEXT DEFAULT 'active',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
        )
    """)


    # =====================================================
    # CLAIMS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS claims (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            claimant_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            status TEXT DEFAULT 'pending',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (item_id)
            REFERENCES items(id),

            FOREIGN KEY (claimant_id)
            REFERENCES users(id)
        )
    """)


    # =====================================================
    # PRIVATE MESSAGES TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            sender_id INTEGER NOT NULL,

            receiver_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            is_read INTEGER DEFAULT 0,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (item_id)
            REFERENCES items(id),

            FOREIGN KEY (sender_id)
            REFERENCES users(id),

            FOREIGN KEY (receiver_id)
            REFERENCES users(id)
        )
    """)


    # =====================================================
    # MESSAGE INDEXES
    # =====================================================

    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_messages_item
        ON messages(item_id)
    """)


    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_messages_sender
        ON messages(sender_id)
    """)


    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_messages_receiver
        ON messages(receiver_id)
    """)


    # =====================================================
    # SAVE CHANGES
    # =====================================================

    connection.commit()

    connection.close()


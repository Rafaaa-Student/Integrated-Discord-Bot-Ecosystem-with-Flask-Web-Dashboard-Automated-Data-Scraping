import sqlite3
import os
from datetime import date, datetime, timedelta

# Path ke database
DB_DIR = os.path.dirname(__file__)
DB_FILE = os.path.join(DB_DIR, 'books.db')

def get_db_connection():
    """Create and return database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with books table, conversation history table, AI usage tracking table, and indexes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judul TEXT NOT NULL,
            harga TEXT,
            deskripsi TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create conversation history table for AI memory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create AI usage tracking table (The Guard System)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_usage (
            user_id TEXT,
            platform TEXT,
            daily_count INTEGER DEFAULT 0,
            last_ask_date TEXT DEFAULT NULL,
            PRIMARY KEY (user_id, platform)
        )
    ''')
    
    # Create exclusive events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exclusive_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_object TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            winner_id TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP DEFAULT NULL
        )
    ''')
    
    # Create inventory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            rarity TEXT NOT NULL,
            obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_id)
        )
    ''')
    
    # Create AI boost table (for extra limits)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_boosts (
            user_id TEXT PRIMARY KEY,
            extra_limit INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create selected badge table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS selected_badge (
            user_id TEXT PRIMARY KEY,
            badge_name TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create bug reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bug_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            guild_name TEXT NOT NULL,
            report_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for faster search
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_judul ON books(judul)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deskripsi ON books(deskripsi)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversations(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_created ON conversations(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_exclusive_active ON exclusive_events(is_active)')
    
    conn.commit()
    conn.close()

def add_book(judul, harga, deskripsi, url):
    """Add a new book to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO books (judul, harga, deskripsi, url)
        VALUES (?, ?, ?, ?)
    ''', (judul, harga, deskripsi, url))
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    return book_id

def get_books(limit=None, offset=0):
    """Get books from database with optional limit and offset"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if limit:
        cursor.execute('SELECT * FROM books ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset))
    else:
        cursor.execute('SELECT * FROM books ORDER BY id DESC')
    
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return books

def search_books(keyword):
    """Search books by judul or deskripsi (case-insensitive)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    search_term = f'%{keyword}%'
    cursor.execute('''
        SELECT * FROM books 
        WHERE LOWER(judul) LIKE LOWER(?) 
           OR LOWER(deskripsi) LIKE LOWER(?)
        ORDER BY id DESC
    ''', (search_term, search_term))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_book_count():
    """Get total number of books in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM books')
    count = cursor.fetchone()['count']
    conn.close()
    return count

def book_exists(judul):
    """Check if a book with given judul already exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM books WHERE judul = ?', (judul,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_random_book():
    """Get a random book from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books ORDER BY RANDOM() LIMIT 1')
    book = cursor.fetchone()
    conn.close()
    return dict(book) if book else None

# ==================== CONVERSATION MEMORY FUNCTIONS ====================
def save_conversation(user_id, role, content):
    """Save a conversation message to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO conversations (user_id, role, content)
        VALUES (?, ?, ?)
    ''', (user_id, role, content))
    conn.commit()
    conn.close()

def get_conversation_history(user_id, limit=10):
    """Get conversation history for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, content, created_at 
        FROM conversations 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    # Reverse to get chronological order
    return history[::-1]

def clear_conversation(user_id):
    """Clear conversation history for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# ==================== AI USAGE TRACKING FUNCTIONS (The Guard System) ====================
def get_ai_usage(user_id, platform='discord'):
    """Get AI usage data for a user on a specific platform"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT daily_count, last_ask_date FROM ai_usage WHERE user_id = ? AND platform = ?', (str(user_id), platform))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'daily_count': result['daily_count'], 'last_ask_date': result['last_ask_date']}
    return {'daily_count': 0, 'last_ask_date': None}

def check_ai_limit(user_id, admin_id, daily_limit=10, platform='discord'):
    """Check if user has reached daily AI limit. Returns (can_use, remaining, message)"""
    # Admin bypass
    if str(user_id) == str(admin_id):
        return True, float('inf'), "Admin - unlimited access"
    
    usage = get_ai_usage(user_id, platform)
    today = str(date.today())
    
    # Get extra boost from inventory/shop
    extra_boost = get_ai_boost(user_id)
    total_limit = daily_limit + extra_boost
    
    # Reset count if it's a new day
    if usage['last_ask_date'] != today:
        reset_ai_count(user_id, platform)
        return True, total_limit, f"New day! Reset to {total_limit} uses (Base: {daily_limit} + Boost: {extra_boost})"
    
    remaining = total_limit - usage['daily_count']
    if remaining <= 0:
        return False, 0, f"⚠️ Limit harian tercapai! Maksimal {total_limit} kali per hari (Base: {daily_limit} + Boost: {extra_boost})."
    
    return True, remaining, f"✅ Sisa kuota hari ini: {remaining}/{total_limit}"

def increment_ai_count(user_id, platform='discord'):
    """Increment AI usage count for a user on a specific platform"""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = str(date.today())
    
    cursor.execute('SELECT daily_count FROM ai_usage WHERE user_id = ? AND platform = ?', (str(user_id), platform))
    result = cursor.fetchone()
    
    if result:
        # Check if it's a new day
        cursor.execute('SELECT last_ask_date FROM ai_usage WHERE user_id = ? AND platform = ?', (str(user_id), platform))
        last_date = cursor.fetchone()['last_ask_date']
        
        if last_date != today:
            # Reset for new day
            cursor.execute('UPDATE ai_usage SET daily_count = 1, last_ask_date = ? WHERE user_id = ? AND platform = ?', (today, str(user_id), platform))
        else:
            # Increment
            cursor.execute('UPDATE ai_usage SET daily_count = daily_count + 1 WHERE user_id = ? AND platform = ?', (str(user_id), platform))
    else:
        # Create new entry
        cursor.execute('INSERT INTO ai_usage (user_id, platform, daily_count, last_ask_date) VALUES (?, ?, 1, ?)', (str(user_id), platform, today))
    
    conn.commit()
    conn.close()

def reset_ai_count(user_id, platform='discord'):
    """Reset AI usage count for a user on a specific platform"""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = str(date.today())
    cursor.execute('UPDATE ai_usage SET daily_count = 0, last_ask_date = ? WHERE user_id = ? AND platform = ?', (today, str(user_id), platform))
    conn.commit()
    conn.close()

def get_remaining_uses(user_id, admin_id, daily_limit=10, platform='discord'):
    """Get remaining AI uses for a user on a specific platform"""
    can_use, remaining, message = check_ai_limit(user_id, admin_id, daily_limit, platform)
    return remaining if can_use else 0

# ==================== EXCLUSIVE EVENT FUNCTIONS ====================
def create_exclusive_event(target_object):
    """Create a new exclusive event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO exclusive_events (target_object, is_active)
            VALUES (?, 1)
        ''', (target_object,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating exclusive event: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def check_event_status():
    """Check if there's an active exclusive event. Returns event data or None"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, target_object, is_active, winner_id, created_at, closed_at
            FROM exclusive_events
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None
    except Exception as e:
        print(f"Error checking event status: {e}")
        return None
    finally:
        conn.close()

def claim_exclusive_event(user_id):
    """Claim the exclusive event. Returns (success, message)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if there's an active event
        cursor.execute('''
            SELECT id, target_object, is_active, winner_id, closed_at
            FROM exclusive_events
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        event = cursor.fetchone()
        
        if not event:
            return False, "no_event"
        
        event_data = dict(event)
        
        # Check if already claimed
        if event_data['winner_id']:
            # Check time difference
            if event_data['closed_at']:
                closed_time = datetime.strptime(event_data['closed_at'], '%Y-%m-%d %H:%M:%S')
                time_diff = datetime.now() - closed_time
                
                if time_diff < timedelta(minutes=2):
                    return False, "recently_claimed"
                else:
                    return False, "no_event"
            else:
                return False, "no_event"
        
        # Claim the event
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE exclusive_events
            SET is_active = 0, winner_id = ?, closed_at = ?
            WHERE id = ?
        ''', (str(user_id), current_time, event_data['id']))
        
        conn.commit()
        return True, event_data['target_object']
        
    except Exception as e:
        print(f"Error claiming exclusive event: {e}")
        conn.rollback()
        return False, "error"
    finally:
        conn.close()

# ==================== SHOP & INVENTORY FUNCTIONS ====================
def add_to_inventory(user_id, item_id, item_name, rarity):
    """Add an item to user's inventory (prevents duplicates)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO inventory (user_id, item_id, item_name, rarity)
            VALUES (?, ?, ?, ?)
        ''', (str(user_id), item_id, item_name, rarity))
        conn.commit()
        # Check if row was actually inserted
        if cursor.rowcount > 0:
            return True
        else:
            print(f"Item {item_id} already exists in inventory for user {user_id}")
            return False
    except Exception as e:
        print(f"Error adding to inventory: {e}")
        return False
    finally:
        conn.close()

def get_inventory(user_id):
    """Get all items in user's inventory"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT item_id, item_name, rarity, obtained_at FROM inventory WHERE user_id = ?', (str(user_id),))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def add_ai_boost(user_id, amount=5):
    """Add extra AI limit to a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT extra_limit FROM ai_boosts WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()
        if result:
            cursor.execute('UPDATE ai_boosts SET extra_limit = extra_limit + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', (amount, str(user_id)))
        else:
            cursor.execute('INSERT INTO ai_boosts (user_id, extra_limit) VALUES (?, ?)', (str(user_id), amount))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding AI boost: {e}")
        return False
    finally:
        conn.close()

def get_ai_boost(user_id):
    """Get extra AI limit for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT extra_limit FROM ai_boosts WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()
        return result['extra_limit'] if result else 0
    finally:
        conn.close()

def set_selected_badge(user_id, badge_name):
    """Set the selected badge for a user to display on profile"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO selected_badge (user_id, badge_name, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET 
            badge_name = excluded.badge_name,
            updated_at = CURRENT_TIMESTAMP
        ''', (str(user_id), badge_name))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error setting selected badge: {e}")
        return False
    finally:
        conn.close()

def get_selected_badge(user_id):
    """Get the selected badge for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT badge_name FROM selected_badge WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()
        return result['badge_name'] if result else None
    finally:
        conn.close()

def save_bug_report(user_id, username, guild_name, report_text):
    """Save a bug report to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO bug_reports (user_id, username, guild_name, report_text)
            VALUES (?, ?, ?, ?)
        ''', (str(user_id), username, guild_name, report_text))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving bug report: {e}")
        return False
    finally:
        conn.close()

def get_bug_reports():
    """Get all bug reports (Admin only)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM bug_reports ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

# Initialize database on import
if __name__ != '__main__':
    init_db()

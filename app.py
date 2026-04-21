from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Path ke file data bot
DATA_DIR = os.path.join(os.path.dirname(__file__), '..')
POIN_FILE = os.path.join(DATA_DIR, 'poin_hijau.json')
CACHE_FILE = os.path.join(DATA_DIR, 'database_buku_log.json')

def load_poin():
    if os.path.exists(POIN_FILE):
        with open(POIN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_books():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@app.route('/')
def home():
    poin_data = load_poin()
    total_users = len(poin_data)
    total_poin = sum(poin_data.values())
    books = load_books()
    total_books = len(books)
    return render_template('home.html', total_users=total_users, total_poin=total_poin, total_books=total_books)

@app.route('/leaderboard')
def leaderboard():
    poin_data = load_poin()
    sorted_users = sorted(poin_data.items(), key=lambda x: x[1], reverse=True)[:10]
    return render_template('leaderboard.html', leaderboard=sorted_users)

@app.route('/books')
def books():
    books = load_books()
    return render_template('books.html', books=books[:50])  # Tampilkan 50 buku pertama

@app.route('/search_books', methods=['GET', 'POST'])
def search_books():
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').lower()
        books = load_books()
        results = [book for book in books if keyword in book.get('judul', '').lower() or keyword in book.get('deskripsi', '').lower()]
        return render_template('search_results.html', results=results, keyword=keyword)
    return render_template('search_books.html')

if __name__ == '__main__':
    app.run(debug=True)

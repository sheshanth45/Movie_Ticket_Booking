from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
import uuid
import time

app = Flask(__name__)
app.secret_key = "super_secret_key_for_flash_messages"

# 1. Movies Data
movies = [
    {
        "id": "m1",
        "title": "RRR",
        "description": "A fictitious story about two legendary revolutionaries and their journey away from home before they started fighting for their country in 1920s.",
        "poster": "rrr.png",
        "timings": ["10:00 AM", "02:00 PM", "06:00 PM"]
    },
    {
        "id": "m2",
        "title": "Pushpa: The Rise",
        "description": "A labourer rises through the ranks of a red sandal smuggling syndicate, making some powerful enemies in the process.",
        "poster": "pushpa.png",
        "timings": ["11:00 AM", "03:00 PM", "07:00 PM"]
    },
    {
        "id": "m3",
        "title": "Baahubali: The Conclusion",
        "description": "When Shiva, the son of Bahubali, learns about his heritage, he begins to look for answers. His story is juxtaposed with past events that unfolded in the Mahishmati Kingdom.",
        "poster": "bahubali.png",
        "timings": ["09:30 AM", "01:30 PM", "05:30 PM", "09:00 PM"]
    }
]

# 2. Seat Layout Initialization (5 Rows, 8 Columns)
# Row 0 (A), Row 1 (B) -> VIP
# Row 2 (C), Row 3 (D), Row 4 (E) -> Normal
# 0 = Available, 1 = Booked
def init_seats():
    # Returns a 5x8 list of zeros
    return [[0 for _ in range(8)] for _ in range(5)]

# Dictionary to hold the seat state for each movie and timing combination
# Structure: show_states["m1"]["10:00 AM"] = 2D list
show_states = {}
for m in movies:
    show_states[m["id"]] = {}
    for t in m["timings"]:
        show_states[m["id"]][t] = init_seats()

# Dictionary to hold seats
# held_seats[(movie_id, timing, r, c)] = {'username': username, 'expires_at': timestamp}
held_seats = {}

def expire_held_seats():
    current_time = time.time()
    expired_keys = []
    for key, data in held_seats.items():
        if current_time > data['expires_at']:
            expired_keys.append(key)
    
    for key in expired_keys:
        movie_id, timing, r, c = key
        show_states[movie_id][timing][r][c] = 0 # Release
        del held_seats[key]

# 3. Bookings Data Store
# List of dictionaries to store booking records
bookings = []

# 4. Users Data Store
users = [
    {"username": "admin", "password": "password123", "role": "admin"}
]

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to require admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session.get('role') != 'admin':
            flash("Admin access required.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get movie by ID
def get_movie(movie_id):
    for m in movies:
        if m["id"] == movie_id:
            return m
    return None

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html', movies=movies)

@app.route('/movie/<movie_id>')
def movie_details(movie_id):
    movie = get_movie(movie_id)
    if not movie:
        return "Movie not found", 404
    return render_template('movie.html', movie=movie)

@app.route('/book/<movie_id>/<timing>')
@login_required
def book_seats(movie_id, timing):
    expire_held_seats()
    movie = get_movie(movie_id)
    if not movie or timing not in movie["timings"]:
        return "Invalid movie or timing", 404
    
    seats = show_states[movie_id][timing]
    return render_template('book.html', movie=movie, timing=timing, seats=seats)

@app.route('/api/seats_state/<movie_id>/<timing>')
def seats_state(movie_id, timing):
    expire_held_seats()
    
    if movie_id not in show_states or timing not in show_states[movie_id]:
        return jsonify({"success": False, "message": "Invalid movie or timing"}), 404
        
    seats = show_states[movie_id][timing]
    
    # We want to also tell the client which seats THEY are holding so they render as selected
    user_holds = []
    current_user = session.get('username')
    for r in range(5):
        for c in range(8):
            key = (movie_id, timing, r, c)
            if key in held_seats and held_seats[key]['username'] == current_user:
                user_holds.append({"row": r, "col": c})
                
    return jsonify({
        "success": True, 
        "seats": seats,
        "user_holds": user_holds
    })

@app.route('/api/hold', methods=['POST'])
@login_required
def hold_seat():
    expire_held_seats()
    data = request.json
    movie_id = data.get('movie_id')
    timing = data.get('timing')
    row = data.get('row')
    col = data.get('col')
    username = session.get('username')
    
    if movie_id not in show_states or timing not in show_states[movie_id]:
        return jsonify({"success": False, "message": "Invalid movie/timing"}), 404
        
    seats_grid = show_states[movie_id][timing]
    
    # Check if available
    if seats_grid[row][col] == 0:
        seats_grid[row][col] = 2 # Mark as held
        held_seats[(movie_id, timing, row, col)] = {
            'username': username,
            'expires_at': time.time() + 300 # 5 minutes hold
        }
        return jsonify({"success": True})
    elif seats_grid[row][col] == 2:
        # Check if it's already held by THIS user (maybe page refresh)
        if held_seats.get((movie_id, timing, row, col), {}).get('username') == username:
            # Renew hold
            held_seats[(movie_id, timing, row, col)]['expires_at'] = time.time() + 300
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "Seat not available"}), 400

@app.route('/api/release', methods=['POST'])
@login_required
def release_seat():
    data = request.json
    movie_id = data.get('movie_id')
    timing = data.get('timing')
    row = data.get('row')
    col = data.get('col')
    username = session.get('username')
    
    key = (movie_id, timing, row, col)
    if key in held_seats and held_seats[key]['username'] == username:
        show_states[movie_id][timing][row][col] = 0 # Release
        del held_seats[key]
        return jsonify({"success": True})
        
    return jsonify({"success": False})

@app.route('/api/book', methods=['POST'])
@login_required
def process_booking():
    data = request.json
    movie_id = data.get('movie_id')
    timing = data.get('timing')
    user_name = session.get('username')
    selected_seats = data.get('selected_seats') # list of dicts: {"row": r, "col": c}
    
    if not all([movie_id, timing, user_name, selected_seats]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400
        
    seats_grid = show_states[movie_id][timing]
    
    # Validation: Check if any of the selected seats are already booked by OTHERS
    for s in selected_seats:
        r, c = s['row'], s['col']
        # The seat must be either 0, or 2 and held by THIS user. 1 means booked.
        if seats_grid[r][c] == 1:
            return jsonify({"success": False, "message": "One or more selected seats are already booked. Please refresh and try again."}), 400
        if seats_grid[r][c] == 2:
            key = (movie_id, timing, r, c)
            if key not in held_seats or held_seats[key]['username'] != user_name:
                return jsonify({"success": False, "message": "One or more seats are held by someone else."}), 400
            
    # Calculate price and book seats
    total_price = 0
    seat_labels = []
    rows_chars = ['A', 'B', 'C', 'D', 'E']
    
    for s in selected_seats:
        r, c = s['row'], s['col']
        # Book the seat
        seats_grid[r][c] = 1
        
        # Remove from held_seats if it was there
        key = (movie_id, timing, r, c)
        if key in held_seats:
            del held_seats[key]
        
        # Calculate price
        if r < 2: # Row A and B (VIP)
            total_price += 200
        else:     # Row C, D, E (Normal)
            total_price += 100
            
        # Get label (e.g., A1, B4)
        seat_labels.append(f"{rows_chars[r]}{c+1}")
        
    # Create booking record
    booking_id = str(uuid.uuid4())[:8]
    movie = get_movie(movie_id)
    
    booking_record = {
        "id": booking_id,
        "movie_id": movie_id,
        "movie_title": movie["title"],
        "timing": timing,
        "user_name": user_name,
        "seats": seat_labels,
        "total_price": total_price,
        "raw_seats": selected_seats # Store to easily unbook later
    }
    
    bookings.append(booking_record)
    
    return jsonify({"success": True, "message": "Booking successful!", "booking_id": booking_id})

@app.route('/receipt/<booking_id>')
def receipt(booking_id):
    booking = next((b for b in bookings if b['id'] == booking_id), None)
    if not booking:
        return "Receipt not found", 404
    return render_template('receipt.html', booking=booking)

@app.route('/bookings')
@login_required
def all_bookings():
    if session.get('role') == 'admin':
        user_bookings = list(reversed(bookings))
        total_revenue = sum(b['total_price'] for b in bookings)
    else:
        user_bookings = list(reversed([b for b in bookings if b['user_name'] == session.get('username')]))
        total_revenue = sum(b['total_price'] for b in user_bookings)
    
    return render_template('bookings.html', bookings=user_bookings, total_revenue=total_revenue)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.", "error")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if any(u['username'] == username for u in users):
            flash("Username already exists.", "error")
        elif not username or not password:
            flash("Username and password are required.", "error")
        else:
            users.append({"username": username, "password": password, "role": "user"})
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

@app.route('/admin/users')
@admin_required
def admin_users():
    return render_template('admin_users.html', users=users)

@app.route('/api/cancel', methods=['POST'])
def cancel_booking():
    data = request.json
    booking_id = data.get('booking_id')
    
    # Find the booking
    booking_to_cancel = None
    for b in bookings:
        if b['id'] == booking_id:
            booking_to_cancel = b
            break
            
    if not booking_to_cancel:
        return jsonify({"success": False, "message": "Booking not found"}), 404
        
    # Free up the seats
    movie_id = booking_to_cancel['movie_id']
    timing = booking_to_cancel['timing']
    
    for s in booking_to_cancel['raw_seats']:
        r, c = s['row'], s['col']
        show_states[movie_id][timing][r][c] = 0 # Mark as available
        
    # Remove from bookings list
    bookings.remove(booking_to_cancel)
    
    return jsonify({"success": True, "message": "Booking cancelled successfully!"})

if __name__ == '__main__':
    # host='0.0.0.0' allows the app to be accessed from other devices on the same network
    app.run(host='0.0.0.0', debug=True, port=5000)

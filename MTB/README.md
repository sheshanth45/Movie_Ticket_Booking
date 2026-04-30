# CineTix - Movie Ticket Booking Application 🎬

A modern, full-stack movie ticket booking web application built using Python Flask for the backend and Vanilla HTML/CSS/JS for the frontend. This project demonstrates core Data Structures and Algorithms (DSA) concepts like 2D grids, dictionaries, and lists through an in-memory data store.

## Features
- **User Authentication:** Registration and Login system with secure session management.
- **Admin Dashboard:** Role-based access control. Admin accounts can view all user credentials and a master ledger of all bookings.
- **Interactive Theatre Layout:** Dynamic 5x8 seat grid with varying prices (VIP vs. Normal).
- **Live Seat Holding:** Asynchronous real-time polling locks a seat for 5 minutes the moment a user clicks it, preventing double-bookings.
- **Digital Receipts:** Auto-generated printable receipts upon successful booking.
- **Modern UI:** Responsive, glassmorphism-inspired dark mode interface.

## Tech Stack
- **Backend:** Python, Flask
- **Frontend:** Vanilla HTML5, CSS3, JavaScript
- **Database:** In-memory Python Data Structures

## How to Run Locally
1. Ensure Python is installed on your system.
2. Open a terminal in the project directory.
3. Install Flask if you haven't already: `pip install flask`
4. Run the application: `python app.py`
5. Open your web browser and navigate to `http://127.0.0.1:5000`.

**Default Admin Credentials:**
- Username: `admin`
- Password: `password123`

## Data Structures & Algorithms Used
This project was specifically designed to demonstrate core DSA concepts for academic purposes:

1. **2D Arrays (Matrices):** The theatre seat layout is represented as a 5x8 two-dimensional list. This allows for **O(1) constant time** access to check or update the status (Available, Booked, Held) of any specific seat using its row and column index.
2. **Hash Maps (Dictionaries):** 
   - Used extensively for `show_states` and `held_seats` to map complex composite keys (like `movie_id` + `timing` + `seat_coordinates`) to their respective states in **O(1)** time.
   - User sessions and movie data are parsed and stored using key-value pairs for optimal retrieval.
3. **Linear Search (O(N)):** Used to authenticate users by iterating through the registered users list, and to fetch specific movie objects by their ID.
4. **Lazy Expiration Algorithm:** Instead of running a continuous background thread to clear expired seat holds, the system uses a "lazy evaluation" algorithm. Every time a user requests the seat map, the system first iterates through the `held_seats` dictionary and removes any locks where `current_time > expires_at`.
5. **Asynchronous State Polling:** On the frontend, a polling algorithm (`setInterval`) queries the server every 3 seconds to fetch the updated 2D grid and dynamically updates the DOM to reflect seats held by concurrent users.

document.addEventListener('DOMContentLoaded', () => {
    
    // --- Booking Page Logic ---
    const seatGrid = document.getElementById('seatGrid');
    if (seatGrid) {
        const seats = document.querySelectorAll('.seat.available');
        const selectedSeatsCountEl = document.getElementById('selectedSeatsCount');
        const selectedSeatsLabelsEl = document.getElementById('selectedSeatsLabels');
        const totalPriceEl = document.getElementById('totalPrice');
        const confirmBtn = document.getElementById('confirmBookingBtn');

        let selectedSeats = [];
        let totalPrice = 0;

        // Toggle seat selection
        seats.forEach(seat => {
            seat.addEventListener('click', async () => {
                const row = parseInt(seat.dataset.row);
                const col = parseInt(seat.dataset.col);
                const price = parseInt(seat.dataset.price);
                const label = seat.dataset.label;
                
                if (seat.classList.contains('held') && !seat.classList.contains('selected')) {
                    // Someone else holds it
                    return;
                }

                if (seat.classList.contains('selected')) {
                    // Deselect and release
                    const res = await fetch('/api/release', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({movie_id: MOVIE_ID, timing: TIMING, row, col})
                    });
                    if (res.ok) {
                        seat.classList.remove('selected');
                        selectedSeats = selectedSeats.filter(s => s.label !== label);
                        totalPrice -= price;
                        updateSummary();
                    }
                } else {
                    // Select and hold
                    const res = await fetch('/api/hold', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({movie_id: MOVIE_ID, timing: TIMING, row, col})
                    });
                    const data = await res.json();
                    
                    if (data.success) {
                        seat.classList.add('selected');
                        selectedSeats.push({ row, col, price, label });
                        totalPrice += price;
                        updateSummary();
                    } else {
                        // Someone just grabbed it
                        seat.classList.remove('available');
                        seat.classList.add('held');
                        alert('Sorry, this seat was just held by someone else.');
                    }
                }
            });
        });
        
        // Polling state every 3 seconds
        setInterval(async () => {
            try {
                const res = await fetch(`/api/seats_state/${MOVIE_ID}/${TIMING}`);
                const data = await res.json();
                
                if (data.success) {
                    const grid = data.seats;
                    const myHolds = data.user_holds || []; // [{row, col}]
                    
                    // Re-evaluate seats
                    seats.forEach(seat => {
                        const r = parseInt(seat.dataset.row);
                        const c = parseInt(seat.dataset.col);
                        const state = grid[r][c];
                        
                        // state: 0=avail, 1=booked, 2=held
                        if (state === 1) {
                            seat.className = `seat booked ${r >= 2 ? 'normal' : 'vip'}`;
                        } else if (state === 2) {
                            // Is it MY hold?
                            const isMine = myHolds.some(h => h.row === r && h.col === c);
                            if (isMine) {
                                // Keep it selected
                                if (!seat.classList.contains('selected')) {
                                    seat.className = `seat available selected ${r >= 2 ? 'normal' : 'vip'}`;
                                }
                            } else {
                                // Someone else holds it
                                seat.className = `seat held ${r >= 2 ? 'normal' : 'vip'}`;
                            }
                        } else if (state === 0) {
                            // If it was selected by me, but I didn't hold it, or my hold expired
                            if (seat.classList.contains('selected')) {
                                const isMine = selectedSeats.some(s => s.row === r && s.col === c);
                                if (!isMine) {
                                    seat.className = `seat available ${r >= 2 ? 'normal' : 'vip'}`;
                                }
                            } else {
                                seat.className = `seat available ${r >= 2 ? 'normal' : 'vip'}`;
                            }
                        }
                    });
                }
            } catch(e) {
                console.error("Polling error", e);
            }
        }, 3000);
        
        // Release on unload
        window.addEventListener('beforeunload', () => {
            if (selectedSeats.length > 0) {
                // Use beacon to send data reliably when page unloads
                const blob = new Blob([JSON.stringify({
                    movie_id: MOVIE_ID,
                    timing: TIMING,
                    seats: selectedSeats.map(s => ({row: s.row, col: s.col}))
                })], {type : 'application/json'});
                // Wait, our backend release route takes row, col one by one.
                // It's better to add a batch release route, but for now we can just send multiple beacons.
                selectedSeats.forEach(s => {
                    const data = JSON.stringify({movie_id: MOVIE_ID, timing: TIMING, row: s.row, col: s.col});
                    navigator.sendBeacon('/api/release', new Blob([data], {type: 'application/json'}));
                });
            }
        });

        function updateSummary() {
            selectedSeatsCountEl.innerText = selectedSeats.length;
            totalPriceEl.innerText = totalPrice;
            
            if (selectedSeats.length > 0) {
                selectedSeatsLabelsEl.innerText = selectedSeats.map(s => s.label).join(', ');
                confirmBtn.disabled = false;
            } else {
                selectedSeatsLabelsEl.innerText = '-';
                confirmBtn.disabled = true;
            }
        }

        // Confirm Booking API Call
        confirmBtn.addEventListener('click', async () => {
            if (selectedSeats.length === 0) return;

            confirmBtn.disabled = true;
            confirmBtn.innerText = "Processing...";

            try {
                const response = await fetch('/api/book', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        movie_id: MOVIE_ID,
                        timing: TIMING,
                        selected_seats: selectedSeats.map(s => ({row: s.row, col: s.col}))
                    })
                });

                const data = await response.json();

                if (data.success) {
                    alert('Booking Successful!');
                    window.location.href = '/receipt/' + data.booking_id;
                } else {
                    alert('Error: ' + data.message);
                    window.location.reload();
                }
            } catch (error) {
                console.error("Error booking seats:", error);
                alert("An error occurred. Please try again.");
                confirmBtn.disabled = false;
                confirmBtn.innerText = "Confirm Booking";
            }
        });
    }

    // --- Bookings Page Logic ---
    const cancelBtns = document.querySelectorAll('.cancel-btn');
    cancelBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            if (!confirm("Are you sure you want to cancel this booking?")) return;

            const bookingId = e.target.dataset.bookingId;
            const originalText = e.target.innerText;
            e.target.innerText = "Cancelling...";
            e.target.disabled = true;

            try {
                const response = await fetch('/api/cancel', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ booking_id: bookingId })
                });

                const data = await response.json();

                if (data.success) {
                    window.location.reload();
                } else {
                    alert('Error: ' + data.message);
                    e.target.innerText = originalText;
                    e.target.disabled = false;
                }
            } catch (error) {
                console.error("Error cancelling booking:", error);
                alert("An error occurred. Please try again.");
                e.target.innerText = originalText;
                e.target.disabled = false;
            }
        });
    });
});

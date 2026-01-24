% --- Helmet facts ---
wears_helmet(driver1, yes).
wears_helmet(driver2, no).

% --- Signal facts ---
signal(junction1, red).
signal(junction2, green).

% --- Stopped facts ---
stopped_at(driver1, junction1, yes).
stopped_at(driver2, junction2, no).

% --- Speed facts ---
speed(driver1, 50).
speed(driver2, 80).

% --- Speed limit facts ---
speed_limit(junction1, 40).
speed_limit(junction2, 60).

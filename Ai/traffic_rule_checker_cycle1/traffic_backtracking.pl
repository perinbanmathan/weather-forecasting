% === Vehicles ===
vehicle(car1).
vehicle(car2).
vehicle(bike1).

% === Violations ===
signal_violation(car1).
speed_violation(car1).
helmet_violation(bike1).
speed_violation(bike1).
signal_violation(car2).

% === Rule: vehicle violation (one by one) ===
violation(V, signal) :- signal_violation(V).
violation(V, speed)  :- speed_violation(V).
violation(V, helmet) :- helmet_violation(V).

% === Rule: collect all violations (using backtracking) ===
all_violations(V, Violations) :-
    findall(Type, violation(V, Type), Violations).

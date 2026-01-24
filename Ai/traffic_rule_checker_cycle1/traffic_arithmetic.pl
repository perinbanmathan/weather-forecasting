% === Drivers ===
driver(mathan).
driver(ravi).
driver(anu).
driver(keerthi).

% === Violations ===
helmet_violation(mathan).
signal_violation(ravi).
speed_violation(ravi).
speed_violation(anu).

% === Fines per violation ===
fine(helmet_violation, 500).
fine(signal_violation, 1000).
fine(speed_violation, 1500).

% === Rule: violation and fine mapping ===
violation(X, helmet_violation, F) :-
    helmet_violation(X),
    fine(helmet_violation, F).

violation(X, signal_violation, F) :-
    signal_violation(X),
    fine(signal_violation, F).

violation(X, speed_violation, F) :-
    speed_violation(X),
    fine(speed_violation, F).

% === Collect all fines of a driver ===
all_fines(X, List) :-
    findall(F, violation(X, _, F), List).

% === Total fine calculation ===
total_fine(X, Total) :-
    all_fines(X, List),
    sum_list(List, Total).

% === Penalty check (limit = 2000) ===
over_limit(X) :-
    total_fine(X, Total),
    Total > 2000.

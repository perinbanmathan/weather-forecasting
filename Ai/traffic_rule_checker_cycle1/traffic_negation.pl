% === Facts ===
driver(mathan).
driver(ravi).
driver(anu).

helmet_violation(mathan).
signal_violation(ravi).
speed_violation(ravi).

% === Rule: general violation check ===
violation(X) :-
    helmet_violation(X);
    signal_violation(X);
    speed_violation(X).

% === Negation: Safe Driver (no violations) ===
safe_driver(X) :-
    driver(X),
    \+ violation(X).

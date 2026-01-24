% =========================================
% Traffic Rule Violation Expert System
% SWI-Prolog knowledge base
% =========================================

:- dynamic vehicle/1.
:- dynamic owner/2.
:- dynamic helmet_worn/2.
:- dynamic signal_respected/2.
:- dynamic speed/2.
:- dynamic speed_limit/2.
:- dynamic at_junction/2.
:- dynamic violation_log/3.   % violation_log(Vehicle, Type, Amount)

% -------------------------
% Base facts (sample data)
% -------------------------
vehicle(bike1).
vehicle(bike2).
vehicle(car1).

owner(bike1, john).
owner(bike2, mike).
owner(car1, alice).

% helmet_worn(Vehicle, yes/no)
helmet_worn(bike1, no).
helmet_worn(bike2, yes).

% signal_respected(Vehicle, yes/no)
signal_respected(bike1, no).
signal_respected(bike2, yes).
signal_respected(car1, yes).

% speed(Vehicle, kmph)
speed(bike1, 55).
speed(bike2, 45).
speed(car1, 85).

% speed_limit(Junction, kmph)
speed_limit(junction1, 60).
speed_limit(junction2, 40).

% vehicle at a junction
at_junction(bike1, junction1).
at_junction(bike2, junction2).
at_junction(car1, junction1).

% -------------------------
% Helper: bike detector
% -------------------------
is_bike(V) :-
    vehicle(V),
    sub_atom(V, 0, _, _, bike).

% -------------------------
% Violations (Rules)
% -------------------------

% Helmet violation: only applies to bikes
helmet_violation(V) :-
    is_bike(V),
    helmet_worn(V, no).

% Signal violation: vehicle did not respect signal at its junction
signal_violation(V) :-
    vehicle(V),
    signal_respected(V, no).

% Speed violation: compare speed at the vehicle's junction
speed_violation(V) :-
    vehicle(V),
    at_junction(V, J),
    speed(V, S),
    speed_limit(J, L),
    S > L.

% General violation enumerator (for backtracking over all)
violation(V, helmet) :- helmet_violation(V).
violation(V, signal) :- signal_violation(V).
violation(V, speed)  :- speed_violation(V).

% -------------------------
% Negation & Verification
% -------------------------

% Law-abiding vehicle: no violations
law_abiding(V) :-
    vehicle(V),
    \+ violation(V, _).

% Verify that ALL vehicles follow the speed limit (Universal Quantifier)
all_follow_speed_limits :-
    forall(vehicle(V), \+ speed_violation(V)).

% Existential: There exists some vehicle with any violation
exists_any_violation :-
    once(violation(_, _)).

% -------------------------
% Arithmetic: Fine amounts
% -------------------------
fine_amount(helmet, 500).
fine_amount(signal, 1000).
fine_amount(speed, 1500).

% Sum a list of numbers (recursion)
sum_list([], 0).
sum_list([H|T], S) :-
    sum_list(T, S1),
    S is S1 + H.

% Calculate total fine for a vehicle by collecting all its violations
total_fine(V, Total) :-
    findall(Amt, (violation(V, T), fine_amount(T, Amt)), Amounts),
    sum_list(Amounts, Total).

% Priority fine assignment (Cut): first matching rule wins
% (Example of operational priority; UI uses total_fine/2 for full sum)
priority_fine(V, 1500) :- speed_violation(V),  !.
priority_fine(V, 1000) :- signal_violation(V), !.
priority_fine(V,  500) :- helmet_violation(V), !.
priority_fine(_,    0).

% -------------------------
% List Ops & Backtracking
% -------------------------

% Collect all offenders (vehicles with at least one violation)
all_offenders(L) :-
    findall(V, (vehicle(V), violation(V, _)), Raw),
    sort(Raw, L).

% Produce a list of (ViolationType, Amount) for vehicle
violations_with_amounts(V, Pairs) :-
    findall((T,A), (violation(V, T), fine_amount(T, A)), Pairs).

% -------------------------
% Prediction (Simple Heuristic)
% If speed is within 5 of the limit, likely overspeed soon
% -------------------------
predict_speed_violation(V) :-
    vehicle(V),
    at_junction(V, J),
    speed(V, S),
    speed_limit(J, L),
    Margin is L - 5,
    S >= Margin,
    S =< L,
    format('~w is likely to overspeed soon at ~w~n', [V, J]).

% -------------------------
% I/O utilities
% -------------------------
check_vehicle :-
    write('Enter vehicle id: '), read(V),
    ( law_abiding(V) ->
        writeln('No violations found.')
    ;
        writeln('Violations:'),
        forall(violation(V, T), (write(' - '), writeln(T))),
        total_fine(V, Total),
        format('Total fine: Rs.~w~n', [Total])
    ).

% -------------------------
% Dynamic updates (runtime)
% -------------------------
set_helmet(V, Status) :-
    retractall(helmet_worn(V, _)),
    assertz(helmet_worn(V, Status)).

set_signal(V, Status) :-
    retractall(signal_respected(V, _)),
    assertz(signal_respected(V, Status)).

set_speed(V, S) :-
    retractall(speed(V, _)),
    assertz(speed(V, S)).

set_at_junction(V, J) :-
    retractall(at_junction(V, _)),
    assertz(at_junction(V, J)).

set_speed_limit(J, L) :-
    retractall(speed_limit(J, _)),
    assertz(speed_limit(J, L)).

% Log a violation (for audit trail)
log_violation(V, T) :-
    fine_amount(T, A),
    assertz(violation_log(V, T, A)).

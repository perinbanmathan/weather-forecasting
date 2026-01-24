% =================================================
% Traffic Violation Expert System - Enhanced Model
% =================================================

% --- Dynamic predicates for runtime updates
:- dynamic vehicle/2.        % vehicle(ID, Type) -> e.g., vehicle(c1, car).
:- dynamic owner/2.
:- dynamic helmet_worn/2.
:- dynamic signal_respected/2.
:- dynamic speed/2.
:- dynamic speed_limit/2.
:- dynamic at_junction/2.
:- dynamic puc_valid/2.        % puc_valid(Vehicle, yes/no)
:- dynamic overloaded/2.       % overloaded(Vehicle, yes/no)
:- dynamic correct_lane/2.     % correct_lane(Vehicle, yes/no)

% --- Base Facts (Sample Data)
vehicle(bk1, bike).
vehicle(bk2, bike).
vehicle(c1, car).
vehicle(tk1, truck).

owner(bk1, john).
owner(bk2, mike).
owner(c1, alice).
owner(tk1, john). % John owns a bike and a truck

% --- Vehicle State Facts
helmet_worn(bk1, no).
helmet_worn(bk2, yes).

signal_respected(bk1, no).
signal_respected(c1, yes).
signal_respected(tk1, no).

speed(bk1, 65).
speed(c1, 85).
speed(tk1, 75).

speed_limit(j1, 60). % Junction 1 limit is 60
speed_limit(j2, 80). % Junction 2 limit is 80 (highway)

at_junction(bk1, j1).
at_junction(c1, j2).
at_junction(tk1, j1).

puc_valid(bk1, yes).
puc_valid(c1, no).   % Pollution check expired
puc_valid(tk1, yes).

overloaded(tk1, yes). % Truck is overloaded

correct_lane(bk1, yes).
correct_lane(c1, yes).
correct_lane(tk1, no). % Truck in wrong lane

% --- Violation Rules ---

% Generic rule to get vehicle type
is_type(V, Type) :- vehicle(V, Type).

% 1. Helmet Violation (only for bikes)
violation(V, helmet) :-
    is_type(V, bike),
    helmet_worn(V, no).

% 2. Signal Violation
violation(V, signal) :-
    signal_respected(V, no).

% 3. Speeding Violation
violation(V, speed) :-
    at_junction(V, J),
    speed(V, S),
    speed_limit(J, L),
    S > L.

% 4. Pollution Check (PUC) Violation
violation(V, puc_expired) :-
    puc_valid(V, no).

% 5. Overloading Violation (only for trucks)
violation(V, overloaded) :-
    is_type(V, truck),
    overloaded(V, yes).

% 6. Lane Discipline Violation
violation(V, lane_discipline) :-
    correct_lane(V, no).

% --- Fines, Severity, and Demerit Points System ---

% fine(ViolationType, Amount, Severity, Points)
fine(helmet, 500, medium, 2).
fine(signal, 1000, high, 3).
fine(speed, 1500, high, 3).
fine(puc_expired, 2000, medium, 1).
fine(overloaded, 5000, critical, 4).
fine(lane_discipline, 750, low, 1).

% --- List, Arithmetic, and Aggregation Logic ---

% sum_points(List, Total) - Recursively sums a list of numbers
sum_points([], 0).
sum_points([H|T], Total) :-
    sum_points(T, SubTotal),
    Total is H + SubTotal.

% total_fine_for_vehicle(Vehicle, TotalFine)
total_fine_for_vehicle(V, Total) :-
    findall(Amount, (violation(V, T), fine(T, Amount, _, _)), Amounts),
    sum_list(Amounts, Total). % sum_list is from the previous model, assuming it exists

% total_points_for_vehicle(Vehicle, TotalPoints)
total_points_for_vehicle(V, Total) :-
    findall(Points, (violation(V, T), fine(T, _, _, Points)), PointsList),
    sum_points(PointsList, Total).

% --- Owner-level Logic (Aggregation across vehicles) ---

% Sum demerit points for an owner across all their vehicles
total_points_for_owner(Owner, TotalPoints) :-
    findall(P, (owner(V, Owner), total_points_for_vehicle(V, P)), PointsByVehicle),
    sum_points(PointsByVehicle, TotalPoints).

% Verification rule: check if an owner's license is at risk
license_at_risk(Owner) :-
    total_points_for_owner(Owner, TotalPoints),
    TotalPoints >= 10.  % License at risk if 10 or more points

% --- Helper & Utility Predicates ---

% Get all violations for a vehicle with details
violations_with_details(V, Details) :-
    findall(
        (Type, Amount, Severity, Points),
        (violation(V, Type), fine(Type, Amount, Severity, Points)),
        Details
    ).

% Collect all owners whose licenses are at risk
all_owners_at_risk(Owners) :-
    findall(O, license_at_risk(O), RawOwners),
    sort(RawOwners, Owners).
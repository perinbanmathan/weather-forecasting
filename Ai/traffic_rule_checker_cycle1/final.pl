% === Facts ===
% violation(Driver, [List of Violations])
% Priority order: helmet > signal > speeding > overspeed > drunk > seatbelt > none

violation(mathan, [helmet, speeding, signal]).
violation(arun, [seatbelt, helmet]).
violation(kumar, [signal]).
violation(surya, [helmet, overspeed, drunk]).
violation(priya, [none]).

% === CUT OPERATION ===
% Rule: Only report the first violation in priority order

priority_violation(Driver, helmet) :-
    violation(Driver, List),
    member(helmet, List), !.

priority_violation(Driver, signal) :-
    violation(Driver, List),
    member(signal, List), !.

priority_violation(Driver, speeding) :-
    violation(Driver, List),
    member(speeding, List), !.

priority_violation(Driver, overspeed) :-
    violation(Driver, List),
    member(overspeed, List), !.

priority_violation(Driver, drunk) :-
    violation(Driver, List),
    member(drunk, List), !.

priority_violation(Driver, seatbelt) :-
    violation(Driver, List),
    member(seatbelt, List), !.

priority_violation(Driver, none) :-
    violation(Driver, List),
    member(none, List), !.

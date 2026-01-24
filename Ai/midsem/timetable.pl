% ---------- Facts ----------
teacher(ram, maths).
teacher(seetha, physics).
teacher(raja, chemistry).
teacher(lakshmi, computer_science).

room(r101).
room(r102).

day(mon).
day(tue).
day(wed).
day(thu).
day(fri).

slot(1).
slot(2).
slot(3).
slot(4).
slot(5).
slot(6).
slot(7).
slot(8).

% course(CourseID, Subject, SessionsPerWeek)
course(maths1, maths, 3).
course(phy1, physics, 2).
course(chem1, chemistry, 2).
course(cs1, computer_science, 3).

% timetable(Day, Slot, Teacher, Course, Room) will be asserted dynamically

:- dynamic timetable/5.

% ---------- Rules ----------

% check conflicts: a slot is invalid if the same teacher or same room already taken
conflict(Day, Slot, Teacher, _, _) :-
    timetable(Day, Slot, Teacher, _, _), !.

conflict(Day, Slot, _, _, Room) :-
    timetable(Day, Slot, _, _, Room), !.

% assign a course session to teacher, day, slot, and room
assign(Course, Teacher, Day, Slot, Room) :-
    course(Course, Spec, _),
    teacher(Teacher, Spec),
    day(Day),
    slot(Slot),
    room(Room),
    \+ conflict(Day, Slot, Teacher, Course, Room).

% recursively allocate sessions for a course
% stop when sessions are done
allocate_sessions(_, _, 0) :- !.

allocate_sessions(Course, Spec, N) :-
    once(assign(Course, Teacher, Day, Slot, Room)),   % pick ONE slot only
    assertz(timetable(Day, Slot, Teacher, Course, Room)),
    N1 is N - 1,
    allocate_sessions(Course, Spec, N1).


% generate timetable for all courses
generate_timetable([]).
generate_timetable([course(C,Spec,S)|Rest]) :-
    allocate_sessions(C, Spec, S),
    generate_timetable(Rest).

% query to reset timetable and generate fresh schedule
make_timetable :-
    retractall(timetable(_,_,_,_,_)),
    findall(course(C,S,Num), course(C,S,Num), Courses),
    generate_timetable(Courses).

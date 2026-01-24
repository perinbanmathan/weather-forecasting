% --------------------------
% Courses and Faculty
% --------------------------
course(cs225, 'Artificial Intelligence', 'Dr. P. Dharanya Devi').
course(cs226, 'Parallel and Distributed Systems', 'Dr. C. Kalaiarasy').
course(cs227, 'Data Science Essentials', 'Dr. F. Sagayaraj Francis').
course(csy09, 'Cloud Computing', 'Dr. J. Kumaran').
course(csy11, 'Business Intelligence', 'Dr. P. Dharanya Devi').
course(csy10, 'Machine Learning', 'Dr. K. Sathiamurthy').
course(cs228, 'AI Lab', 'Dr. K. Sathiamurthy').
course(cs229, 'Seminar', 'Dr. M. Thirumaran').
course(cs230, 'Professional Ethics', 'Dr. Ka. Selvaradjou').
course(h_m, 'Honors/Minor', 'N/A').
course(oec, 'Open Elective', 'N/A').
course(tnp, 'Training & Placement', 'N/A').

% --------------------------
% Time Slots & Days
% --------------------------
slot('9:00-9:50').
slot('9:50-10:40').
slot('10:50-11:40').
slot('11:40-12:30').
slot('1:30-2:20').
slot('2:20-3:10').
slot('3:10-4:00').
slot('4:00-4:50').

day(mon). day(tue). day(wed). day(thu). day(fri).

% --------------------------
% Dynamic Timetable
% --------------------------
:- dynamic timetable/3.

% Initial timetable facts
timetable(mon, '9:00-9:50', h_m).
timetable(mon, '9:50-10:40', h_m).
timetable(mon, '10:50-11:40', cs228).
timetable(mon, '11:40-12:30', cs228).
timetable(mon, '1:30-2:20', oec).
timetable(mon, '2:20-3:10', csy11).
timetable(mon, '3:10-4:00', csy10).
timetable(mon, '4:00-4:50', cs225).

timetable(tue, '9:00-9:50', cs225).
timetable(tue, '9:50-10:40', csy10).
timetable(tue, '10:50-11:40', cs227).
timetable(tue, '11:40-12:30', h_m).
timetable(tue, '1:30-2:20', csy09).
timetable(tue, '2:20-3:10', cs228).
timetable(tue, '3:10-4:00', cs228).
% free slot: tue, '4:00-4:50'

timetable(wed, '9:00-9:50', oec).
timetable(wed, '9:50-10:40', csy09).
timetable(wed, '10:50-11:40', csy11).
timetable(wed, '11:40-12:30', cs226).
timetable(wed, '1:30-2:20', h_m).
timetable(wed, '2:20-3:10', cs227).
timetable(wed, '3:10-4:00', cs226).
timetable(wed, '4:00-4:50', cs226).

timetable(thu, '9:00-9:50', cs227).
timetable(thu, '9:50-10:40', csy09).
timetable(thu, '10:50-11:40', cs226).
timetable(thu, '11:40-12:30', cs225).
timetable(thu, '1:30-2:20', cs230).
timetable(thu, '2:20-3:10', cs228).
timetable(thu, '3:10-4:00', cs228).
% free slot: thu, '4:00-4:50'

timetable(fri, '9:00-9:50', cs227).
timetable(fri, '9:50-10:40', csy10).
timetable(fri, '10:50-11:40', csy11).
timetable(fri, '11:40-12:30', h_m).
timetable(fri, '1:30-2:20', oec).
timetable(fri, '2:20-3:10', tnp).
timetable(fri, '3:10-4:00', tnp).
timetable(fri, '4:00-4:50', tnp).

% ==================================================
% QUERIES
% ==================================================

% Teacher at a given slot
teacher_at(Day, Slot, Teacher) :-
    timetable(Day, Slot, Course),
    course(Course, _, Teacher),
    Teacher \= 'N/A'.

% Teacher free at a given slot
teacher_free(Teacher, Day, Slot) :-
    slot(Slot),
    day(Day),
    \+ teacher_at(Day, Slot, Teacher).

% Get all free slots of a teacher
teacher_all_free(Teacher, Day, Slot) :-
    teacher_free(Teacher, Day, Slot).

% Modify timetable: update a course in (Day, Slot)
update_timetable(Day, Slot, NewCourse) :-
    retractall(timetable(Day, Slot, _)),
    assertz(timetable(Day, Slot, NewCourse)).

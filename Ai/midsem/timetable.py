from pyswip import Prolog
prolog = Prolog()
prolog.consult("timetable.pl")


courses = list(prolog.query("findall(course(C,Spec,S), course(C,Spec,S), Courses)"))
print("Courses:", courses)


print("\nGenerating timetable...\n")
list(prolog.query("generate_timetable([course(maths1, maths, 3), course(phy1, physics, 2), course(chem1, chemistry, 2), course(cs1, computer_science, 3)])"))


print("\nFinal Timetable:")
for res in prolog.query("timetable(Day, Slot, Teacher, Course, Room)"):
    print(res)

from pyswip import Prolog
import matplotlib.pyplot as plt

# Setup Prolog engine
prolog = Prolog()

# --- Define Facts ---
facts = [
    "passed(john, math)", "passed(john, physics)",
    "passed(amy, math)", "passed(amy, chemistry)",
    "passed(rita, math)", "passed(rita, physics)", "passed(rita, chemistry)",

    "prerequisite(engineering, math)",
    "prerequisite(physics_course, math)",
    "prerequisite(ai_course, engineering)",
    "prerequisite(chemistry_course, math)",

    ":- dynamic(passed/2)"
]

# --- Define Rules ---
rules = [
    "eligible(S, C) :- prerequisite(C, P), passed(S, P)",
    "eligible(S, C) :- prerequisite(C, P), eligible(S, P)",
    "not_eligible(S, C) :- \\+ eligible(S, C)",
    "student_courses(S, Cs) :- findall(C, passed(S, C), Cs)",
    "recommend_course(S, ai_course) :- eligible(S, ai_course), !",
    "recommend_course(_, general_course)"
]

# Load facts and rules into Prolog
for line in facts + rules:
    prolog.assertz(line)

# --- Query and Output ---
students = ['john', 'amy', 'rita']
courses = ['engineering', 'ai_course', 'physics_course', 'chemistry_course']

eligibility_matrix = {}

for student in students:
    print(f"\n🧑 Student: {student}")
    eligibility_matrix[student] = []

    for course in courses:
        result = list(prolog.query(f"eligible({student}, {course})"))
        if result:
            print(f"✅ Eligible for: {course}")
            eligibility_matrix[student].append(course)
        else:
            print(f"❌ Not eligible for: {course}")

    # Recommendation
    recommendation = list(prolog.query(f"recommend_course({student}, X)"))[0]['X']
    print(f"🎓 Recommended Course: {recommendation}")

# --- Visualization using matplotlib ---
fig, ax = plt.subplots()
colors = ['skyblue', 'lightgreen', 'salmon']
for i, student in enumerate(students):
    ax.barh(student, len(eligibility_matrix[student]), color=colors[i])

ax.set_xlabel("Number of Eligible Courses")
ax.set_title("Student Eligibility Analysis")
plt.show()

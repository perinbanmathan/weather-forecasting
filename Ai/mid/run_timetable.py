from pyswip import Prolog
from prettytable import PrettyTable

# Load Prolog file
prolog = Prolog()
prolog.consult("timetable.pl")

days = {"monday": "mon", "mon": "mon",
        "tuesday": "tue", "tue": "tue",
        "wednesday": "wed", "wed": "wed",
        "thursday": "thu", "thu": "thu",
        "friday": "fri", "fri": "fri"}

slots = ["9:00-9:50", "9:50-10:40", "10:50-11:40", "11:40-12:30",
         "1:30-2:20", "2:20-3:10", "3:10-4:00", "4:00-4:50"]

def print_timetable():
    table = PrettyTable()
    table.field_names = ["Day"] + slots
    for day in ["mon", "tue", "wed", "thu", "fri"]:
        row = [day.upper()]
        for slot in slots:
            q = list(prolog.query(f"timetable({day}, '{slot}', C)"))
            if q:
                course = q[0]["C"]
                title_q = list(prolog.query(f"course({course}, Title, _)"))
                if title_q:
                    row.append(title_q[0]["Title"])
                else:
                    row.append(course)
            else:
                row.append("---")
        table.add_row(row)
    print("\n=== Current Timetable ===")
    print(table)

def show_teacher_free(teacher):
    print(f"\n=== Free Periods for {teacher} ===")
    for day in ["mon", "tue", "wed", "thu", "fri"]:
        free_slots = list(prolog.query(f"teacher_all_free('{teacher}', {day}, S)"))
        if free_slots:
            slots_list = [s["S"] for s in free_slots]
            print(f"{day.upper()}: {', '.join(slots_list)}")
        else:
            print(f"{day.upper()}: No free slots")

def update_timetable(day_input, slot, course):
    # Normalize day (allow full names like 'monday')
    if day_input.lower() not in days:
        print("❌ Invalid day! Use mon/tue/wed/thu/fri or full name.")
        return
    day = days[day_input.lower()]

    # Run Prolog update
    list(prolog.query(f"update_timetable({day}, '{slot}', {course})"))

    print(f"\n✅ Updated {day.upper()} {slot} -> {course}")
    print_timetable()

# -----------------------------
# Interactive Menu
# -----------------------------
if __name__ == "__main__":
    while True:
        print("\nMenu:")
        print("1. Show Timetable")
        print("2. Show Teacher Free Periods")
        print("3. Update Timetable")
        print("4. Exit")
        choice = input("Enter choice: ")

        if choice == "1":
            print_timetable()

        elif choice == "2":
            teacher = input("Enter teacher name (case-sensitive): ")
            show_teacher_free(teacher)

        elif choice == "3":
            day = input("Enter day (mon/tue/wed/thu/fri or full name): ")
            slot = input("Enter slot (e.g., 9:00-9:50): ")
            course = input("Enter course code (e.g., cs225, cs228): ")
            update_timetable(day, slot, course)

        elif choice == "4":
            print("Exiting...")
            break

        else:
            print("Invalid choice. Try again.")

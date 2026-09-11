import random

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]

def generate_timetable(theory_subjects, lab_subjects, busy_slots=None):
    # Initialize timetable grid
    timetable = {day: {p: "" for p in PERIODS} for day in DAYS}
    
    # 1. Block Busy Slots from Class 1 (Imported) to avoid confusion
    if busy_slots:
        for day, p_list in busy_slots.items():
            for p in p_list:
                
                if p in timetable[day]:
                    timetable[day][p] = "BUSY (Class 1)"

    # 2. Prepare Pools
    theory_pool = []
    for name, hours in theory_subjects:
        theory_pool.extend([name.strip()] * int(hours))
    
    lab_pool = []
    for name, hours in lab_subjects:
        lab_pool.extend([name.strip()] * (int(hours) // 2))

    random.shuffle(theory_pool)
    random.shuffle(lab_pool)

    # 3. Lab Rule: 3 Days, 2 Sessions, NO Monday Morning
    lab_days = random.sample(DAYS, 4)
    for day in lab_days:
        
        slots = [
    ("P1", "P2"),
    ("P3", "P4"),
    ("P6", "P7"),
    
]
        if day == "Monday": slots = [s for s in slots if s != ("P1", "P2")]
        
        available = [s for s in slots if timetable[day][s[0]] == "" and timetable[day][s[1]] == ""]
        for _ in range(2):
            if lab_pool and available:
                lab_name = lab_pool.pop(0)
                chosen = random.choice(available)
                available.remove(chosen)
                timetable[day][chosen[0]] = f"{lab_name} (Lab)"
                timetable[day][chosen[1]] = f"{lab_name} (Lab)"

    # 4. Library Rule: 1 Hour Total
    lib_assigned = False
    for day in random.sample(DAYS, 5):
        if lib_assigned: break
        for p in reversed(PERIODS):
            if timetable[day][p] == "":
                timetable[day][p] = "Library"
                lib_assigned = True
                break

    # 5. Fill Theory - Anti-Vertical & Anti-Horizontal Repetition
    for day in DAYS:
        for p in PERIODS:
            if timetable[day][p] == "":
                if theory_pool:
                    # Get subjects already used TODAY (Horizontal Check)
                    subjects_today = [timetable[day][slot] for slot in PERIODS if timetable[day][slot]]
                    
                    # Get subjects already used in this PERIOD on other days (Vertical Check)
                    subjects_this_period = [timetable[d][p] for d in DAYS if timetable[d][p]]

                    found = False
                    # Priority 1: Subject not used today AND not used in this vertical column
                    for i, sub in enumerate(theory_pool):
                        if sub not in subjects_today and sub not in subjects_this_period:
                            timetable[day][p] = theory_pool.pop(i)
                            found = True
                            break
                    
                    # Priority 2: Subject not used today (allows vertical if necessary to fill hours)
                    if not found:
                        for i, sub in enumerate(theory_pool):
                            if sub not in subjects_today:
                                timetable[day][p] = theory_pool.pop(i)
                                found = True
                                break
                    
                    # Priority 3: Forced placement to ensure all input hours are met
                    if not found and theory_pool:
                        timetable[day][p] = theory_pool.pop(0)
                else:
                    timetable[day][p] = "Free"

    return timetable
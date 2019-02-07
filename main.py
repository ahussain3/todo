from typing import Dict, List

import os
import sys
import datetime
from subprocess import run
from enum import Enum

ROOT_DIR = "/Users/awais/Dropbox (Personal)/Todos/"
DATE_FORMAT = '%Y-%m-%d'

COMPLETED_MARKERS = ["[x]", "[X]"]
UNCOMPLETED_MARKERS = ["-", "*", "[]", "[ ]", "->"]

class State(Enum):
    TODAY = "TODAY"
    THIS_WEEK = "THIS WEEK"
    THIS_MONTH = "THIS MONTH"
    THIS_QUARTER = "THIS QUARTER"
    THIS_YEAR = "THIS YEAR"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"

class Section(object):
    heading: State = None
    # used to specify which
    last: str = None
    def matches(dt: datetime) -> bool:
        raise NotImplementedError


class Day(Section):
    heading = State.TODAY
    last = "yesterday"

    def matches(dt: datetime) -> bool:
        today = datetime.datetime.now()
        return (
            dt.day == today.day
            and dt.month == today.month
            and dt.year == today.year
        )

class Week(Section):
    heading = State.THIS_WEEK
    last = "last week"

    def matches(dt: datetime) -> bool:
        today = datetime.datetime.now()
        return (
            dt.isocalendar()[1] == today.isocalendar()[1]
            and dt.year == today.year
        )

class Month(Section):
    heading = State.THIS_MONTH
    last = "last month"

    def matches(dt: datetime) -> bool:
        today = datetime.datetime.now()
        return dt.month == today.month and dt.year == today.year

class Quarter(Section):
    heading = State.THIS_QUARTER
    last = "last quarter"

    def matches(dt: datetime) -> bool:
        today = datetime.datetime.now()
        groups = [[1,2,3], [4,5,6], [7,8,9], [10,11,12]]
        return (
            groups.index(next(i for i in groups if dt.month in i)) == groups.index(next(i for i in groups if today.month in i))
            and dt.year == today.year
        )

class Year(Section):
    heading = State.THIS_YEAR
    last = "last year"

    def matches(dt: datetime) -> bool:
        today = datetime.datetime.now()
        return dt.year == today.year

TIME_PERIODS = [Day, Week, Month, Quarter, Year]
TODOS = {state.value:[] for state in State}


def create_file(filename_stub: str, todos: Dict[str, List[str]]) -> None:
    with open(os.path.join(ROOT_DIR, filename_stub + ".md"), "w+") as f:
        f.write(f"# TODO FOR {filename_stub}\n\n")

        for heading, tasks in todos.items():
            f.write(f'# {heading}\n')
            for task in tasks:
                output = task
                if heading == State.COMPLETED.value:
                    output = COMPLETED_MARKERS[0] + " " + task.lstrip("".join(COMPLETED_MARKERS + UNCOMPLETED_MARKERS))
                f.write(f'{output}\n')
            f.write('\n')


def add_task(state: State, task: str) -> None:
    if not TODOS.get(state.value):
        TODOS[state.value] = []

    TODOS[state.value].append(task)


def get_task_state(task: str, section: Section) -> State:
    if any(task.startswith(marker) for marker in COMPLETED_MARKERS):
        return State.COMPLETED

    print(f'''Did you complete this {section.last}?
    <enter> = completed
    d = dropped / abandoned / delegated
    t = defer to today
    w = defer to this week
    m = defer to this month
    q = defer to this quarter
    y = defer to this year
    ''')
    response = input(task + '\n')
    while response is not None:
        if response == '':
            return State.COMPLETED
        elif response == 't':
            return State.TODAY
        elif response == 'w':
            return State.THIS_WEEK
        elif response == 'm':
            return State.THIS_MONTH
        # elif response == 'q':
        #     return State.THIS_QUARTER
        elif response == 'y':
            return State.THIS_YEAR
        elif response == 'd':
            return State.DROPPED
        else:
            print("I didn't understand that, please try again")
            response = input(task + '\n')


def read_section(filepath: str, section: Section, to_review: bool) -> List[str]:
    with open(filepath, "r") as f:
        reading = False
        for line in f:
            if reading == True and line == "\n":
                break
            if reading:
                task = line.strip()
                if to_review:
                    state = get_task_state(task, section)
                else:
                    state = section.heading

                add_task(state, task)
            if line.strip() == f"# {section.heading.value}":
                reading = True


def main():
    today_date = datetime.datetime.now().strftime(DATE_FORMAT)
    today_filepath = os.path.join(ROOT_DIR, today_date + ".md")

    if os.path.exists(today_filepath):
        # open the file for today in vim
        exit()

    existing_files = [fname for fname in os.listdir(ROOT_DIR) if fname.endswith(".md")]
    if len(existing_files) == 0:
        create_file(today_date, TODOS)
        exit()

    most_recent_date_str = sorted(existing_files)[0].split(".")[0]
    most_recent_date = datetime.datetime.strptime(most_recent_date_str, DATE_FORMAT)

    for tp in TIME_PERIODS:
        tasks = read_section(
            filepath=os.path.join(ROOT_DIR, most_recent_date_str + ".md"),
            section=tp,
            to_review=not tp.matches(most_recent_date),
        )

    create_file(today_date, TODOS)

if __name__ == '__main__':
    main()
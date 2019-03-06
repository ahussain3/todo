from typing import Dict, List, NamedTuple

import os
import sys
import datetime
from subprocess import run
from enum import Enum

ROOT_DIR = "~/todo"
DATE_FORMAT = '%Y-%m-%d'

COMPLETED_MARKERS = ["[x]", "[X]"]
UNCOMPLETED_MARKERS = ["-", "*", "[]", "[ ]", "->"]


# MODELS

class State(Enum):
    TODAY = "TODAY"
    ANYTIME = "ANYTIME"
    THIS_WEEK = "THIS WEEK"
    THIS_MONTH = "THIS MONTH"
    THIS_QUARTER = "THIS QUARTER"
    THIS_YEAR = "THIS YEAR"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"

class Section(object):
    heading: State = None
    # used to specify the language we should use when referring to the last week/month etc.
    last: str = None

    # True if the date specified is within the current time period
    def matches(dt: datetime.datetime) -> bool:
        raise NotImplementedError

class Action(NamedTuple):
    command: str
    label: str
    state: State

# TIME PERIODS

class Day(Section):
    heading = State.TODAY
    last = "yesterday"

    def matches(dt: datetime.datetime) -> bool:
        today = datetime.datetime.now()
        return (
            dt.day == today.day
            and dt.month == today.month
            and dt.year == today.year
        )

class Anytime(Section):
    heading = State.ANYTIME
    last = "yet"

    def matches(dt: datetime.datetime) -> bool:
        return False

class Week(Section):
    heading = State.THIS_WEEK
    last = "last week"

    def matches(dt: datetime.datetime) -> bool:
        today = datetime.datetime.now()
        return (
            dt.isocalendar()[1] == today.isocalendar()[1]
            and dt.year == today.year
        )

class Month(Section):
    heading = State.THIS_MONTH
    last = "last month"

    def matches(dt: datetime.datetime) -> bool:
        today = datetime.datetime.now()
        return dt.month == today.month and dt.year == today.year

class Quarter(Section):
    heading = State.THIS_QUARTER
    last = "last quarter"

    def matches(dt: datetime.datetime) -> bool:
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

# BASIC CONFIG / GLOBALS

TIME_PERIODS = [Day, Anytime, Week, Month, Quarter, Year]
TODOS = {state.value:[] for state in State}
ACTIONS = [
    Action("", "<enter> = completed", State.COMPLETED),
    Action("t", "t = defer to today", State.TODAY),
    Action("a", "a = defer to anytime", State.ANYTIME),
    Action("w", "w = defer to this week", State.THIS_WEEK),
    Action("m", "m = defer to this month", State.THIS_MONTH),
    Action("q", "q = defer to this quarter", State.THIS_QUARTER),
    Action("y", "y = defer to this year", State.THIS_YEAR),
    Action("d", "d = dropped / abandoned / delegated", State.DROPPED),
]

# BUSINESS LOGIC

def get_action(command: str) -> Action:
    actions = [action for action in ACTIONS if action.command == command]
    if not actions:
        return None
    if len(actions) > 1:
        raise Exception("Multiple actions with the same command.")
    return actions[0]

def get_available_commands() -> str:
    commands = ", ".join([action.command for action in ACTIONS])
    return f"[{commands}]"

def generate_instructions() -> str:
    return "\n".join([action.label for action in ACTIONS])

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


def is_task_completed(task: str) -> bool:
    return any(task.startswith(marker) for marker in COMPLETED_MARKERS)

def get_task_input(task: str, section: Section) -> str:
    available_commands = get_available_commands()

    print(f'{task}')
    return input(f"Did you complete this {section.last}? {available_commands}\n")


def review_task(task: str, section: Section) -> State:
    if is_task_completed(task):
        return State.COMPLETED

    response = get_task_input(task, section)

    while response is not None:
        action = get_action(response)
        instructions = generate_instructions()

        if action:
            return action.state
        elif response == "help":
            print(f"{instructions}\n")
            response = get_task_input(task, section)
        else:
            print(f"I didn't understand that, please try again\n{instructions}\n")
            response = get_task_input(task, section)


def read_section(filepath: str, section: Section, to_review: bool) -> List[str]:
    with open(filepath, "r") as f:
        reading = False
        for line in f:
            if reading == True and line == "\n":
                break
            if reading:
                task = line.strip()
                if to_review:
                    state = review_task(task, section)
                elif is_task_completed(task):
                    state = State.COMPLETED
                else:
                    state = section.heading

                add_task(state, task)
            if line.strip() == f"# {section.heading.value}":
                reading = True


def main():
    today_date = datetime.datetime.now().strftime(DATE_FORMAT)
    today_filepath = os.path.join(ROOT_DIR, today_date + ".md")

    if os.path.exists(today_filepath):
        # will later use vim to open the file for today
        exit()

    existing_files = [fname for fname in os.listdir(ROOT_DIR) if fname.endswith(".md")]
    if len(existing_files) == 0:
        create_file(today_date, TODOS)
        exit()

    most_recent_date_str = sorted(existing_files)[-1].split(".")[0]
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
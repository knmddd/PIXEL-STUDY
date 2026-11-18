"""PixelStudy tasks and Data Structures & Algorithms.

START STUDYING HERE! The interface in ui.py uses these simple operations.
Module 3: List     | Module 4: Stack     | Module 5: Queue
Module 9: Linear search and Merge sort
"""

import copy
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path


QUADRANTS = (
    'Urgent & Important',
    'Important, Not Urgent',
    'Urgent, Not Important',
    'Not Urgent, Not Important',
)


def quadrant_of(urgent, important):
    if urgent and important:
        return 0
    if important:
        return 1
    if urgent:
        return 2
    return 3


class Task:
    def __init__(self, title, subject, due_at, urgent=False,
                 important=False, completed=False, id=None):
        self.title = title
        self.subject = subject
        self.due_at = due_at  # Example: '2026-11-25 14:30'
        self.urgent = urgent
        self.important = important
        self.completed = completed
        self.id = id or uuid.uuid4().hex

    @property
    def quadrant(self):
        return quadrant_of(self.urgent, self.important)

    @property
    def due(self):
        return datetime.strptime(self.due_at, '%Y-%m-%d %H:%M')

    def to_dict(self):
        """Turn a task into a dictionary so JSON can save it."""
        return {
            'title': self.title,
            'subject': self.subject,
            'due_at': self.due_at,
            'urgent': self.urgent,
            'important': self.important,
            'completed': self.completed,
            'id': self.id,
        }


def merge_sort(tasks):
    if len(tasks) <= 1:
        return tasks[:]

    middle = len(tasks) // 2
    left = merge_sort(tasks[:middle])
    right = merge_sort(tasks[middle:])

    sorted_tasks = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        if left[i].due_at <= right[j].due_at:
            sorted_tasks.append(left[i])
            i += 1
        else:
            sorted_tasks.append(right[j])
            j += 1

    sorted_tasks.extend(left[i:])
    sorted_tasks.extend(right[j:])
    return sorted_tasks

class UndoStack:
    def __init__(self):
        self.items = []

    def push(self, tasks):
        self.items.append(copy.deepcopy(tasks))

    def pop(self):
        if len(self.items) == 0:
            return None
        return self.items.pop()


class ReminderQueue:
    def __init__(self):
        self.items = []

    def enqueue(self, task):
        self.items.append(task)

    def dequeue(self):
        if len(self.items) == 0:
            return None
        return self.items.pop(0)

    def __len__(self):
        return len(self.items)


def save_path():
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or Path.home())
        return base / 'PixelStudy' / 'tasks.json'
    return Path.home() / '.pixelstudy' / 'tasks.json'


class TaskStore:
    """Module 3: the task list, with simple add/edit/delete operations."""

    def __init__(self, path=None):
        self.path = Path(path) if path else save_path()
        self.tasks = []  # The LIST of all tasks (Module 3)
        self.undo = UndoStack()

        if path is None and not self.path.exists():
            if os.name == 'nt':
                old_file = Path(os.environ.get('APPDATA') or Path.home()) / 'StudyBloom' / 'tasks.json'
            else:
                old_file = Path.home() / '.studybloom' / 'tasks.json'
            if old_file.exists():
                self.path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old_file, self.path)

        self.load()

    def load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            rows = data['tasks'] if isinstance(data, dict) else data
            self.tasks = []
            for row in rows:
                try:
                    task = Task(**row)
                    self.tasks.append(task)
                except (TypeError, ValueError, KeyError):
                    continue
        except (OSError, ValueError, TypeError, KeyError):
            self.tasks = []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = [task.to_dict() for task in self.tasks]
        text = json.dumps({'tasks': rows}, ensure_ascii=False, indent=2)
        temporary_file = self.path.with_suffix('.tmp')
        temporary_file.write_text(text, encoding='utf-8')
        temporary_file.replace(self.path)

    def add(self, task):
        self.undo.push(self.tasks)
        self.tasks.append(task)
        self.save()

    def get(self, task_id):
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def edit(self, task_id, **changes):
        task = self.get(task_id)
        if task is None:
            return False
        self.undo.push(self.tasks)
        for name in ('title', 'subject', 'due_at', 'urgent', 'important', 'completed'):
            if name in changes:
                setattr(task, name, changes[name])
        self.save()
        return True

    def remove(self, task_id):
        if self.get(task_id) is None:
            return False
        self.undo.push(self.tasks)
        self.tasks = [task for task in self.tasks if task.id != task_id]
        self.save()
        return True

    def undo_last(self):
        previous_tasks = self.undo.pop()
        if previous_tasks is None:
            return False
        self.tasks = previous_tasks
        self.save()
        return True

    def filtered_sorted(self, quadrant):
        chosen = [task for task in self.tasks if task.quadrant == quadrant]
        return merge_sort(chosen)

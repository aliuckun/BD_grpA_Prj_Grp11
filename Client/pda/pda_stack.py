# pda/pda_stack.py

class PDA:
    def __init__(self):
        self.stack = []

    def push(self, error):
        print(f"[PDA] PUSH → {error}")
        self.stack.append(error)

    def pop(self):
        if self.stack:
            removed = self.stack.pop()
            print(f"[PDA] POP → {removed}")
            return removed
        else:
            print("[PDA] Stack is already empty.")
            return None

    def peek(self):
        return self.stack[-1] if self.stack else None

    def is_empty(self):
        return len(self.stack) == 0

    def clear(self):
        print("[PDA] Stack cleared.")
        self.stack = []

    def get_stack(self):
        return list(reversed(self.stack))  # Son hata üstte görünsün

    def contains(self, error_msg):
        return error_msg in self.stack

# fsm/state_machine.py

class State:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<State: {self.name}>"


class Transition:
    def __init__(self, source_state, trigger, destination_state):
        self.source = source_state
        self.trigger = trigger
        self.destination = destination_state

    def __repr__(self):
        return f"<{self.source.name} --[{self.trigger}]--> {self.destination.name}>"


class StateMachine:
    def __init__(self, name="FSM"):
        self.name = name
        self.states = {}
        self.transitions = []
        self.current_state = None
        self.last_valid_state = None  # FSM'in hata öncesi durumunu tutar

    def add_state(self, state_name):
        state = State(state_name)
        self.states[state_name] = state
        return state

    def set_initial_state(self, state_name):
        self.current_state = self.states.get(state_name)
        if not self.current_state:
            raise ValueError(f"Initial state '{state_name}' not found.")

    def add_transition(self, source, trigger, destination):
        source_state = self.states[source]
        destination_state = self.states[destination]
        self.transitions.append(Transition(source_state, trigger, destination_state))

    def trigger(self, event):
        # Eğer mevcut state Error ve gelen event error_occurred ise hiçbir şey yapmadan devam
        if self.current_state.name == "Error" and event == "error_occurred":
            print(f"[FSM] Error durumundayken yeni bir hata event'i alındı: {event}. FSM geçişi yapılmadı.")
            return

        for transition in self.transitions:
            if transition.source == self.current_state and transition.trigger == event:
                print(f"[FSM] {self.current_state.name} --[{event}]--> {transition.destination.name}")
                self.last_valid_state = self.current_state
                self.current_state = transition.destination
                return
        print(f"[FSM] No valid transition from '{self.current_state.name}' on event '{event}'.")

    def get_state(self):
        return self.current_state.name if self.current_state else None

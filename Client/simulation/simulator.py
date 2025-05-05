# simulation/simulator.py

from fsm.state_machine import StateMachine
from fsm.loader import load_fsm_from_xml
from pda.loader import load_errors_from_xml
from pda.pda_stack import PDA

class Simulator:
    def __init__(self):
        self.fsm = StateMachine("ISO 15118 + OCPP FSM")
        self.pda = PDA()
        self.previous_state_before_error = None
        self.error_rules = {}
        self.setup_fsm()
        self.load_error_rules()

    def setup_fsm(self):
        load_fsm_from_xml("config/fsm_states.xml", self.fsm)

    def load_error_rules(self):
        self.error_rules = load_errors_from_xml("config/pda_errors.xml")

    def get_error_rules(self):
        return self.error_rules

    def get_error_types(self):
        return list(self.error_rules.keys())

    def trigger_event(self, event):
        if not self.pda.is_empty():
            print(f"[Simulator] Hata çözülmeden '{event}' tetiklenemez. PDA stack boş değil.")
            print(f"[PDA] Aktif Hatalar: {self.pda.get_stack()}")
            return
        self.fsm.trigger(event)

    def simulate_error(self, error_msg):
        if self.fsm.get_state() != "Error":
            self.previous_state_before_error = self.fsm.get_state()
        self.pda.push(error_msg)
        self.fsm.trigger("error_occurred")

    def resolve_error(self):
        self.pda.pop()
        if self.pda.is_empty():
            print("[Simulator] Hatalar çözüldü, FSM geçişleri yeniden aktif.")
            if self.fsm.get_state() == "Error" and self.previous_state_before_error:
                print(f"[FSM] Error durumundan geri dönülüyor → {self.previous_state_before_error}")
                self.fsm.current_state = self.fsm.states[self.previous_state_before_error]
                self.previous_state_before_error = None

    def reset_errors(self):
        self.pda.clear()
        print("[Simulator] Tüm hatalar temizlendi.")

    def get_current_state(self):
        return self.fsm.get_state()

def run_simulation():
    sim = Simulator()

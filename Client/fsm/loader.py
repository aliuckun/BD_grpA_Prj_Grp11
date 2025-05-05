# fsm/loader.py

import xml.etree.ElementTree as ET


def load_fsm_from_xml(filepath, state_machine):
    tree = ET.parse(filepath)
    root = tree.getroot()

    # 1. Tüm durumları ekle
    for state_elem in root.findall("state"):
        state_name = state_elem.get("name")
        state_machine.add_state(state_name)

    # 2. Başlangıç durumu olarak ilk durumu al (manuel setlenebilir istenirse)
    first_state = root.find("state").get("name")
    state_machine.set_initial_state(first_state)

    # 3. Tüm geçişleri ekle
    for transition_elem in root.findall("transition"):
        from_state = transition_elem.get("from")
        trigger = transition_elem.get("trigger")
        to_state = transition_elem.get("to")

        state_machine.add_transition(from_state, trigger, to_state)

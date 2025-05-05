# pda/loader.py

import xml.etree.ElementTree as ET

def load_errors_from_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()

    error_dict = {}

    for error_node in root.findall("error"):
        message = error_node.get("message")
        states = [state.text for state in error_node.find("validStates").findall("state")]
        error_dict[message] = states

    return error_dict

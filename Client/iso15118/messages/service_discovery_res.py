from lxml import etree

def generate_service_discovery_res(session_id, response_code, service_list):
    ns = "urn:iso:15118:2:2013:MsgDataTypes"

    root = etree.Element("{%s}ServiceDiscoveryRes" % ns, nsmap={None: ns})

    session_elem = etree.SubElement(root, "{%s}SessionID" % ns)
    session_elem.text = session_id

    code_elem = etree.SubElement(root, "{%s}ResponseCode" % ns)
    code_elem.text = response_code

    service_list_elem = etree.SubElement(root, "{%s}MatchedServiceList" % ns)
    for service in service_list:
        service_elem = etree.SubElement(service_list_elem, "{%s}Service" % ns)

        id_elem = etree.SubElement(service_elem, "{%s}ServiceID" % ns)
        id_elem.text = str(service["id"])

        name_elem = etree.SubElement(service_elem, "{%s}ServiceName" % ns)
        name_elem.text = service["name"]

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

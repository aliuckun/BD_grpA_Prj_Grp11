from lxml import etree

def generate_service_discovery_req(session_id, services):
    ns = "urn:iso:15118:2:2013:MsgDataTypes"
    nsmap = {None: ns}

    root = etree.Element("{%s}ServiceDiscoveryReq" % ns, nsmap=nsmap)

    # SessionID
    session_elem = etree.SubElement(root, "{%s}SessionID" % ns)
    session_elem.text = session_id

    # SupportedServiceList
    service_list_elem = etree.SubElement(root, "{%s}SupportedServiceList" % ns)

    for service_id, service_name in services:
        service_elem = etree.SubElement(service_list_elem, "{%s}Service" % ns)

        id_elem = etree.SubElement(service_elem, "{%s}ServiceID" % ns)
        id_elem.text = str(service_id)

        name_elem = etree.SubElement(service_elem, "{%s}ServiceName" % ns)
        name_elem.text = service_name

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

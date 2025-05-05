from lxml import etree

def validate_xml(xml_bytes: bytes, xsd_path: str) -> bool:
    try:
        # Şema dosyasını aç
        with open(xsd_path, 'rb') as schema_file:
            schema_doc = etree.parse(schema_file)
            schema = etree.XMLSchema(schema_doc)

        # XML verisini bellekte parse et
        xml_doc = etree.fromstring(xml_bytes)

        # Doğrulama yap
        schema.assertValid(xml_doc)
        return True

    except Exception as e:
        print(f"[HATA] Dosya yükleme ya da analiz hatası: {e}")
        return False

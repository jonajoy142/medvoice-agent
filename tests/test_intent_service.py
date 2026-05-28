from app.services.intent_service import intent_service


def test_extract_entities_includes_raw_text_and_opid():
    entities = intent_service.extract_entities("My OPID is 411326")
    assert entities["opid"] == "411326"
    assert entities["text"] == "My OPID is 411326"


def test_doctor_info_route_does_not_crash_on_that_doctor_reference():
    entities = intent_service.extract_entities("Tell me about that doctor")
    session = {"last_doctor_list": ["Meera"]}
    result = intent_service.route_intent("doctor_info", entities, session)
    assert result["action"] in {"doctor_info", "doctor_list"}
    assert isinstance(result["response"], str)


def test_availability_response_has_single_doctor_prefix():
    entities = intent_service.extract_entities("Is any dermatologist available?")
    result = intent_service.route_intent("check_availability", entities, {})
    assert result["action"] == "availability_info"
    assert "Dr. Dr." not in result["response"]

from typing import Dict

import pytest
from pydantic import ValidationError

from fides.api.ops.graph.config import CollectionAddress, FieldAddress
from fides.api.ops.schemas.dataset import FidesopsDatasetReference
from fides.api.ops.schemas.saas.saas_config import (
    ConnectorParam,
    ParamValue,
    SaaSConfig,
    SaaSRequest,
)


@pytest.mark.unit_saas
def test_saas_configs(saas_example_config) -> None:
    """Simple test to verify that the example config can be deserialized into SaaSConfigs"""
    SaaSConfig(**saas_example_config)


@pytest.mark.unit_saas
def test_saas_request_without_method_or_path():
    with pytest.raises(ValidationError) as exc:
        SaaSRequest(path="/test")
    assert "A request must specify a method" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        SaaSRequest(method="GET")
    assert "A request must specify a path" in str(exc.value)


@pytest.mark.unit_saas
def test_saas_request_override():
    """
    Verify that valid request configs with override function
    can be deserialized into SaaSRequest
    """
    SaaSRequest(request_override="test_override")

    pv = ParamValue(
        name="test_param",
        references=[
            FidesopsDatasetReference(
                dataset="test_dataset", field="test_field", direction="from"
            )
        ],
    )
    SaaSRequest(request_override="test_override", param_values=[pv])

    SaaSRequest(
        request_override="test_override",
        param_values=[pv],
        grouped_inputs=["test_param"],
    )


@pytest.mark.unit_saas
def test_saas_request_override_invalid_properties():
    """
    Verify that invalid request configs with override function
    and various additional, unallowed properties are properly rejected
    """
    with pytest.raises(ValidationError) as exc:
        SaaSRequest(request_override="test_override", path="/test")
    assert "Invalid properties" in str(exc.value) and "path" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        SaaSRequest(request_override="test_override", method="GET")
    assert "Invalid properties" in str(exc.value) and "method" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        SaaSRequest(request_override="test_override", path="/test", method="GET")
    assert (
        "Invalid properties" in str(exc.value)
        and "path" in str(exc.value)
        and "method" in str(exc.value)
    )

    with pytest.raises(ValidationError) as exc:
        SaaSRequest(request_override="test_override", body="testbody")
    assert "Invalid properties" in str(exc.value) and "body" in str(exc.value)


@pytest.mark.unit_saas
def test_saas_config_to_dataset(saas_example_config: Dict[str, Dict]):
    """Verify dataset generated by SaaS config"""

    # convert endpoint references to dataset references to be able to hook
    # SaaS connectors into the graph traversal
    saas_config = SaaSConfig(**saas_example_config)
    saas_dataset = saas_config.get_graph()

    # messages
    messages_collection = next(
        col for col in saas_dataset.collections if col.name == "messages"
    )
    conversation_id_field = messages_collection.fields[0]
    conversations_reference = conversation_id_field.references[0]
    field_address, direction = conversations_reference

    assert conversation_id_field.name == "conversation_id"
    assert field_address == FieldAddress(saas_config.fides_key, "conversations", "id")
    assert direction == "from"

    member_collection = next(
        col for col in saas_dataset.collections if col.name == "member"
    )
    query_field = member_collection.fields[0]
    assert query_field.name == "email"
    assert query_field.identity == "email"

    # users
    users_collection = next(
        col for col in saas_dataset.collections if col.name == "users"
    )
    org_slug_reference, direction = users_collection.fields[0].references[0]
    assert users_collection.after == {
        CollectionAddress("saas_connector_example", "projects")
    }
    assert users_collection.grouped_inputs == {
        "organization_slug",
        "project_slug",
        "query",
    }
    assert org_slug_reference == FieldAddress(
        saas_config.fides_key, "projects", "organization", "slug"
    )
    assert direction == "from"

    project_slug_reference, direction = users_collection.fields[1].references[0]
    assert project_slug_reference == FieldAddress(
        saas_config.fides_key, "projects", "slug"
    )
    assert direction == "from"

    # assert that delete-only endpoints generate a collection with at least one primary key field
    people_collection = next(
        col for col in saas_dataset.collections if col.name == "people"
    )
    assert any(field for field in people_collection.fields if field.primary_key)


@pytest.mark.unit_saas
def test_saas_config_ignore_errors_param(saas_example_config: Dict[str, Dict]):
    """Verify saas config ignore errors"""
    # convert endpoint references to dataset references to be able to hook SaaS connectors into the graph traversal
    saas_config = SaaSConfig(**saas_example_config)

    collections_endpoint = next(
        end for end in saas_config.endpoints if end.name == "conversations"
    )
    # Specified on collections read endpoint
    assert collections_endpoint.requests["read"].ignore_errors

    member_endpoint = next(end for end in saas_config.endpoints if end.name == "member")
    # Not specified on member read endpoint - defaults to False
    assert not member_endpoint.requests["read"].ignore_errors


@pytest.mark.unit_saas
class TestConnectorParam:
    def test_name_only(self):
        ConnectorParam(name="account_type")

    def test_single_default_value(self):
        ConnectorParam(name="account_type", default_value="checking")

    def test_list_default_values(self):
        ConnectorParam(name="account_types", default_value=["checking", "savings"])

    def test_missing_name(self):
        with pytest.raises(ValidationError) as exc:
            ConnectorParam(default_value="checking")
        assert "field required" in str(exc.value)

    def test_default_value_not_in_options(self):
        with pytest.raises(ValidationError) as exc:
            ConnectorParam(
                name="account_types",
                default_value="roth",
                options=["checking", "savings"],
            )
        assert (
            "'roth' is not a valid option, default_value must be a value from [checking, savings]"
            in str(exc.value)
        )

    def test_default_values_not_in_options(self):
        with pytest.raises(ValidationError) as exc:
            ConnectorParam(
                name="account_types",
                default_value=["roth", "401k"],
                options=["checking", "savings"],
                multiselect=True,
            )
        assert (
            "[roth, 401k] are not valid options, default_value must be a list of values from [checking, savings]"
            in str(exc.value)
        )

    def test_multiselect_without_options(self):
        with pytest.raises(ValidationError) as exc:
            ConnectorParam(name="account_types", multiselect=True)
        assert (
            "The 'multiselect' field in the account_types connector_param must be accompanied by an 'options' field containing a list of values."
            in str(exc.value)
        )

    def test_default_value_list_without_multiselect(self):
        with pytest.raises(ValidationError) as exc:
            ConnectorParam(
                name="account_types",
                default_value=["checking", "savings"],
                options=["checking", "savings"],
            )
        assert (
            "The default_value for the account_types connector_param must be a single value when multiselect is not enabled, not a list"
            in str(exc.value)
        )

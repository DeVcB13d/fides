"""
Exports various resources as data maps.
"""

from typing import Dict, List, Tuple

import pandas as pd
from fideslang.models import ContactDetails, Taxonomy

from fidesctl.core.api_helpers import get_server_resources
from fidesctl.core.export_helpers import (
    convert_tuple_to_string,
    export_datamap_to_excel,
    export_to_csv,
    generate_data_category_rows,
    get_datamap_fides_keys,
    get_formatted_data_protection_impact_assessment,
    get_formatted_data_subjects,
    get_formatted_data_use,
    union_data_categories_in_joined_dataframe,
)
from fidesctl.core.utils import echo_green, get_all_level_fields


def generate_dataset_records(
    server_dataset_list: List,
) -> List[Tuple[str, str, str, str, str, str, str]]:
    """
    Returns a list of tuples as records (with expected headers)
    to be exported as csv. The ouput rows consist of unique combinations
    of data categories, data qualifiers, and data uses for the entire dataset
    """

    output_list = [
        (
            "dataset.name",
            "dataset.description",
            "dataset.data_categories",
            "dataset.data_qualifier",
            "dataset.retention",
            "dataset.third_country_transfers",
            "dataset.fides_key",
        )
    ]

    # using a set to preserve uniqueness of categories and qualifiers across fields
    unique_data_categories: set = set()
    for dataset in server_dataset_list:
        dataset_name = dataset.name
        dataset_description = dataset.description
        dataset_fides_key = dataset.fides_key
        dataset_retention = dataset.retention
        dataset_third_country_transfers = ", ".join(
            dataset.third_country_transfers or []
        )
        if dataset.data_categories:
            dataset_rows = generate_data_category_rows(
                dataset_name,
                dataset_description,
                dataset.data_qualifier,
                dataset.data_categories,
                dataset_retention,
                dataset_third_country_transfers,
                dataset_fides_key,
            )
            unique_data_categories = unique_data_categories.union(dataset_rows)
        for collection in dataset.collections:
            collection_retention = collection.retention or dataset_retention
            if collection.data_categories:
                dataset_rows = generate_data_category_rows(
                    dataset_name,
                    dataset_description,
                    collection.data_qualifier,
                    collection.data_categories,
                    collection_retention,
                    dataset_third_country_transfers,
                    dataset_fides_key,
                )
                unique_data_categories = unique_data_categories.union(dataset_rows)
            for field in get_all_level_fields(collection.fields):
                if field.data_categories:
                    dataset_rows = generate_data_category_rows(
                        dataset_name,
                        dataset_description,
                        field.data_qualifier,
                        field.data_categories,
                        field.retention or collection_retention,
                        dataset_third_country_transfers,
                        dataset_fides_key,
                    )
                    unique_data_categories = unique_data_categories.union(dataset_rows)

    # combine found records from the set as a list of tuples/records to be exported
    output_list += list(unique_data_categories)

    return output_list


def export_dataset(
    url: str, dataset_list: List, headers: Dict[str, str], manifests_dir: str, dry: bool
) -> None:
    """
    Exports the required fields from a dataset resource to a csv file.

    The resource is flattened from the server prior to being
    flattened as needed for exporting.
    """
    resource_type = "dataset"
    existing_keys = [resource.fides_key for resource in dataset_list]

    server_resource_list = get_server_resources(
        url, resource_type, existing_keys, headers
    )

    output_list = generate_dataset_records(server_resource_list)

    if not dry:
        exported_filename = export_to_csv(output_list, resource_type, manifests_dir)

        echo_green(exported_filename + " successfully exported.")
    else:
        echo_green("Output would contain:")
        for record in output_list:
            print(record)


def generate_system_records(
    server_system_list: List,
    url: str,
    headers: Dict[str, str],
) -> List[Tuple[str, ...]]:
    """
    Takes a list of systems from the server, creating a list of tuples
    to be used as records to be exported. The headers of the csv are
    currently added here as well.
    """
    output_list: List[Tuple[str, ...]] = [
        (
            "system.name",
            "system.description",
            "system.data_responsibility_title",
            "system.administrating_department",
            "system.third_country_transfers",
            "system.privacy_declaration.name",
            "system.privacy_declaration.data_categories",
            "system.privacy_declaration.data_use.name",
            "system.privacy_declaration.data_use.legal_basis",
            "system.privacy_declaration.data_use.special_category",
            "system.privacy_declaration.data_use.recipients",
            "system.privacy_declaration.data_use.legitimate_interest",
            "system.privacy_declaration.data_use.legitimate_interest_impact_assessment",
            "system.privacy_declaration.data_subjects.name",
            "system.privacy_declaration.data_subjects.rights_available",
            "system.privacy_declaration.data_subjects.automated_decisions_or_profiling",
            "system.privacy_declaration.data_qualifier",
            "system.data_protection_impact_assessment.is_required",
            "system.data_protection_impact_assessment.progress",
            "system.data_protection_impact_assessment.link",
            "dataset.fides_key",
        )
    ]

    for system in server_system_list:
        third_country_list = ", ".join(system.third_country_transfers or [])
        data_protection_impact_assessment = (
            get_formatted_data_protection_impact_assessment(
                system.data_protection_impact_assessment.dict()
            )
        )
        for declaration in system.privacy_declarations:
            data_use = get_formatted_data_use(url, headers, declaration.data_use)
            data_categories = declaration.data_categories or []
            data_subjects = get_formatted_data_subjects(
                url, headers, declaration.data_subjects
            )
            dataset_references = declaration.dataset_references or ["N/A"]
            cartesian_product_of_declaration = [
                (
                    system.name,
                    system.description,
                    system.data_responsibility_title,
                    system.administrating_department,
                    third_country_list,
                    declaration.name,
                    category,
                    data_use["name"],
                    data_use["legal_basis"],
                    data_use["special_category"],
                    data_use["recipients"],
                    data_use["legitimate_interest"],
                    data_use["legitimate_interest_impact_assessment"],
                    subject["name"],
                    subject["rights_available"],
                    subject["automated_decisions_or_profiling"],
                    declaration.data_qualifier,
                    data_protection_impact_assessment["is_required"],
                    data_protection_impact_assessment["progress"],
                    data_protection_impact_assessment["link"],
                    dataset_reference,
                )
                for category in data_categories
                for subject in data_subjects
                for dataset_reference in dataset_references
            ]
            output_list += cartesian_product_of_declaration

    return output_list


def export_system(
    url: str, system_list: List, headers: Dict[str, str], manifests_dir: str, dry: bool
) -> None:
    """
    Exports the required fields from a system resource to a csv file.

    The resource is fetched from the server prior to being
    flattened as needed for exporting.
    """
    resource_type = "system"

    existing_keys = [resource.fides_key for resource in system_list]
    server_resource_list = get_server_resources(
        url, resource_type, existing_keys, headers
    )

    output_list = generate_system_records(server_resource_list, url, headers)

    if not dry:
        exported_filename = export_to_csv(output_list, resource_type, manifests_dir)

        echo_green(exported_filename + " successfully exported.")
    else:
        echo_green("Output would contain:")
        for record in output_list:
            print(record)


def generate_contact_records(
    server_organization_list: List,
) -> List:
    """
    Takes a list of organizations and breaks out the individual
    fields to be returned.
    """
    output_list: List[Tuple] = [
        (
            "Organization Name and Contact Detail",
            "",
            "Data Protection Officer (if applicable)",
            "",
            "Representative (if applicable)",
            "",
        )
    ]

    # currently the output file will only truly support a single organization
    # need to better understand the use case for multiple and how to handle
    for organization in server_organization_list:
        fields = tuple(ContactDetails().dict().keys())

        get_values = (
            lambda x: tuple(x.dict().values())
            if x
            else tuple(ContactDetails().dict().values())
        )
        controller = get_values(organization.controller)
        data_protection_officer = get_values(organization.data_protection_officer)
        representative = get_values(organization.representative)

        contact_details = list(
            zip(
                fields,
                controller,
                fields,
                data_protection_officer,
                fields,
                representative,
            )
        )

        output_list += contact_details

    return output_list


def export_organization(
    url: str,
    organization_list: List,
    headers: Dict[str, str],
    manifests_dir: str,
    dry: bool,
) -> None:
    """
    Exports the required fields from a system resource to a csv file.

    The resource is fetched from the server prior to being
    flattened as needed for exporting.
    """
    resource_type = "organization"

    existing_keys = [resource.fides_key for resource in organization_list]

    server_resource_list = get_server_resources(
        url, resource_type, existing_keys, headers
    )

    output_list = generate_contact_records(server_resource_list)

    if not dry:
        exported_filename = export_to_csv(output_list, resource_type, manifests_dir)

        echo_green(exported_filename + " successfully exported.")
    else:
        echo_green("Output would contain:")
        for record in output_list:
            print(record)


def build_joined_dataframe(
    server_resource_dict: Dict[str, List], url: str, headers: Dict[str, str]
) -> pd.DataFrame:
    """
    Return joined dataframes for datamap export

    Currently we have a few unhandled columns that exist in the template
    Including those here manually for now is required to use the append
    function built in to pandas
    """

    # systems
    system_output_list = generate_system_records(
        server_resource_dict["system"], url, headers
    )
    systems_df = pd.DataFrame.from_records(system_output_list)
    systems_df.columns = systems_df.iloc[0]
    systems_df = systems_df[1:]

    # datasets

    dataset_output_list = generate_dataset_records(server_resource_dict["dataset"])
    datasets_df = pd.DataFrame.from_records(dataset_output_list)
    datasets_df.columns = datasets_df.iloc[0]
    datasets_df = datasets_df[1:]

    # merge systems and datasets
    joined_df = systems_df.merge(datasets_df, how="left", on=["dataset.fides_key"])
    joined_df.fillna("N/A", inplace=True)
    ## create a set of third_country attrs to combine as a single entity
    joined_df["third_country_combined"] = [
        convert_tuple_to_string(i)
        for i in zip(
            joined_df["system.third_country_transfers"].map(str),
            joined_df["dataset.third_country_transfers"],
        )
    ]

    # restructure the joined dataframe to represent system and dataset data categories appropriately
    joined_df = union_data_categories_in_joined_dataframe(joined_df)

    delete_df = joined_df[["system.name", "unioned_data_categories"]][
        joined_df.groupby(["system.name", "unioned_data_categories"])[
            "dataset.name"
        ].transform("count")
        > 1
    ].drop_duplicates()

    delete_df["dataset.name"] = "N/A"

    joined_df = (
        pd.merge(joined_df, delete_df, indicator=True, how="outer")
        .query('_merge=="left_only"')
        .drop("_merge", axis=1)
    )

    # model empty columns until implemented as part of appending to template
    joined_df["system.joint_controller"] = ""
    joined_df["system.third_country_safeguards"] = ""
    joined_df["system.link_to_processor_contract"] = ""

    joined_df["organization.link_to_security_policy"] = (
        server_resource_dict["organization"][0].security_policy or ""
    )

    return joined_df


def export_datamap(
    url: str,
    taxonomy: Taxonomy,
    headers: Dict[str, str],
    manifests_dir: str,
    dry: bool,
    to_csv: bool,
) -> None:
    """
    Exports the required fields from a system resource to a csv file.

    The resource is fetched from the server prior to being
    flattened as needed for exporting.
    """

    # load resources from server

    fides_keys_dict = get_datamap_fides_keys(taxonomy)

    server_resource_dict = {}
    for resource_type in ["organization", "system", "dataset"]:

        server_resource_dict[resource_type] = get_server_resources(
            url,
            resource_type,
            fides_keys_dict[resource_type],
            headers,
        )

    joined_system_dataset_df = build_joined_dataframe(
        server_resource_dict, url, headers
    )

    if not dry and not to_csv:

        # build an organization dataframe if exporting to excel
        organization_df = pd.DataFrame.from_records(
            generate_contact_records(server_resource_dict["organization"])
        )
        organization_df.columns = organization_df.iloc[0]
        organization_df = organization_df[1:]

        exported_filename = export_datamap_to_excel(
            organization_df, joined_system_dataset_df, manifests_dir
        )
        echo_green(exported_filename + " successfully exported.")
    else:
        output_list = [tuple(joined_system_dataset_df.columns)]
        output_list += list(joined_system_dataset_df.itertuples(index=False, name=None))

        if dry:
            echo_green("Output would contain:")
            for record in output_list:
                print(record)
        else:
            exported_filename = export_to_csv(output_list, "datamap", manifests_dir)
            echo_green(exported_filename + " successfully exported.")

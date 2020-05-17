from distutils import version


# TODO: this method could go in shaptools itself, providing the query return formatted if
# it is requested (returning a list of dictionaries like this method)
def format_query_result(query_result):
    """
    Format query results to match column names with their values for each row
    Returns: list containing a dictionaries (column_name, value)

    Args:
        query_result (obj): QueryResult object
    """
    formatted_query_result = []
    query_columns = [meta[0] for meta in query_result.metadata]
    for record in query_result.records:
        record_data = {}
        for index, record_item in enumerate(record):
            record_data[query_columns[index]] = record_item

        formatted_query_result.append(record_data)
    return formatted_query_result


def check_hana_range(hana_version, availability_range):
    """
    Check if the current hana version is inside the available range

    Args:
        hana_version (str): Current hana version
        availability_range (list): List with one or two elements definining the
            available hana versions

    Returns:
        bool: True if the current hana version is inside the availability range
    """

    if len(availability_range) == 1:
        return version.LooseVersion(hana_version) >= version.LooseVersion(
            availability_range[0])
    elif len(availability_range) == 2:
        return version.LooseVersion(hana_version) >= version.LooseVersion(availability_range[0]) \
            and version.LooseVersion(hana_version) <= version.LooseVersion(availability_range[1])
    raise ValueError(
        'provided availability range does not have the correct number of elements'
    )

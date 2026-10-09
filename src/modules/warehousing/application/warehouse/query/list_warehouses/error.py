class InvalidWarehouseListParametersError(Exception):
    """Некорректные параметры чтения списка, включая cursor и limit."""

    code = "warehouse.invalid_list_parameters"

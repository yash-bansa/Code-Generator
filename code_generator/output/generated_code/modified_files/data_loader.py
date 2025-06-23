import pandas as pd

def load_data():
    """
    Simulate loading data from a CSV or database.

    Returns:
        pd.DataFrame: Loaded data.
    """
    data = {
        "c_id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "score": [95, 88, 76],
        "check": [True, False, True]  # Added a new column 'check' to the loaded data
    }
    df = pd.DataFrame(data)
    return df
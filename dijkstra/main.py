from datastore import load_datastore
from report import print_report


if __name__ == "__main__":
    store = load_datastore()
    print_report(store)

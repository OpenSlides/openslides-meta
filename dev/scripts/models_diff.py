#!/bin/python3

from os import listdir
from os.path import splitext, join
from json import load
from yaml import safe_load
from datetime import datetime,timezone,timedelta
import argparse
import sys


ARGS = argparse.Namespace()
COLLECTIONS_DIRNAME = 'collections/'
COLLECTIONS = {}
D1 = {}
D2 = {}
DIFF = []


def list_type_is_equal(l1, l2):
    is_equal = False

    # Case not observed, but would count as equal
    if l1 is None and l2 is None:
        is_equal = True
    # EXPECTED DIFF: empty list becomes None
    if type(l1) is list and l2 is None:
        if len(l1) == 0:
            is_equal = True
    # EXPECTED DIFF: non-empty list may be in different order
    elif type(l1) is list and type(l2) is list:
        if sorted(l1) == sorted(l2):
            is_equal = True

    return is_equal


def relation_list_type_is_equal(l1, l2):
    is_equal = list_type_is_equal(l1, l2)

    # Some back relations were not consistently maintained pre 4.3.0 .
    # Those cases are fine as long as no ids were lost.
    # -> i.e. l2 fully contains l1
    if not is_equal:
        if type(l1) is list and type(l2) is list:
            if set(l1).issubset(l2):
                is_equal = True

    return is_equal


def timestamp_is_equal(s1, s2):
    # EXPECTED DIFF: UNIX timestamps become ISO timestamps
    t1 = datetime.fromtimestamp(s1, timezone.utc)
    t2 = datetime.fromisoformat(s2)

    return t1.timestamp() == t2.timestamp()


def compare_value(type_, value_d1, value_d2):
    # assume not equal until proven otherwise
    is_equal = False

    # To be very explicit we will now look at all known field types distinctly.

    # In most cases '==' equality suffices.
    if type_ in [
        'boolean',
        'color',
        'decimal(6)',
        'float',
        'generic-relation',
        'HTMLPermissive',
        'HTMLStrict',
        'JSON',
        'number',
        'relation',
        'string',
        'text'
    ]:
        is_equal = value_d1 == value_d2

    # In other cases we need to compare in a more specific way.
    elif type_ in [
        'timestamp'
    ]:
        is_equal = timestamp_is_equal(value_d1, value_d2)
    elif type_ in [
        'number[]',
        'string[]',
        'text[]'
    ]:
        is_equal = list_type_is_equal(value_d1, value_d2)
    elif type_ in [
        'generic-relation-list',
        'relation-list'
    ]:
        is_equal = relation_list_type_is_equal(value_d1, value_d2)

    # This should never happen.
    else:
        DIFF += [f"type {type_} is not recognized."]

    return is_equal


def check_field_empty_list(collection, model_id, field_name):
    global D2

    log(4, f"check_field_empty_list: {collection}/{model_id}/{field_name} ...")

    field_type = COLLECTIONS[collection][field_name]['type']
    if field_type not in ['text[]', 'string[]', 'number[]']:
        log(4, f"- {field_name} is not a list type - not visiting")
        return

    field_value_d2 = D2[collection][model_id][field_name]
    if type(field_value_d2) is not list:
        log(4, f"- value is no list - not visiting")
        return
    if len(field_value_d2) != 0:
        log(4, f"- value is no empty list - not visiting")
        return

    log(4, f"+ visited field in D2: {collection}/{model_id}/{field_name} (empty list)")
    del D2[collection][model_id][field_name]


def check_field_default(collection, model_id, field_name):
    global D2, DIFF

    log(4, f"check_field_default: {collection}/{model_id}/{field_name} ...")

    if 'default' not in COLLECTIONS[collection][field_name].keys():
        log(4, f"- no default defined - not visiting")
        return

    field_type = COLLECTIONS[collection][field_name]['type']
    field_value_default = COLLECTIONS[collection][field_name]['default']
    field_value_d2 = D2[collection][model_id][field_name]
    is_equal = compare_value(field_type, field_value_default, field_value_d2)

    if not is_equal:
        DIFF += [f"{collection}/{model_id}/{field_name} of type {field_type} differs from default."]
        DIFF += [f"  D1: NOT SET"]
        DIFF += [f"  D2: {field_value_d2}"]

    log(4, f"+ visited field in D2: {collection}/{model_id}/{field_name} (default value)")
    del D2[collection][model_id][field_name]


def check_field(collection, model_id, field_name):
    global D1, D2, DIFF

    log(3, f"check_field: {collection}/{model_id}/{field_name} ...")

    field_type = COLLECTIONS[collection][field_name]['type']
    field_value_d1 = D1[collection][model_id][field_name]
    field_value_d2 = D2[collection][model_id][field_name]

    field_value_d1_human_readable = ""
    field_value_d2_human_readable = ""
    if field_type == 'timestamp':
        field_value_d1_human_readable = f"  ({datetime.fromtimestamp(field_value_d1, timezone.utc)})"

    is_equal = compare_value(field_type, field_value_d1, field_value_d2)

    if not is_equal:
        DIFF += [f"{collection}/{model_id}/{field_name} of type {field_type} differs."]
        DIFF += [f"  D1: {field_value_d1}{field_value_d1_human_readable}"]
        DIFF += [f"  D2: {field_value_d2}{field_value_d2_human_readable}"]

    # Fields of type generic-relation will additionally appear in an expanded form
    if field_type == 'generic-relation':
        if not is_equal:
            log(4, f"- field values not equal - not visiting expanded {field_name} fields")
        else:
            related_collection, _ = field_value_d1.split('/')
            expanded_field_name = f"{field_name}_{related_collection}_id"
            # Remove visited field
            log(4, f"+ visited expanded field in D2: {collection}/{model_id}/{expanded_field_name}")
            del D2[collection][model_id][expanded_field_name]

    # Remove visited field
    log(3, f"+ visited field in D1: {collection}/{model_id}/{field_name}")
    del D1[collection][model_id][field_name]
    log(3, f"+ visited field in D2: {collection}/{model_id}/{field_name}")
    del D2[collection][model_id][field_name]


def check_model(collection, model_id):
    global D1, D2, DIFF

    log(2, f"check_model: {collection}/{model_id} ...")

    field_names_d1 = list(D1[collection][model_id].keys())
    field_names_d2 = list(D2[collection][model_id].keys())

    for field_name in field_names_d1:
        # EXPECTED DIFF: meta_deleted and meta_position fields were removed
        if field_name == 'meta_deleted' or field_name == 'meta_position':
            # Remove visited field
            log(4, f"+ visited field in D1: {collection}/{model_id}/{field_name} (old field)")
            del D1[collection][model_id][field_name]
            continue

        if field_name not in field_names_d2:
            DIFF += [f"field {collection}/{model_id}/{field_name} exists in D1 but not in D2"]
            continue

        check_field(collection, model_id, field_name)

    log(4, f"visiting known new fields in D2 ...")
    remaining_field_names_d2 = list(D2[collection][model_id].keys())
    if collection in ['organization', 'meeting']:
        if 'time_zone' in remaining_field_names_d2:
            log(4, f"+ visited field in D2: {collection}/{model_id}/time_zone (new field)")
            del D2[collection][model_id]['time_zone']

    log(4, f"checking remaining fields in D2 ...")
    # Fields not present in D1 may appear in D2
    # - as None (null value)
    remaining_field_names_d2 = list(D2[collection][model_id].keys())
    for field_name in remaining_field_names_d2:
        if D2[collection][model_id][field_name] is None:
            log(4, f"+ visited field in D2: {collection}/{model_id}/{field_name} (null value)")
            del D2[collection][model_id][field_name]
    # - with default value
    remaining_field_names_d2 = list(D2[collection][model_id].keys())
    for field_name in remaining_field_names_d2:
        check_field_default(collection, model_id, field_name)
    # - as empty list
    remaining_field_names_d2 = list(D2[collection][model_id].keys())
    for field_name in remaining_field_names_d2:
        check_field_empty_list(collection, model_id, field_name)

    # Remove visited model
    if len(D1[collection][model_id]) == 0:
        log(2, f"+ fully visited model in D1: {collection}/{model_id}")
        del D1[collection][model_id]
    if len(D2[collection][model_id]) == 0:
        log(2, f"+ fully visited model in D2: {collection}/{model_id}")
        del D2[collection][model_id]


def check_collection(collection):
    global D1, D2, DIFF

    # This can happen if certain features were not used and therefore no models
    # in corresponding collections were created.
    if collection not in D1.keys() and collection not in D2.keys():
        log(1, f"check_collection: skipping {collection}, does not exist in both D1 and D2 ...")
        return
    # This would be a fatal flaw in migration100 and should never occur.
    if collection not in D1.keys() or collection not in D2.keys():
        DIFF += [f"collection {collection} exists in only one of D1 and D2"]
        return

    log(1, f"check_collection: {collection} ...")

    model_ids_d1 = list(D1[collection].keys())
    model_ids_d2 = list(D2[collection].keys())

    for model_id in model_ids_d1:
        if model_id not in model_ids_d2:
            DIFF += [f"model {collection}/{model_id} exists in D1 but not in D2"]
            continue

        check_model(collection, model_id)

    # Remove visited collection
    if len(D1[collection]) == 0:
        log(1, f"+ fully visited collection in D1: {collection}")
        del D1[collection]
    if len(D2[collection]) == 0:
        log(1, f"+ fully visited collection in D2: {collection}")
        del D2[collection]


def check_all():
    for collection in COLLECTIONS.keys():
        check_collection(collection)


def load_collections():
    global COLLECTIONS

    collection_files = listdir(COLLECTIONS_DIRNAME)
    for fname in collection_files:
        collection, ext = splitext(fname)

        if ext != '.yml':
            continue

        with open(join(COLLECTIONS_DIRNAME, fname)) as f:
            COLLECTIONS[collection] = safe_load(f)['fields']


def load_input():
    global D1, D2

    filename1 = ARGS.d1
    filename2 = ARGS.d2

    with open(filename1) as f1:
        D1 = load(f1)
    with open(filename2) as f2:
        D2 = load(f2)


def print_models(d):
    for collection in d.keys():
        for model_id in d[collection].keys():
            model = f"{collection}/{model_id}"
            print(f"  {model}: {d[collection][model_id]}")


def print_results():
    print()

    if len(D1) == 0 and len(D2) == 0:
        print("All collections, models and fields have been visited and compared.")
    else:
        print("Not all collections, models and fields were compared.")
        print("This hints to inconsistent data.")
        print("Remaining fields in models, that were not visited.")
        print()
        print("D1:")
        print_models(D1)
        print()
        print("D2:")
        print_models(D2)

    print()

    if len(DIFF) == 0:
        print("No differences found.")
    else:
        print("Found differences.")
        print()
        print('\n'.join(DIFF))


def log(l, s):
    if ARGS.level >= l:
        print(f"{l}:{'  ' * l}{s}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Script for comparing OpenSlides data in JSON format before and after migration to 4.3.0 ."
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Use multiple times to set log level (1: collection, 2: model, 3: field, 4: detail)",
        dest="level",
    )

    parser.add_argument(
        "d1",
        help="Path to D1 (JSON data - pre 4.3.0)",
    )
    parser.add_argument(
        "d2",
        help="Path to D2 (JSON data - post 4.3.0)",
    )

    return parser


def main():
    global ARGS

    parser = build_parser()
    ARGS = parser.parse_args(sys.argv[1:])

    load_collections()
    load_input()

    check_all()
    print_results()


if __name__ == '__main__':
    main()

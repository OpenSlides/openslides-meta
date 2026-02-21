# join_models_yml.py is a temporary script to create the old models.yml until
# all services are able to work with the new separat collections.


from pathlib import Path

from .helper_get_names import build_models_yaml_content


def join_yaml_file(meta_file: str, collections_dir: str, output_file: str) -> None:
    content = build_models_yaml_content(meta_file, collections_dir)

    with open(output_file, "wb") as f:
        f.write(content)


if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).resolve().parent.parent  # dev/
    PROJECT_ROOT = SCRIPT_DIR.parent

    meta_file = PROJECT_ROOT / "collection-meta.yml"
    collections_dir = PROJECT_ROOT / "collections"
    output_file = PROJECT_ROOT / "models.yml"
    try:
        join_yaml_file(str(meta_file), str(collections_dir), str(output_file))
    except Exception as e:
        print(f"Fehler: {e}")

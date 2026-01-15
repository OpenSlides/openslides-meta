# OpenSlides Meta Repository

This shared repository holds all relevant (meta) data. Other service may include
it as a sub-repository to have access to its data.


## Collections

The datastructor of OpenSlides is defined by a list of collections. For each
collection, there is a file in the `collections` folder. The file
`collection-meta.yml` contains meta fields, that are used by more then one of
the collection.

Each collection-file has the following format:

Length of names:
    - field name: Their length is limited to 25 characters. There are still some
      fields with longer names, that has to be shortened
Types:
    - Nativ datatypes: text, string (text with maxLength=256), number, boolean, JSON
    - HTMLStrict: A string with HTML content.
    - HTMLPermissive: A string with HTML content (with video tags).
    - float: Numbers that are expected to be non-integer. Formatted as in rfc7159.
    - decimal(X): Decimal values represented as a string with X decimal places.
      At the moment we support only X == 6.
    - timestamp: Datetime as a unix timestamp. Why a number? This enables queries
      in the DB. And we do not need more precision than 1 second.
    - <T>[]: This indicates and arbitrary array of the given type. At the moment
      we support only some types. You can add JSON Schema properties for items
      using the extra property `items`
    - color: string that must match ^#[0-9a-f]{6}$
Relations:
    - We have the following types: `relation`, `relation-list`, `generic-relation`
      and `generic-relation-list`.
    - Non-generic relations: The simple syntax for such a field
      `to: <collection>/<field>`. This is a reference to a collection. The reverse
      relation field in this collection is <field>. E. g. in a motion the field
      `category_id` links to one category where the field `motion_ids` contains the
      motion id. The simple notation for the field is `motion_category/motion_ids`.
      The reverse field has type `relation-list` and is related back to
      `motion/category_id`. The type indicates that there are many
      motion ids.
    - Generic relations: The difference to non-generic relations is that you have a
      list of possible fields, so `to` can either hold multiple collections (if the
      field name is the same):
        to:
          collections:
            - agenda_item
            - assignment
            - ...
          field: tag_ids
      Or `to` can be a list of collection fields:
        to:
          - motion/option_ids
          - user/option_$_ids
    - on_delete: This fields determines what should happen with the foreign model if
      this model gets deleted. Possible values are:
          - SET_NULL (default): delete the id from the foreign key
          - PROTECT: if the foreign key is not empty, throw an error instead of
                     deleting the object
          - CASCADE: also delete all models in this foreign key
JSON Schema Properties:
    - You can add JSON Schema properties to the fields like `enum`, `description`,
      `items`, `maxLength` and `minimum`
Additional properties:
    - The property `read_only` describes a field that can not be changed by an action.
    - The property `default` describes the default value that is used for new objects.
    - The property `required` describes that this field can not be null or an empty
      string. If this field is given it must have some content. On relation and generic-relation
      fields the value as to be an id of an existing object.
    - The property `equal_fields` describes fields that must have the same value in
      the instance and the related instance.
Restriction Mode:
  The field `restriction_mode` is required for every field. It puts the field into a
  restriction group. See https://github.com/OpenSlides/OpenSlides/wiki/Restrictions-Overview

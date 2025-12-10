# Readme for relational sql schema

All names used in postgres are limited to 63 characters per name. This can only be changed by compiling the source code of postgres.
The length will be checked by the following methods on generating the sql-schema.

## The type TableFieldType

This type is used sometimes for the parameters of the methods. It can be build by it's constructor or as convinience with the static method **get_definitions_from_foreign**, which takes as parameters
the str-values from the **to**- and the **reference**-Attribut from models field description.

It contains the **table_name**, **fname** for the field name, the dictionary **tfield** from the models.yml with all attributes and a **ref_column**, usually filled with **id** for the foreign-key definitions.
As convinience property there is the collectionfield as combination of table_name/field_name.

## Naming conventions for tables and depending views as used in models.yml

To get the table name use method **get_table_name** with the parameter of the collection name from the models.yml. The resulting name has a **T** for table to distinguish it from the view.

To get the view name use the method **get_view_name** with the parameter of the collection name from the models.yml. The view name is identical with that from models.yml, except for **group and user**, which are reserved names in sql. They will get an appended **_** to their name.


## Naming conventions for intermediate tables and views

### relation-list versus relation-list

Because the base tables of these intermediate files are symmetric, the parts of the tables name are taken in an alphabetical order of their **collectionfields**. The name is build from parts

* nm_ Constant part to mark a n:m intermediate table
* table_name of the smaller **collectionfield**
* _ Constant divider
* field name of the smaller **collectionfield**
* _ Constant divider
* table name of the greater **collectionfield** 

### generic-relation-list versus relation-list

The name of the intermediate table for **generic-relation-list** versus **relation-list** is always build from the generic-relation-lists side.

* gm_ Constant part to mark a genericc-list:m intermediate table
* table name of the generic-relation-list field
* _ Constant divider
* field name of the generic-relation-list field

## Attributes and rules
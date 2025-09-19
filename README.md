# GPS File Specification

### Input and Output
The first two lines tell the script what are the input file (a GeoJSON NL type file), and the output file (a normal GeoJSON file).

### Filter the records
Then we can start describing how we want to filter the data, we can write `"city"="New York"` and the script will filter for the "city" value in the "properties" section

## Transformative Operations
### Renaming
To rename a key in the "properties" list we can use the `^` operator, so by writing `"city"^"addr:city"`we are telling the program to update every field with this new key
### Deleting
To delete something we use the `-` operator, by doing this every field, empty or not, will be deleted, the syntax is `-"addr:city"` (Note that we use addr:city since the old one has been changed, the operations are done in order, so if you rename a field you have to use the new name)
### Soft Delete
A soft delete is when we delete only empty or null fields and leave fields with data, we use the syntax similar to the delete with `~"addr:city"`
### Lowercase
To lowercase everything we use the `_` sign, by doing this every letter will be in lowercase, the syntax is `_"street"`
### Title case
To make every starting letter of a phrase capitalized we can use the `§`, like with `§"street"` that will transform streets names like `VIALE GENERAL GIARDINO` and `viale general giardino` in `Viale General Giardino`
### Offsetting coordinates
By using +x, +y, -x and -y we can modify the coordinates of the geometry field and offset the coordinates, so by using a syntax similar to `+x"0.001"`
### Concatenate Fields
To join or concatenate two fields in the "property" field, we use it as `"number"+"unit"` and this will produce something like 17A or 17B
### Separate multiple values
If a set of values is described in a field like a CSV file and you want to create multiple records with this value separated you can use this syntax `"unit"[;]` indicating in the brackets the separator
### Unique geographic coordinates
To use unique geographic coordinates to prevent software like JOSM to create joint nodes you can use the `#` char and the script will aply an offset when a coordinate is already used
### Conditional statements
To apply a statement based on a condition you can use the `:` and a syntax like this `"number % 2 == 0":+x"0.00001"`.

To simply put it before the `:` we have the condition, evaluated based on python syntax and with values replaced by the contents of the feature.
### 
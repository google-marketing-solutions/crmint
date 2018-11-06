---
bodyclass: docs
headline: CRMint workers reference
layout: docs
sidenav: doc-side-reference-nav.html
type: markdown
---

### Using Google Analytics Measurement Protocol from CRMint

The [`BQToMeasurementProtocol` worker](worker_spec.html#bqtomeasurementprotocol) provides the means to send [Measurement Protocol](https://developers.google.com/analytics/devguides/collection/protocol/v1/) hits to GA sourced from a BigQuery table.

The BigQuery table schema for `BQToMeasurementProtocol` is as follows:

*   Field names and types should be names and types of [Measurement Protocol parameters](https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters).
*   For Measurement Protocol parameters representing lists, [repeated fields](https://cloud.google.com/bigquery/docs/nested-repeated) (arrays) should be used (see details below).

The only parameter that can be omitted is `v` — the Measurement Protocol version, which is provided by CRMint by default as `v=1`.

If the table has a column with a name not matching a valid Measurement Protocol parameter, it will be sent as a non-existing parameter, resulting in an invalid Measurement Protocol hit. The idea behind this is to not interfere with what a user wants to send as Measurement Protocol hit: we're neither validating, nor transforming parameters and their names.

The only exception is made for the names of repeated parameters: for those we *unfold* array fields to params named like `<field_name><array_element_index>`.

For example, for multiple [Content Groups](https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters#cg_) you can either:

*   Use separate fields named `cg1`, `cg2`, etc.
*   **OR** use one array field named `cg` — this will be unfolded automatically to `cg1`, `cg2` and so on with values taken from the corresponding array elements (one-based indices are used).

All of this is to support Enhanced E-Commerce [Product Impressions lists](https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters#il_nm) and [Product Lists](https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters#pr_id).

Structures are  unfolded the same way as arrays are, but using structure keys instead of array indices. Arrays and structures are unfolded recursively to the full nesting depth.

Consider this example data row from a BigQuery table represented in JSON:

```json
{
    "ni": "1",
    "tid": "UA-12345-67",
    "cid": "12345.67890",
    "t": "pageview",
    "dl": "https://example.host/path/page/",
    "pa": "purchase",
    "ti": "1234",
    "ta": "Moscow",
    "tr": 54321,
    "cu": "RUB",
    "geoid": "1011969",
    "cs": "(direct)",
    "cm": "offline",
    "ds": "crm",
    "pr": [
        {
            "id": "SKU1",
            "nm": "Product Name 1",
            "br": "Brand 1",
            "ca": "Category 1",
            "pr": 111,
            "qt": "1"
        },
        {
            "id": "SKU2",
            "nm": "Product Name 2",
            "br": "Brand 2",
            "ca": "Category 2",
            "pr": 222,
            "qt": "2"
        },
        {
            "id": "SKU3",
            "nm": "Product Name 3",
            "br": "Brand 3",
            "ca": "Category 3",
            "pr": 333,
            "qt": "3"
        },
    ]
}
```

This is converted to this Measurement Protocol parameters and values:

| parameter | value |
|---|---|
|cid|12345.67890|
|cm|offline|
|cs|(direct)|
|cu|RUB|
|dl|https://example.host/path/page/|
|ds|crm|
|geoid|1011969|
|ni|1|
|pa|purchase|
|pr1br|Brand 1|
|pr1ca|Category 1|
|pr1id|SKU1|
|pr1nm|Product Name 1|
|pr1pr|111|
|pr1qt|1|
|pr2br|Brand 2|
|pr2ca|Category 2|
|pr2id|SKU2|
|pr2nm|Product Name 2|
|pr2pr|222|
|pr2qt|2|
|pr3br|Brand 3|
|pr3ca|Category 3|
|pr3id|SKU3|
|pr3nm|Product Name 3|
|pr3pr|333|
|pr3qt|3|
|t|pageview|
|ta|Moscow|
|ti|1234|
|tid|UA-12345-67|
|tr|54321|
|v|1|

Transformed to a Measurement Protocol payload string, this is represented as follows:

```
cid=12345.67890&cm=offline&cs=%28direct%29&cu=RUB&dl=https%3A%2F%2Fexample.host%2Fpath%2Fpage%2F&ds=crm&geoid=1011969&ni=1&pa=purchase&pr1br=Brand+1&pr1ca=Category+1&pr1id=SKU1&pr1nm=Product+Name+1&pr1pr=111&pr1qt=1&pr2br=Brand+2&pr2ca=Category+2&pr2id=SKU2&pr2nm=Product+Name+2&pr2pr=222&pr2qt=2&pr3br=Brand+3&pr3ca=Category+3&pr3id=SKU3&pr3nm=Product+Name+3&pr3pr=333&pr3qt=3&t=pageview&ta=Moscow&ti=1234&tid=UA-12345-67&tr=54321&v=1
```


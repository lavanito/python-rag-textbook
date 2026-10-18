# Concept map (ontology and triples)

A small, hand-built map of the ideas in the corpus and how they relate.
Chapter 5 uses it to widen searches (a query for "volume measure" also finds
"constant prices" and "chain-linked") and to move between manuals (from a BEA
passage to the equivalent SNA or ESA paragraph). Chapter 12 uses the question
types and indicators to split a vague question.

| File | What it holds |
| --- | --- |
| `schema.json` | The ontology: six kinds of thing and eleven relations, each with the kind of its subject and object |
| `entities.csv` | Every thing in the map: id, kind, label, and other names (aliases) separated by semicolons |
| `triples.csv` | Facts as subject, relation, object, with the evidence for each: a passage id, or `author` for the author's own framing |

Each line of `triples.csv` is one fact in three parts, for example
`terms_of_trade, defined_in, sna08-15.187`.

Which manual each passage comes from is not repeated here: it is the
`source_code` field of each passage in `data/corpus/passages.jsonl`, and the
code adds those facts when it loads the map.

`tests/test_ontology.py` checks that every fact uses a declared relation, that
subject and object have the kinds the relation requires, that every passage id
exists, and that every fact has evidence.

## Known gaps

- Hedonic adjustment has no passage in the corpus yet.
- Only the economies whose manual is certain are linked to one (United States:
  BEA; euro area: ESA 2010).

## Where a larger system would differ

This map has 51 things and 73 facts (plus one per passage linking it to its manual), typed in by hand and read by plain
Python. A commercial system with millions of series would store the same kind
of facts in a graph database or as RDF with an OWL ontology, extract many of
them from documents with a language model and have people check the doubtful
ones, and search them with a search engine such as Elasticsearch or OpenSearch.
The ideas are the same: kinds of thing, typed relations, evidence for each
fact. Those tools are a later extension, outside this book.

# Knowledge graph (ontology and triplets)

A small, hand-built knowledge graph of the ideas in the corpus and how they
relate. Chapter 5 uses it to widen searches (a query for "volume measure" also
finds "constant prices" and "chain-linked") and to move between manuals (from
a BEA passage to the equivalent SNA or ESA paragraph). Chapter 12 uses the
question types and indicators to split a vague question.

## Terms

- **Ontology:** the rules. It lists which kinds of thing exist and which
  relations may link them. Here: `schema.json`.
- **Knowledge graph:** an ontology together with the facts that follow its
  rules: the things, and the triplets that link them. Here: all three files.
- **Concept map:** a diagram of concepts joined by labelled arrows, with no
  fixed rules on kinds or relations. This folder is not one: every fact must
  pass the ontology's rules, and a test checks that it does.

| File | What it holds |
| --- | --- |
| `schema.json` | The ontology: six kinds of thing and eleven relations, each with the kind of its subject and object |
| `entities.csv` | Every thing in the graph: id, kind, label, and other names (aliases) separated by semicolons |
| `triples.csv` | Triplets as subject, relation, object, with the evidence for each: a passage id, or `author` for the author's own framing |

Each line of `triples.csv` is one triplet, for example
`terms_of_trade, defined_in, sna08-15.187`.

Which manual each passage comes from is not repeated here: it is the
`source_code` field of each passage in `data/corpus/passages.jsonl`, and the
code reads it from there.

`tests/test_knowledge_graph.py` checks that every triplet uses a declared
relation, that subject and object have the kinds the relation requires, that
every passage id exists, and that every triplet has evidence.

## Known gaps

- Hedonic adjustment has no passage in the corpus yet.
- Only the economies whose manual is certain are linked to one (United States:
  BEA; euro area: ESA 2010).

## Extracted triplets (Chapter 13)

Chapter 13 has the local model read each passage and propose triplets in the
same three-part form. The code compares them with this hand-built graph and
reports how many are right, wrong or missing; doubtful ones go to the author
to check. The hand-built graph is the answer key.

## Where a larger system would differ

This graph has 51 things and 73 triplets, typed in by hand and read by plain
Python. A commercial system with millions of series would store the same kind
of facts in a graph database such as Neo4j, or as RDF with an OWL ontology,
extract many of them from documents with a language model and have people
check the doubtful ones, and search them with a search engine such as
Elasticsearch or OpenSearch. The ideas are the same: kinds of thing, typed
relations, evidence for each fact. Appendix D loads this graph into Neo4j.
